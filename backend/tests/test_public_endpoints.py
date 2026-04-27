import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend.database import DynamicList, DynamicListItem, Story, User


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
