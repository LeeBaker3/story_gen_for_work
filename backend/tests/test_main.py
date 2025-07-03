import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.main import app
from backend import auth, schemas
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
