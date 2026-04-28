import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.database import DynamicList, DynamicListItem, Story, User
from unittest.mock import AsyncMock, patch


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
            },
            "pages": [
                {
                    "id": page.id,
                    "text": "Edited through API",
                    "editor_state": {
                        "text_position": "left",
                        "font_size": 24,
                        "font_color": "#123456",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Edited Through API"
    updated_page = next(
        item for item in data["pages"] if item["id"] == page.id)
    assert updated_page["text"] == "Edited through API"
    assert updated_page["editor_state"]["text_position"] == "left"


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
