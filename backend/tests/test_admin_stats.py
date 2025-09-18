import pytest
from datetime import datetime, timedelta, timezone
from backend.database import StoryGenerationTask, Story, User
from backend import schemas


def create_story(db, user_id: int, is_draft: bool):
    s = Story(
        # Title column is non-nullable in current schema, so always provide one
        title="Draft Story" if is_draft else "Generated Story",
        genre="Action",
        story_outline="Outline",
        main_characters=[],
        num_pages=5,
        owner_id=user_id,
        is_draft=is_draft,
        generated_at=datetime.now(timezone.utc) if not is_draft else None,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def create_task(db, story_id: int, user_id: int, status: str, created_offset_minutes: int = 0, duration_seconds: int = 30):
    created_at = datetime.now(timezone.utc) - \
        timedelta(minutes=created_offset_minutes)
    updated_at = created_at + timedelta(seconds=duration_seconds)
    t = StoryGenerationTask(
        id=f"task-{story_id}-{status}-{created_offset_minutes}",
        story_id=story_id,
        user_id=user_id,
        status=status,
        progress=100 if status == 'completed' else 0,
        current_step='finalizing',
        created_at=created_at,
        updated_at=updated_at,
    )
    db.add(t)
    db.commit()
    return t


def test_admin_stats_authorization(client, regular_user_auth_headers):
    # Regular user should be forbidden
    r = client.get("/api/v1/admin/stats", headers=regular_user_auth_headers)
    assert r.status_code == 403


def test_admin_stats_happy_path(client, db_session, admin_auth_headers):
    # Prepare some data
    admin_user = db_session.query(User).filter(
        User.username == "admin@example.com").first()

    draft = create_story(db_session, admin_user.id, is_draft=True)
    story = create_story(db_session, admin_user.id, is_draft=False)

    # Tasks: one completed, one failed, one in progress inside 24h
    create_task(db_session, story.id, admin_user.id, 'completed',
                created_offset_minutes=10, duration_seconds=42)
    create_task(db_session, story.id, admin_user.id, 'failed',
                created_offset_minutes=20, duration_seconds=15)
    create_task(db_session, story.id, admin_user.id, 'in_progress',
                created_offset_minutes=5, duration_seconds=5)

    r = client.get("/api/v1/admin/stats", headers=admin_auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()

    # Basic shape assertions
    expected_keys = {
        'total_users', 'active_users', 'total_stories', 'generated_stories', 'draft_stories', 'total_characters',
        'tasks_last_24h', 'tasks_in_progress', 'tasks_failed_last_24h', 'tasks_completed_last_24h',
        'avg_task_duration_seconds_last_24h', 'success_rate_last_24h', 'avg_attempts_last_24h'
    }
    assert set(data.keys()) == expected_keys

    assert data['total_users'] >= 1
    assert data['total_stories'] == 2
    assert data['generated_stories'] == 1
    assert data['draft_stories'] == 1
    assert data['tasks_last_24h'] == 3
    assert data['tasks_in_progress'] == 1
    assert data['tasks_failed_last_24h'] == 1
    assert data['tasks_completed_last_24h'] == 1
    # Success rate: completed / (completed + failed) = 1 / 2 = 0.5
    assert data['success_rate_last_24h'] == pytest.approx(0.5)
    # Avg duration approximated; ensure positive
    if data['avg_task_duration_seconds_last_24h'] is not None:
        assert data['avg_task_duration_seconds_last_24h'] > 0
    # Avg attempts is present (may be null if no completed tasks)
    assert 'avg_attempts_last_24h' in data
