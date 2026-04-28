import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from fastapi.middleware.cors import CORSMiddleware

from backend import auth, database, schemas
from backend.main import app
import backend.main as main_module
from datetime import datetime, UTC


# --- Fixtures ---


@pytest.fixture(scope="module")
def client():
    """Fixture to provide a test client for the app."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_admin_user():
    """Fixture to provide a mock admin user."""
    return schemas.User(
        id=1,
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_normal_user():
    """Fixture to provide a mock normal user."""
    return schemas.User(
        id=2,
        username="testuser",
        email="test@example.com",
        role="user",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# --- Admin User Role Management Tests ---


@patch("backend.crud.get_user_admin")
@patch("backend.crud.admin_update_user")
def test_admin_can_update_user_role(
    mock_update, mock_get, client, mock_admin_user, mock_normal_user
):
    """
    Test that an admin user can successfully update another user's role.
    This test mocks the database interactions to isolate the endpoint logic.
    """
    app.dependency_overrides[auth.get_current_admin_user] = lambda: mock_admin_user

    mock_get.return_value = mock_normal_user

    # Create a copy of the user with the updated role
    updated_user = mock_normal_user.model_copy(update={"role": "admin"})
    mock_update.return_value = updated_user

    response = client.put(
        f"/api/v1/admin/management/users/{mock_normal_user.id}",
        json={"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    mock_update.assert_called_once()

    # Clean up dependency override
    del app.dependency_overrides[auth.get_current_admin_user]


def test_non_admin_cannot_update_user_role(client, mock_normal_user):
    """
    Test that a non-admin user is forbidden from updating a user's role.
    This test relies on the `get_current_admin_user` dependency to correctly
    raise a 403 Forbidden error for users without the 'admin' role.
    """
    app.dependency_overrides[auth.get_current_user] = lambda: mock_normal_user

    response = client.put(
        f"/api/v1/admin/management/users/{mock_normal_user.id}",
        json={"role": "admin"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Admin access required"}

    # Clean up dependency override
    del app.dependency_overrides[auth.get_current_user]


def test_cors_middleware_registered():
    """Test that CORSMiddleware is registered with the configured origins."""

    cors_middleware = next(
        (
            middleware
            for middleware in app.user_middleware
            if middleware.cls is CORSMiddleware
        ),
        None,
    )

    assert cors_middleware is not None
    assert cors_middleware.kwargs["allow_origins"] == main_module.settings.cors_origins
    assert cors_middleware.kwargs["allow_credentials"] is True


def test_recover_stuck_generation_tasks_marks_tasks_failed(db_session):
    """Test that pending and in-progress tasks are failed during startup recovery."""

    owner = db_session.query(database.User).filter(
        database.User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = database.Story(
        title="Recovery Story",
        story_outline="Outline",
        genre="fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    pending_task = database.StoryGenerationTask(
        id="pending-task",
        story_id=story.id,
        user_id=owner.id,
        status=schemas.GenerationTaskStatus.PENDING.value,
        progress=0,
    )
    in_progress_task = database.StoryGenerationTask(
        id="in-progress-task",
        story_id=story.id,
        user_id=owner.id,
        status=schemas.GenerationTaskStatus.IN_PROGRESS.value,
        progress=50,
    )
    completed_task = database.StoryGenerationTask(
        id="completed-task",
        story_id=story.id,
        user_id=owner.id,
        status=schemas.GenerationTaskStatus.COMPLETED.value,
        progress=100,
    )
    db_session.add_all([pending_task, in_progress_task, completed_task])
    db_session.commit()

    recovered_count = main_module._recover_stuck_generation_tasks(db_session)

    assert recovered_count == 2

    db_session.refresh(pending_task)
    db_session.refresh(in_progress_task)
    db_session.refresh(completed_task)

    assert pending_task.status == schemas.GenerationTaskStatus.FAILED.value
    assert in_progress_task.status == schemas.GenerationTaskStatus.FAILED.value
    assert pending_task.error_message == "Server restarted during generation"
    assert in_progress_task.error_message == "Server restarted during generation"
    assert completed_task.status == schemas.GenerationTaskStatus.COMPLETED.value


def test_secure_secret_key_guard_raises_outside_testing(monkeypatch):
    """Test that startup rejects the insecure default JWT secret outside tests."""

    monkeypatch.setenv("SECRET_KEY", "your-default-secret-key")
    monkeypatch.delenv("TESTING", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY environment variable"):
        main_module._assert_secure_secret_key()


def test_secure_secret_key_guard_allows_testing(monkeypatch):
    """Test that testing mode bypasses the secret-key startup guard."""

    monkeypatch.setenv("SECRET_KEY", "your-default-secret-key")
    monkeypatch.setenv("TESTING", "true")

    main_module._assert_secure_secret_key()
