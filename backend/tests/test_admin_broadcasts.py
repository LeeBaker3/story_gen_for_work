from datetime import datetime, timedelta, timezone

import pytest

from backend.database import AdminBroadcast, Character, Story
from backend.database import StoryGenerationTask, User


def test_admin_broadcast_endpoints_require_admin(client, regular_user_auth_headers):
    """Non-admin users cannot access broadcast or analytics endpoints."""

    list_response = client.get(
        "/api/v1/admin/broadcasts",
        headers=regular_user_auth_headers,
    )
    create_response = client.post(
        "/api/v1/admin/broadcasts",
        headers=regular_user_auth_headers,
        json={"title": "Launch update", "message": "New feature is live."},
    )
    analytics_response = client.get(
        "/api/v1/admin/analytics",
        headers=regular_user_auth_headers,
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403
    assert analytics_response.status_code == 403


def test_admin_can_create_and_list_broadcasts(
    client,
    db_session,
    admin_auth_headers,
):
    """Admins can send a minimal broadcast and see it in history."""

    db_session.add_all(
        [
            User(
                username="extra-active@example.com",
                email="extra-active@example.com",
                hashed_password="hash",
                is_active=True,
                role="user",
            ),
            User(
                username="inactive@example.com",
                email="inactive@example.com",
                hashed_password="hash",
                is_active=False,
                role="user",
            ),
            User(
                username="deleted@example.com",
                email="deleted@example.com",
                hashed_password="hash",
                is_active=True,
                is_deleted=True,
                role="user",
            ),
        ]
    )
    db_session.commit()

    response = client.post(
        "/api/v1/admin/broadcasts",
        headers=admin_auth_headers,
        json={
            "title": "Scheduled maintenance",
            "message": "Story generation will be read-only for 15 minutes.",
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["title"] == "Scheduled maintenance"
    assert payload["message"] == (
        "Story generation will be read-only for 15 minutes."
    )
    assert payload["status"] == "sent"
    assert payload["target_scope"] == "all_active_users"
    assert payload["recipient_count"] == 3

    list_response = client.get(
        "/api/v1/admin/broadcasts",
        headers=admin_auth_headers,
    )
    assert list_response.status_code == 200, list_response.text
    broadcasts = list_response.json()
    assert len(broadcasts) == 1
    assert broadcasts[0]["id"] == payload["id"]


def test_admin_analytics_summary_reports_recent_usage(
    client,
    db_session,
    admin_auth_headers,
):
    """Analytics summary aggregates recent usage and broadcast totals."""

    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=2)
    old = now - timedelta(days=40)

    admin_user = db_session.query(User).filter(
        User.username == "admin@example.com"
    ).first()
    regular_user = db_session.query(User).filter(
        User.username == "user@example.com"
    ).first()

    admin_user.created_at = old
    regular_user.created_at = old

    recent_user = User(
        username="recent@example.com",
        email="recent@example.com",
        hashed_password="hash",
        is_active=True,
        role="user",
        created_at=recent,
    )
    db_session.add(recent_user)
    db_session.commit()
    db_session.refresh(recent_user)

    recent_generated = Story(
        title="Generated",
        genre="Action",
        story_outline="Outline",
        main_characters=[],
        num_pages=5,
        owner_id=admin_user.id,
        is_draft=False,
        created_at=recent,
        generated_at=recent,
    )
    recent_draft = Story(
        title="Draft",
        genre="Action",
        story_outline="Outline",
        main_characters=[],
        num_pages=5,
        owner_id=regular_user.id,
        is_draft=True,
        created_at=recent,
    )
    old_story = Story(
        title="Old",
        genre="Action",
        story_outline="Outline",
        main_characters=[],
        num_pages=5,
        owner_id=admin_user.id,
        is_draft=False,
        created_at=old,
        generated_at=old,
    )
    db_session.add_all([recent_generated, recent_draft, old_story])
    db_session.commit()
    db_session.refresh(recent_generated)

    db_session.add_all(
        [
            Character(user_id=admin_user.id,
                      name="Recent Character", created_at=recent),
            Character(user_id=admin_user.id,
                      name="Old Character", created_at=old),
            StoryGenerationTask(
                id="recent-complete",
                story_id=recent_generated.id,
                user_id=admin_user.id,
                status="completed",
                progress=100,
                current_step="done",
                created_at=recent,
                updated_at=recent,
            ),
            StoryGenerationTask(
                id="recent-failed",
                story_id=recent_generated.id,
                user_id=admin_user.id,
                status="failed",
                progress=100,
                current_step="done",
                created_at=recent,
                updated_at=recent,
            ),
            StoryGenerationTask(
                id="old-complete",
                story_id=old_story.id,
                user_id=admin_user.id,
                status="completed",
                progress=100,
                current_step="done",
                created_at=old,
                updated_at=old,
            ),
            AdminBroadcast(
                title="Recent broadcast",
                message="Recent update",
                target_scope="all_active_users",
                status="sent",
                recipient_count=4,
                created_by_user_id=admin_user.id,
                created_at=recent,
                sent_at=recent,
            ),
            AdminBroadcast(
                title="Old broadcast",
                message="Old update",
                target_scope="all_active_users",
                status="sent",
                recipient_count=10,
                created_by_user_id=admin_user.id,
                created_at=old,
                sent_at=old,
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/admin/analytics",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == {
        "users_registered_last_7d": 1,
        "stories_created_last_7d": 2,
        "stories_generated_last_7d": 1,
        "characters_created_last_7d": 1,
        "active_story_authors_last_7d": 2,
        "generation_success_rate_last_7d": pytest.approx(0.5),
        "broadcasts_sent_last_30d": 1,
        "broadcast_recipients_last_30d": 4,
    }
