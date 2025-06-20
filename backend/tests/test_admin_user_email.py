import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from backend import crud


def get_token(client: TestClient, username, password):
    response = client.post(
        "/token", data={"username": username, "password": password})
    assert response.status_code == 200, f"Failed to get token for {username}. Response: {response.json()}"
    return response.json()["access_token"]


def test_admin_can_update_user_details(client: TestClient, db_session: Session):
    token = get_token(client, "admin@example.com", "adminpassword")

    user_to_update = crud.get_user_by_username(db_session, "user@example.com")
    assert user_to_update is not None, "Test user 'user@example.com' not found in the database."
    user_id = user_to_update.id

    updated_details = {
        "username": "updateduser",
        "email": "updateduser@example.com",
        "role": "user",
        "is_active": False
    }
    response = client.put(
        f"/api/v1/admin/management/users/{user_id}",
        json=updated_details,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["username"] == updated_details["username"]
    assert response_json["email"] == updated_details["email"]
    assert response_json["role"] == updated_details["role"]
    assert response_json["is_active"] == updated_details["is_active"]


def test_update_nonexistent_user_details_returns_404(client: TestClient):
    token = get_token(client, "admin@example.com", "adminpassword")
    response = client.put(
        "/api/v1/admin/management/users/999999",
        json={"email": "noone@example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404


def test_non_admin_cannot_update_user_details(client: TestClient, db_session: Session):
    token = get_token(client, "user@example.com", "userpassword")

    admin_user = crud.get_user_by_username(db_session, "admin@example.com")
    assert admin_user is not None, "Admin user 'admin@example.com' not found in the database."
    user_id = admin_user.id

    response = client.put(
        f"/api/v1/admin/management/users/{user_id}",
        json={"email": "hacker@example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
