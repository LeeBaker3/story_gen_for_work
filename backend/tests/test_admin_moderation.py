from datetime import datetime, timedelta
from typing import List
from backend.database import AdminAuditEvent, Story, User
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
    payload = resp.json()
    assert payload["total"] >= 2
    items: List[dict] = payload["items"]
    assert any(it["id"] == s1.id for it in items)
    assert any(it["id"] == s2.id for it in items)

    # Hide s1
    resp = client.patch(
        f"/api/v1/admin/moderation/stories/{s1.id}/hide", headers=admin_auth_headers, json={"is_hidden": True})
    assert resp.status_code == 200
    assert resp.json()["is_hidden"] is True
    hide_audit = db_session.query(AdminAuditEvent).filter(
        AdminAuditEvent.event_type == "story_visibility_change",
        AdminAuditEvent.target_id == s1.id,
    ).one()
    assert hide_audit.metadata_json == {
        "story_id": s1.id,
        "changed_fields": ["is_hidden"],
    }

    # Now list without include_hidden should exclude s1
    resp = client.get("/api/v1/admin/moderation/stories",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()["items"]]
    assert s1.id not in ids

    # List with include_hidden should include s1
    resp = client.get(
        "/api/v1/admin/moderation/stories?include_hidden=true", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()["items"]]
    assert s1.id in ids

    # Soft delete s2
    resp = client.delete(
        f"/api/v1/admin/moderation/stories/{s2.id}", headers=admin_auth_headers)
    assert resp.status_code == 204
    delete_audit = db_session.query(AdminAuditEvent).filter(
        AdminAuditEvent.event_type == "story_soft_delete",
        AdminAuditEvent.target_id == s2.id,
    ).one()
    assert delete_audit.metadata_json == {
        "story_id": s2.id,
        "changed_fields": ["is_deleted"],
    }

    # Listing without include_deleted should exclude s2
    resp = client.get("/api/v1/admin/moderation/stories",
                      headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()["items"]]
    assert s2.id not in ids

    # Listing with include_deleted includes s2
    resp = client.get(
        "/api/v1/admin/moderation/stories?include_deleted=true", headers=admin_auth_headers)
    assert resp.status_code == 200
    ids = [it["id"] for it in resp.json()["items"]]
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
    audit_event = db_session.query(AdminAuditEvent).filter(
        AdminAuditEvent.event_type == "user_soft_delete",
        AdminAuditEvent.target_id == u.id,
    ).one()
    assert audit_event.metadata_json == {
        "user_id": u.id,
        "changed_fields": ["is_active", "is_deleted"],
    }

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


def test_moderation_list_returns_empty_paginated_envelope(
    client,
    admin_auth_headers,
):
    """Test that the admin moderation list returns an empty envelope with totals."""

    response = client.get(
        "/api/v1/admin/moderation/stories",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }


def test_moderation_list_returns_total_and_paginated_items(
    client,
    db_session,
    admin_auth_headers,
):
    """Test that the admin moderation list preserves total across pagination."""

    regular_user: User = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()

    first_story = _make_story(db_session, regular_user.id, title="Story One")
    second_story = _make_story(db_session, regular_user.id, title="Story Two")

    response = client.get(
        "/api/v1/admin/moderation/stories",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert len(payload["items"]) == 2
    assert {item["id"] for item in payload["items"]} == {
        first_story.id,
        second_story.id,
    }

    paginated_response = client.get(
        "/api/v1/admin/moderation/stories?page_size=1",
        headers=admin_auth_headers,
    )

    assert paginated_response.status_code == 200
    paginated_payload = paginated_response.json()
    assert paginated_payload["total"] == 2
    assert paginated_payload["page"] == 1
    assert paginated_payload["page_size"] == 1
    assert len(paginated_payload["items"]) == 1
