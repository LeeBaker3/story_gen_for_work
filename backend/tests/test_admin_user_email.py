import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal, Base, engine
from backend import database
from backend import crud
from backend.schemas import UserCreate
from backend.tests.conftest import override_get_db, TestingSessionLocal, setup_test_db
import os
from sqlalchemy import text

# Remove old test DB if exists (ensure clean state)
if os.path.exists("./test.db"):
    os.remove("./test.db")

# Override the app's get_db dependency to use the test DB
app.dependency_overrides[database.get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_users():
    db = TestingSessionLocal()
    # Clean up users if they exist
    db.execute(
        text("DELETE FROM users WHERE username IN ('adminuser', 'testuser')"))
    db.commit()
    # Create admin
    admin = crud.get_user_by_username(db, "adminuser")
    if not admin:
        admin = crud.create_user(db, UserCreate(
            username="adminuser", email="admin@example.com", password="adminpass", role="admin"))
    # Create regular user
    user = crud.get_user_by_username(db, "testuser")
    if not user:
        user = crud.create_user(db, UserCreate(
            username="testuser", email="testuser@example.com", password="testpass", role="user"))
    db.commit()
    db.close()


def get_token(username, password):
    response = client.post(
        "/token", data={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_update_user_email(setup_test_db, setup_test_users):
    token = get_token("adminuser", "adminpass")
    new_email = "updateduser@example.com"
    user_id = 2  # testuser's ID (assuming auto-increment and only two users)
    response = client.patch(f"/admin/users/{user_id}", json={
                            "email": new_email}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == new_email


def test_update_nonexistent_user_returns_404(setup_test_db, setup_test_users):
    token = get_token("adminuser", "adminpass")
    response = client.patch(f"/admin/users/999999", json={
                            "email": "noone@example.com"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_non_admin_cannot_update_user_email(setup_test_db, setup_test_users):
    token = get_token("testuser", "testpass")
    user_id = 2  # testuser's ID
    response = client.patch(f"/admin/users/{user_id}", json={
                            "email": "hacker@example.com"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
