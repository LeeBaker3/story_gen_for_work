"""Regression tests for story generation task timestamp handling."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend import crud, database, schemas


def test_update_story_generation_task_handles_mixed_naive_aware_datetimes(
    db_session: Session,
) -> None:
    """Ensure duration_ms computation handles naive/aware timestamp mixes.

    SQLite frequently returns timezone-naive datetimes even when SQLAlchemy
    columns are declared with timezone=True. Our CRUD layer should normalize
    timestamps to UTC before doing arithmetic.
    """
    user = (
        db_session.query(database.User)
        .filter(database.User.username == "user@example.com")
        .first()
    )
    assert user is not None

    story = database.Story(
        title="Test Story",
        genre="Fantasy",
        num_pages=1,
        owner_id=user.id,
        is_draft=True,
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    task = database.StoryGenerationTask(
        id="task-1",
        user_id=user.id,
        story_id=story.id,
        status=schemas.GenerationTaskStatus.IN_PROGRESS.value,
        progress=50,
        current_step=schemas.GenerationTaskStep.GENERATING_TEXT.value,
        started_at=datetime(2026, 1, 1, 0, 0, 0),  # naive
        completed_at=datetime(2026, 1, 1, 0, 0, 3,
                              tzinfo=timezone.utc),  # aware
    )

    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    updated = crud.update_story_generation_task(
        db_session,
        task_id=task.id,
        status=schemas.GenerationTaskStatus.COMPLETED,
    )

    assert updated.duration_ms == 3000
