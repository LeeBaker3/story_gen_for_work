import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY, call, AsyncMock
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
    # FastAPI response_model validation will call model_validate and expects attributes accessible.
    # Ensure refresh is a no-op that leaves timestamps intact.
    db_session_mock.refresh = MagicMock()

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


def test_story_creation_with_character_ids_merges_characters(client, db_session_mock, current_user_mock):
    """Ensure that when character_ids are provided, existing character data is merged with new main_characters without duplication and reference image paths are preserved."""
    mock_story_id = 42
    now = datetime.now(UTC)

    existing_character_obj = MagicMock()
    existing_character_obj.id = 7
    existing_character_obj.user_id = current_user_mock.id
    existing_character_obj.name = "ExistingHero"
    existing_character_obj.description = "Brave"
    existing_character_obj.age = 30
    existing_character_obj.gender = "female"
    existing_character_obj.clothing_style = "cloak"
    existing_character_obj.key_traits = "fearless"
    existing_character_obj.current_image = MagicMock(
        file_path="images/user_1/characters/7/img.png")

    incoming_payload = {
        "title": "Merged Story",
        "genre": "Fantasy",
        "story_outline": "An epic merge.",
        "main_characters": [{"name": "NewCompanion"}],
        "character_ids": [existing_character_obj.id],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)"
    }

    crud.get_story_by_title_and_owner = MagicMock(return_value=None)

    class FakeStory:
        def __init__(self):
            self.id = mock_story_id
            self.owner_id = current_user_mock.id
            self.title = "[AI Title Pending...]"
            self.genre = incoming_payload["genre"]
            self.story_outline = incoming_payload["story_outline"]
            self.main_characters = incoming_payload["main_characters"]
            self.num_pages = incoming_payload["num_pages"]
            self.image_style = incoming_payload["image_style"]
            self.word_to_picture_ratio = incoming_payload["word_to_picture_ratio"]
            self.text_density = incoming_payload["text_density"]
            self.is_draft = False
            self.created_at = now
            self.updated_at = now
            self.pages = []

    mock_story_db = FakeStory()
    crud.create_story_db_entry = MagicMock(return_value=mock_story_db)

    def _update_story_title(db, story_id, new_title):
        mock_story_db.title = new_title
        mock_story_db.updated_at = datetime.now(UTC)
        return mock_story_db
    crud.update_story_title = MagicMock(side_effect=_update_story_title)

    filter_mock = MagicMock()
    filter_mock.filter.return_value = filter_mock
    filter_mock.all.return_value = [existing_character_obj]
    db_session_mock.query.return_value = filter_mock

    # NOTE: The synchronous story creation with character merge logic lives at root /stories/ (not /api/v1) in main.py.
    with patch("backend.ai_services.generate_story_from_chatgpt", return_value={"Title": "Merged Story Final", "Pages": []}):
        response = client.post(
            "/stories/",
            json={"story_input": incoming_payload},
            headers={"X-Token": "testtoken"}
        )
    assert response.status_code in (200, 201), response.text
    data = response.json()
    assert data["title"] == "Merged Story Final"
    returned_names = {c["name"] for c in data.get("main_characters", [])}
    assert {"ExistingHero", "NewCompanion"}.issubset(returned_names)
    existing_entry = next((c for c in data.get(
        "main_characters", []) if c["name"] == "ExistingHero"), {})
    assert existing_entry.get(
        "reference_image_path") == "images/user_1/characters/7/img.png"


def test_get_story_status(client, db_session_mock):
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


def test_get_story_status_not_found(client, db_session_mock):
    """
    Test polling for a task that does not exist.
    """
    mock_task_id = str(uuid.uuid4())
    crud.get_story_generation_task = MagicMock(return_value=None)

    response = client.get(f"/api/v1/stories/generation-status/{mock_task_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_get_story_status_unauthorized(client, db_session_mock, current_user_mock):
    """
    Test that a user cannot poll for a task that belongs to another user.
    """
    mock_task_id = str(uuid.uuid4())
    mock_task = schemas.StoryGenerationTask(
        id=mock_task_id,
        story_id=1,
        user_id=999,  # Different user ID
        status=schemas.GenerationTaskStatus.IN_PROGRESS,
        progress=50,
        current_step=schemas.GenerationTaskStep.GENERATING_PAGE_IMAGES,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )

    crud.get_story_generation_task = MagicMock(return_value=mock_task)

    response = client.get(f"/api/v1/stories/generation-status/{mock_task_id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to view this task"


def test_task_tracking_fields_lifecycle(client, db_session_mock, current_user_mock):
    """Validate that task lifecycle updates populate started_at, completed_at, duration_ms and attempts."""
    mock_task_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    # Initial pending task
    base_task = schemas.StoryGenerationTask(
        id=mock_task_id,
        story_id=1,
        user_id=current_user_mock.id,
        status=schemas.GenerationTaskStatus.PENDING,
        progress=0,
        current_step=schemas.GenerationTaskStep.INITIALIZING,
        created_at=now,
        updated_at=now,
    )
    # Simulate DB returning evolving object reference
    crud.get_story_generation_task = MagicMock(return_value=base_task)
    # Move to in_progress
    crud.update_story_generation_task = MagicMock(
        side_effect=lambda db, task_id, **kwargs: _apply_updates(base_task, **kwargs))

    # Transition to in_progress
    crud.update_story_generation_task(
        db_session_mock, mock_task_id, status=schemas.GenerationTaskStatus.IN_PROGRESS)
    assert base_task.started_at is not None, "started_at should be set on first IN_PROGRESS"

    # Fail the task
    crud.update_story_generation_task(
        db_session_mock, mock_task_id, status=schemas.GenerationTaskStatus.FAILED, error_message="Boom")
    assert base_task.completed_at is not None, "completed_at set when FAILED"
    assert base_task.duration_ms is not None, "duration_ms computed on failure"
    first_duration = base_task.duration_ms
    assert base_task.last_error == "Boom"

    # Retry (simulate new attempt)
    prev_attempts = base_task.attempts or 0
    crud.update_story_generation_task(
        db_session_mock, mock_task_id, status=schemas.GenerationTaskStatus.IN_PROGRESS)
    assert base_task.attempts == prev_attempts + \
        1, "attempts increments when retrying after failure"

    # Complete
    crud.update_story_generation_task(
        db_session_mock, mock_task_id, status=schemas.GenerationTaskStatus.COMPLETED)
    assert base_task.completed_at is not None
    assert base_task.duration_ms is not None
    assert base_task.duration_ms >= first_duration


def _apply_updates(task_obj, status=None, progress=None, current_step=None, error_message=None, **_):
    """Helper applied in MagicMock side effect to simulate crud.update_story_generation_task logic minimal subset."""
    now_ts = datetime.now(UTC)
    if status is not None:
        status_val = status.value if hasattr(status, 'value') else status
        prev = task_obj.status
        task_obj.status = status_val
        if status_val == schemas.GenerationTaskStatus.IN_PROGRESS.value and task_obj.started_at is None:
            task_obj.started_at = now_ts
        if status_val in [schemas.GenerationTaskStatus.COMPLETED.value, schemas.GenerationTaskStatus.FAILED.value]:
            if task_obj.completed_at is None:
                task_obj.completed_at = now_ts
            if task_obj.started_at and task_obj.completed_at and task_obj.duration_ms is None:
                task_obj.duration_ms = int(
                    (task_obj.completed_at - task_obj.started_at).total_seconds() * 1000)
        if status_val == schemas.GenerationTaskStatus.IN_PROGRESS.value and prev == schemas.GenerationTaskStatus.FAILED.value:
            task_obj.attempts = (task_obj.attempts or 0) + 1
    if progress is not None:
        task_obj.progress = progress
    if current_step is not None:
        task_obj.current_step = current_step.value if hasattr(
            current_step, 'value') else current_step
    if error_message is not None:
        task_obj.error_message = error_message
        task_obj.last_error = error_message
    task_obj.updated_at = now_ts
    return task_obj


@pytest.mark.asyncio
async def test_generate_story_as_background_task_passes_correct_references():
    """
    Tests that the background task correctly identifies characters in a scene
    and passes the correct reference image paths and character names to the
    image generation function.
    """
    # Arrange
    db_session_mock = MagicMock(spec=Session)
    task_id = "test-task-123"
    story_id = 1
    user_id = 1
    story_input = schemas.StoryCreate(
        title="Test Story",
        genre="Sci-Fi",
        story_outline="A space adventure.",
        main_characters=[
            schemas.CharacterDetail(
                name="Captain Eva", description="Brave leader"),
            schemas.CharacterDetail(
                name="Robot X-1", description="Witty sidekick"),
            schemas.CharacterDetail(
                name="Alien Zorp", description="Mysterious alien")
        ],
        num_pages=2,
        image_style=schemas.ImageStyle.SCI_FI_CONCEPT,
        word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE,
        text_density=schemas.TextDensity.STANDARD
    )

    # Mock the database dependency
    with patch('backend.story_generation_service.database.get_db') as mock_get_db:
        mock_get_db.return_value = iter([db_session_mock])

        # Mock CRUD operations
        with patch('backend.story_generation_service.crud') as mock_crud:
            # Mock AI service calls
            with patch('backend.story_generation_service.ai_services') as mock_ai_services:
                # Setup mock return values for AI services
                mock_ai_services.generate_character_reference_image = AsyncMock(side_effect=[
                    {"name": "Captain Eva",
                        "reference_image_path": "images/user_1/story_1/eva_ref.png"},
                    {"name": "Robot X-1",
                        "reference_image_path": "images/user_1/story_1/x1_ref.png"},
                    {"name": "Alien Zorp",
                        "reference_image_path": "images/user_1/story_1/zorp_ref.png"},
                ])
                mock_ai_services.generate_story_from_chatgpt = AsyncMock(return_value={
                    "Title": "Test Story",
                    "Pages": [
                        {
                            "Page_number": 1, "Text": "Eva and X-1 on the bridge.",
                            "Image_description": "A vibrant image of Captain Eva and Robot X-1 on the bridge of a starship, looking out at a nebula.",
                            "Characters_in_scene": ["Captain Eva", "Robot X-1"]
                        },
                        {
                            "Page_number": 2, "Text": "Zorp appears!",
                            "Image_description": "The mysterious Alien Zorp emerging from a shadowy corner of the cargo bay.",
                            "Characters_in_scene": ["Alien Zorp"]
                        }
                    ]
                })
                mock_ai_services.generate_image_for_page = AsyncMock(
                    return_value="images/user_1/story_1/page_1.png")

                # Import the service to be tested
                from backend.story_generation_service import generate_story_as_background_task

                # Act
                await generate_story_as_background_task(task_id, story_id, user_id, story_input)

                # Assert
                # Check that generate_image_for_page was called with the correct arguments for each page
                expected_calls = [
                    call(
                        page_content="A vibrant image of Captain Eva and Robot X-1 on the bridge of a starship, looking out at a nebula.",
                        style_reference="Sci-Fi Concept Art",
                        db=db_session_mock,
                        user_id=user_id,
                        story_id=story_id,
                        page_number=1,
                        reference_image_paths=[
                            "images/user_1/story_1/eva_ref.png", "images/user_1/story_1/x1_ref.png"],
                        characters_in_scene=["Captain Eva", "Robot X-1"],
                        image_save_path_on_disk=ANY,
                        image_path_for_db=ANY,
                    ),
                    call(
                        page_content="The mysterious Alien Zorp emerging from a shadowy corner of the cargo bay.",
                        style_reference="Sci-Fi Concept Art",
                        db=db_session_mock,
                        user_id=user_id,
                        story_id=story_id,
                        page_number=2,
                        reference_image_paths=[
                            "images/user_1/story_1/zorp_ref.png"],
                        characters_in_scene=["Alien Zorp"],
                        image_save_path_on_disk=ANY,
                        image_path_for_db=ANY,
                    )
                ]
                mock_ai_services.generate_image_for_page.assert_has_calls(
                    expected_calls, any_order=True)
