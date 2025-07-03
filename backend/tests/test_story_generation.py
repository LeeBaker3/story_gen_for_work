import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from sqlalchemy.orm import Session
from backend.main import app
from backend import schemas, crud, auth, database
import uuid
from datetime import datetime, UTC


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def db_session_mock():
    """Mocks the database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def current_user_mock():
    """Mocks the current authenticated user."""
    now = datetime.now(UTC)
    return schemas.User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,
        role="user",
        created_at=now,
        updated_at=now
    )


@pytest.fixture
def story_create_input_mock():
    """Provides a sample StoryCreate input."""
    return {
        "title": "My Async Test Story",
        "genre": "Fantasy",
        "story_outline": "A quest for an async artifact.",
        "main_characters": [{"name": "Async Knight"}],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Standard (~60-90 words)"
    }


@pytest.fixture(autouse=True)
def mock_dependencies(db_session_mock, current_user_mock):
    """Overrides dependencies for all tests in this module."""
    def override_get_db():
        yield db_session_mock

    def override_get_current_user():
        return current_user_mock

    app.dependency_overrides[database.get_db] = override_get_db
    app.dependency_overrides[auth.get_current_user] = override_get_current_user
    yield
    app.dependency_overrides = {}


def test_create_story_generation_task_successfully(client, db_session_mock, story_create_input_mock, current_user_mock):
    """
    Test that POST /stories/ successfully creates a generation task.
    """
    mock_task_id = str(uuid.uuid4())
    mock_story_id = 1
    now = datetime.now(UTC)

    # Mock the CRUD function for creating the story placeholder
    mock_story_db = schemas.Story(
        id=mock_story_id,
        owner_id=current_user_mock.id,
        title="[Placeholder]",
        is_draft=True,
        genre=story_create_input_mock["genre"],
        story_outline=story_create_input_mock["story_outline"],
        main_characters=story_create_input_mock["main_characters"],
        num_pages=story_create_input_mock["num_pages"],
        created_at=now,
        updated_at=now
    )
    # No existing story
    crud.get_story_by_title_and_owner = MagicMock(return_value=None)
    crud.create_story_db_entry = MagicMock(return_value=mock_story_db)

    # Mock the CRUD function for creating the task
    crud.create_story_generation_task = MagicMock(return_value=schemas.StoryGenerationTask(
        id=mock_task_id,
        story_id=mock_story_id,
        user_id=current_user_mock.id,
        status=schemas.GenerationTaskStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    ))

    with patch('backend.public_router.generate_story_as_background_task') as mock_background_task:
        response = client.post(
            "/api/v1/stories/",
            json=story_create_input_mock,
            headers={"X-Token": "testtoken"}
        )
        print("Response JSON:", response.json())
        assert response.status_code == 202
        response_data = response.json()
        assert response_data["id"] is not None
        assert response_data["story_id"] == mock_story_id
        assert response_data["status"] == "pending"
        mock_background_task.assert_called_once()


def test_create_story_with_existing_title_fails(client, db_session_mock, story_create_input_mock, current_user_mock):
    """
    Test that creating a story with an existing title for the same user fails.
    """
    # Mock that a story with the same title already exists for this user
    crud.get_story_by_title_and_owner = MagicMock(
        return_value=MagicMock(spec=database.Story))

    response = client.post(
        "/api/v1/stories/",
        json=story_create_input_mock,
        headers={"X-Token": "testtoken"}
    )
    print("Response JSON:", response.json())
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_get_generation_status(client, db_session_mock):
    """
    Test polling the generation status of a task.
    """
    mock_task_id = str(uuid.uuid4())
    mock_task = schemas.StoryGenerationTask(
        id=mock_task_id,
        story_id=1,
        user_id=1,
        status=schemas.GenerationTaskStatus.IN_PROGRESS,
        progress=50,
        current_step=schemas.GenerationTaskStep.GENERATING_PAGE_IMAGES,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    crud.get_story_generation_task = MagicMock(return_value=mock_task)

    response = client.get(f"/api/v1/stories/generation-status/{mock_task_id}")

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == mock_task_id
    assert response_data["status"] == "in_progress"
    assert response_data["progress"] == 50
    assert response_data["current_step"] == "generating_page_images"


def test_get_generation_status_not_found(client, db_session_mock):
    """
    Test polling for a task that does not exist.
    """
    mock_task_id = str(uuid.uuid4())
    crud.get_story_generation_task = MagicMock(return_value=None)

    response = client.get(f"/api/v1/stories/generation-status/{mock_task_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
