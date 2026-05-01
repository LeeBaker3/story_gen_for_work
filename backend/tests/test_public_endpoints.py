import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend import settings as settings_mod, storage_paths
from backend.database import Character, DynamicList, DynamicListItem, Page, Story, User
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="function", autouse=True)
def seed_test_db(db_session: Session):
    """Seeds the test database with initial data before each test."""
    # Clear existing data to ensure a clean slate for this test module
    db_session.query(DynamicListItem).delete()
    db_session.query(DynamicList).delete()
    db_session.commit()

    # Create lists
    db_session.add(DynamicList(list_name="genres", list_label="Genres"))
    db_session.add(DynamicList(
        list_name="image_styles", list_label="Image Styles"))
    db_session.commit()

    # Create items
    db_session.add(DynamicListItem(list_name="genres", item_value="sci-fi",
                   item_label="Science Fiction", is_active=True, sort_order=1))
    db_session.add(DynamicListItem(list_name="genres", item_value="fantasy",
                   item_label="Fantasy", is_active=True, sort_order=0))
    db_session.add(DynamicListItem(list_name="genres", item_value="horror",
                   item_label="Horror", is_active=False, sort_order=2))
    db_session.add(DynamicListItem(list_name="image_styles", item_value="cartoon",
                   item_label="Cartoon Style", is_active=True, sort_order=0))
    db_session.add(DynamicListItem(list_name="image_styles", item_value="realistic",
                   item_label="Realistic", is_active=True, sort_order=1))
    db_session.commit()


def test_get_public_list_items_success(client: TestClient):
    """Test successfully fetching active items from a public list."""
    response = client.get("/api/v1/dynamic-lists/genres/active-items")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Check for correct sorting (Fantasy has sort_order 0)
    assert data[0]["item_value"] == "fantasy"
    assert data[0]["item_label"] == "Fantasy"
    assert data[1]["item_value"] == "sci-fi"
    # Ensure inactive items are not included
    assert "horror" not in [item["item_value"] for item in data]
    # Ensure only public fields are returned
    assert "is_active" not in data[0]
    assert "sort_order" not in data[0]


def test_get_public_list_items_not_found(client: TestClient):
    """Test fetching items from a list that does not exist."""
    response = client.get(
        "/api/v1/dynamic-lists/non_existent_list/active-items")
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Dynamic list 'non_existent_list' not found."}


def test_get_public_list_items_empty_list(client: TestClient, db_session: Session):
    """Test fetching items from a list that exists but has no active items."""
    db_session.add(DynamicList(
        list_name="empty_list", list_label="Empty List"))
    db_session.commit()
    response = client.get("/api/v1/dynamic-lists/empty_list/active-items")
    assert response.status_code == 200
    assert response.json() == []


def test_register_user_forces_user_role(
    client: TestClient,
    db_session: Session,
):
    response = client.post(
        "/api/v1/users/",
        json={
            "username": "self_promoted_admin",
            "password": "strongpassword",
            "email": "self_promoted_admin@example.com",
            "role": "admin",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["role"] == "user"

    created_user = db_session.query(User).filter(
        User.username == "self_promoted_admin"
    ).first()
    assert created_user is not None
    assert created_user.role == "user"


def test_login_endpoint_rate_limits_by_ip(client: TestClient):
    """The login endpoint should throttle repeated attempts from one IP."""

    for _ in range(10):
        response = client.post(
            "/api/v1/token",
            data={
                "username": "user@example.com",
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/token",
        data={
            "username": "user@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 429


def test_delete_story_via_api_prefix(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    """Test deleting a user-owned story through the public API prefix."""
    owner = db_session.query(User).filter(
        User.username == "user@example.com").first()
    assert owner is not None

    story = Story(
        title="Delete Me",
        story_outline="A story to remove.",
        genre="fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    response = client.delete(
        f"/api/v1/stories/{story.id}",
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 204
    assert db_session.query(Story).filter(Story.id == story.id).first() is None


def test_story_list_omits_pages_but_detail_includes_them(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Contract Check",
        story_outline="A story used to verify list and detail payloads.",
        genre="fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    page = Page(
        story_id=story.id,
        page_number=1,
        text="Once upon a payload.",
        image_description="A contract verification scene.",
        image_path="images/user_1/story_1/page1.png",
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    list_response = client.get(
        "/api/v1/stories/",
        headers=regular_user_auth_headers,
    )

    assert list_response.status_code == 200
    list_item = next(
        item for item in list_response.json() if item["id"] == story.id
    )
    assert "pages" not in list_item

    detail_response = client.get(
        f"/api/v1/stories/{story.id}",
        headers=regular_user_auth_headers,
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert "pages" in detail_payload
    assert len(detail_payload["pages"]) == 1
    assert detail_payload["pages"][0]["id"] == page.id
    assert detail_payload["pages"][0]["story_id"] == story.id
    assert detail_payload["pages"][0]["page_number"] == 1
    assert detail_payload["pages"][0]["text"] == "Once upon a payload."
    assert detail_payload["pages"][0]["image_description"] == (
        "A contract verification scene."
    )
    assert detail_payload["pages"][0]["image_path"] == (
        "images/user_1/story_1/page1.png"
    )


def test_delete_story_via_api_prefix_removes_story_images(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
    monkeypatch,
    tmp_path,
):
    """Deleting a story should remove its generated image directory."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_mod._settings_instance = None
    settings_mod.get_settings()

    owner = db_session.query(User).filter(
        User.username == "user@example.com").first()
    assert owner is not None

    story = Story(
        title="Delete Images Too",
        story_outline="A story with generated assets.",
        genre="fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    story_dir = storage_paths.story_images_abs(owner.id, story.id)
    os.makedirs(story_dir, exist_ok=True)
    with open(os.path.join(story_dir, "page_1.png"), "wb") as image_file:
        image_file.write(b"image-bytes")

    response = client.delete(
        f"/api/v1/stories/{story.id}",
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 204
    assert db_session.query(Story).filter(Story.id == story.id).first() is None
    assert not os.path.exists(story_dir)


def test_save_story_editor_via_api_prefix(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com").first()
    assert owner is not None

    story = Story(
        title="Editor API",
        story_outline="A story to edit.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        editor_settings={
            "font_family": "storybook",
            "font_size": 28,
            "font_color": "#ffffff",
            "text_position": "bottom",
            "text_box_opacity": 0.6,
            "layout_mode": "full-page-overlay",
        },
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)
    page = __import__("backend.database", fromlist=["Page"]).Page(
        story_id=story.id,
        page_number=1,
        text="Original text",
        image_description="page image",
        image_path="images/user_1/story_1/page1.png",
        editor_state={
            "original_text": "Original text",
            "original_image_path": "images/user_1/story_1/page1.png",
        },
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    response = client.put(
        f"/api/v1/stories/{story.id}/editor",
        headers=regular_user_auth_headers,
        json={
            "title": "Edited Through API",
            "editor_settings": {
                "font_family": "classic",
                "font_size": 32,
                "font_color": "#ffeeaa",
                "text_position": "top",
                "text_box_opacity": 0.5,
                "layout_mode": "horizontal-split",
            },
            "pages": [
                {
                    "id": page.id,
                    "text": "Edited through API",
                    "editor_state": {
                        "text_position": "left",
                        "font_size": 24,
                        "font_color": "#123456",
                    }
                }
            ]
        }
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Edited Through API"
    assert data["editor_settings"]["layout_mode"] == "horizontal-split"
    updated_page = next(
        item for item in data["pages"] if item["id"] == page.id)
    assert updated_page["text"] == "Edited through API"
    assert updated_page["editor_state"]["text_position"] == "left"


def test_save_story_editor_via_api_prefix_returns_404_for_unknown_page_id(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Editor Unknown Page",
        story_outline="A story with one editable page.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    page = __import__("backend.database", fromlist=["Page"]).Page(
        story_id=story.id,
        page_number=1,
        text="Original text",
        image_description="page image",
        image_path="images/user_1/story_1/page1.png",
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    response = client.put(
        f"/api/v1/stories/{story.id}/editor",
        headers=regular_user_auth_headers,
        json={
            "pages": [
                {
                    "id": page.id + 999,
                    "text": "Should fail",
                }
            ]
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Page not found"}


def test_create_new_story_returns_500_when_task_creation_fails(
    client: TestClient,
    regular_user_auth_headers: dict,
    monkeypatch,
):
    mock_story = MagicMock(id=123)
    monkeypatch.setattr(
        "backend.public_router.crud.get_story_by_title_and_owner",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(
        "backend.public_router.crud.create_story_db_entry",
        MagicMock(return_value=mock_story),
    )
    monkeypatch.setattr(
        "backend.public_router.crud.create_story_generation_task",
        MagicMock(return_value=None),
    )

    response = client.post(
        "/api/v1/stories/",
        headers=regular_user_auth_headers,
        json={
            "title": "Task Failure",
            "genre": "fantasy",
            "story_outline": "A route-level failure case.",
            "main_characters": [],
            "num_pages": 1,
            "image_style": "cartoon",
        },
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Could not create generation task."}


def test_restore_story_page_image_returns_404_for_unknown_page_id(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Restore Missing Image",
        story_outline="A story with one page.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    page = Page(
        story_id=story.id,
        page_number=1,
        text="Original text",
        image_description="page image",
        image_path="images/user_1/story_1/page1.png",
        editor_state={
            "original_image_path": "images/user_1/story_1/page1.png",
        },
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    response = client.post(
        f"/api/v1/stories/{story.id}/pages/{page.id + 999}/restore-image",
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Page not found"}


def test_regenerate_story_page_image_returns_502_when_generation_returns_none(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Regenerate Failure",
        story_outline="A story to edit.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        image_style="Default",
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    page = Page(
        story_id=story.id,
        page_number=1,
        text="A dragon by the sea",
        image_description="Dragon scene",
        image_path="images/user_1/story_1/page1.png",
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    with patch(
        "backend.public_router.ai_services.generate_image_for_page",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = None
        response = client.post(
            f"/api/v1/stories/{story.id}/pages/{page.id}/regenerate-image",
            headers=regular_user_auth_headers,
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Image generation did not return a new page image.",
    }


def test_create_new_story_rejects_missing_or_unowned_character_ids(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    other_user = db_session.query(User).filter(
        User.username == "admin@example.com"
    ).first()
    assert owner is not None
    assert other_user is not None

    owned_character = Character(
        user_id=owner.id,
        name="Owned Hero",
        description="Brave",
    )
    unowned_character = Character(
        user_id=other_user.id,
        name="Someone Else",
        description="Off limits",
    )
    db_session.add(owned_character)
    db_session.add(unowned_character)
    db_session.commit()
    db_session.refresh(owned_character)
    db_session.refresh(unowned_character)

    response = client.post(
        "/api/v1/stories/",
        headers=regular_user_auth_headers,
        json={
            "title": "Invalid Character Selection",
            "genre": "fantasy",
            "story_outline": "A story request with invalid selected characters.",
            "main_characters": [],
            "character_ids": [
                owned_character.id,
                unowned_character.id,
                999999,
            ],
            "num_pages": 1,
            "image_style": "cartoon",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Character not found"}


def test_story_page_image_endpoint_requires_auth(
    client: TestClient,
    db_session: Session,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Private Image",
        story_outline="Only owners should see this.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    image_rel = f"images/user_{owner.id}/story_{story.id}/page_1.png"
    image_abs = storage_paths.resolve_data_path(image_rel)
    os.makedirs(os.path.dirname(image_abs), exist_ok=True)
    with open(image_abs, "wb") as image_file:
        image_file.write(b"private-image")

    page = __import__("backend.database", fromlist=["Page"]).Page(
        story_id=story.id,
        page_number=1,
        text="Page text",
        image_description="Scene",
        image_path=image_rel,
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    response = client.get(f"/api/v1/stories/{story.id}/pages/{page.id}/image")

    assert response.status_code == 401


def test_story_page_image_endpoint_enforces_story_ownership(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
    admin_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = Story(
        title="Private Image",
        story_outline="Only owners should see this.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    image_rel = f"images/user_{owner.id}/story_{story.id}/page_1.png"
    image_abs = storage_paths.resolve_data_path(image_rel)
    os.makedirs(os.path.dirname(image_abs), exist_ok=True)
    with open(image_abs, "wb") as image_file:
        image_file.write(b"private-image")

    page = __import__("backend.database", fromlist=["Page"]).Page(
        story_id=story.id,
        page_number=1,
        text="Page text",
        image_description="Scene",
        image_path=image_rel,
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    owner_response = client.get(
        f"/api/v1/stories/{story.id}/pages/{page.id}/image",
        headers=regular_user_auth_headers,
    )
    other_user_response = client.get(
        f"/api/v1/stories/{story.id}/pages/{page.id}/image",
        headers=admin_auth_headers,
    )
    legacy_public_response = client.get(f"/static_content/{image_rel}")

    assert owner_response.status_code == 200
    assert owner_response.content == b"private-image"
    assert other_user_response.status_code == 403
    assert legacy_public_response.status_code == 404


def test_regenerate_story_page_image_uses_text_position_guidance(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(
        User.username == "user@example.com").first()
    assert owner is not None

    story = Story(
        title="Regenerate API",
        story_outline="A story to edit.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        image_style="Default",
        editor_settings={
            "font_family": "storybook",
            "font_size": 28,
            "font_color": "#ffffff",
            "text_position": "bottom",
            "text_box_opacity": 0.6,
        },
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)
    page = __import__("backend.database", fromlist=["Page"]).Page(
        story_id=story.id,
        page_number=1,
        text="A dragon by the sea",
        image_description="Dragon scene",
        image_path="images/user_1/story_1/page1.png",
        editor_state={
            "original_text": "A dragon by the sea",
            "original_image_path": "images/user_1/story_1/page1.png",
            "text_position": "top",
        },
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    with patch("backend.public_router.ai_services.generate_image_for_page", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "images/user_1/story_1/new-page1.png"
        response = client.post(
            f"/api/v1/stories/{story.id}/pages/{page.id}/regenerate-image",
            headers=regular_user_auth_headers,
        )

    assert response.status_code == 200, response.text
    assert response.json()[
        "image_path"] == "images/user_1/story_1/new-page1.png"
    assert "top area" in mock_generate.await_args.kwargs["page_content"]
