from datetime import datetime, timedelta
from typing import List
from backend.database import Story, User
from backend.schemas import StoryGenre


def _make_story(db, owner_id: int, title: str = "T", is_draft: bool = False, created_at: datetime | None = None):
    s = Story(
        title=title,
        genre=StoryGenre.DRAMA.value,
        story_outline="o",
        main_characters=[],
        num_pages=1,
        tone=None,
        setting=None,
        image_style=None,
        word_to_picture_ratio=None,
        text_density=None,
        is_draft=is_draft,
        generated_at=None,
        owner_id=owner_id,
        is_hidden=False,
        is_deleted=False,
        created_at=created_at or datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_moderation_list_hide_delete_flow(client, db_session, admin_auth_headers):
    # Arrange: create stories for both users
    admin_user: User = db_session.query(User).filter(
        User.username == "admin@example.com").first()
    regular_user: User = db_session.query(User).filter(
        User.username == "user@example.com").first()

    s1 = _make_story(db_session, admin_user.id,
                     title="Admin Gen", is_draft=False)
    s2 = _make_story(db_session, regular_user.id,
                     title="User Draft", is_draft=True)

    # List stories (default filters: exclude hidden/deleted)
    resp = client.get("/api/v1/admin/moderation/stories",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    items: List[dict] = resp.json()
    assert any(it["id"] == s1.id for it in items)
    assert any(it["id"] == s2.id for it in items)

    # Hide s1
    resp = client.patch(
        f"/api/v1/admin/moderation/stories/{s1.id}/hide", headers=admin_auth_headers, json={"is_hidden": True})
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is True

    # Now list without include_hidden should exclude s1
    resp = client.get("/api/v1/admin/moderation/stories",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert s1.id not in ids

    # List with include_hidden should include s1
    resp = client.get(
        "/api/v1/admin/moderation/stories?include_hidden=true", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert s1.id in ids

    # Soft delete s2
    resp = client.delete(
        f"/api/v1/admin/moderation/stories/{s2.id}", headers=admin_auth_headers)
    assert resp.status_code == 204

    # Listing without include_deleted should exclude s2
    resp = client.get("/api/v1/admin/moderation/stories",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert s2.id not in ids

    # Listing with include_deleted includes s2
    resp = client.get(
        "/api/v1/admin/moderation/stories?include_deleted=true", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert s2.id in ids


def test_admin_soft_delete_user_endpoint(client, db_session, admin_auth_headers):
    # Create a throwaway user to delete
    u = User(
        username="temp@example.com",
        email="temp@example.com",
        hashed_password="x",
        role="user",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    resp = client.delete(
        f"/api/v1/admin/management/users/{u.id}", headers=admin_auth_headers)
    assert resp.status_code == 204

    # Verify hidden from admin list by default
    resp = client.get("/api/v1/admin/management/users/",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()]
    assert u.id not in ids

    # Can't delete self
    admin_user: User = db_session.query(User).filter(
        User.username == "admin@example.com").first()
    resp = client.delete(
        f"/api/v1/admin/management/users/{admin_user.id}", headers=admin_auth_headers)
    assert resp.status_code == 403
