"""Single-worker polling entrypoint for split story generation."""

from __future__ import annotations

import asyncio
import socket
from datetime import datetime, timedelta, timezone

from backend import crud, database, schemas, story_generation_service
from backend.database import SessionLocal
from backend.logging_config import app_logger, error_logger
from backend.runtime_alerting import send_high_severity_runtime_alert
from backend.settings import get_settings


def _recover_stale_in_progress_tasks(
    db,
    *,
    stale_after_seconds: int,
) -> int:
    """Fail stale in-progress tasks so the single worker can recover cleanly."""

    stale_before = datetime.now(timezone.utc) - timedelta(
        seconds=stale_after_seconds,
    )
    stale_tasks = (
        db.query(database.StoryGenerationTask)
        .filter(
            database.StoryGenerationTask.status
            == schemas.GenerationTaskStatus.IN_PROGRESS.value,
            database.StoryGenerationTask.updated_at < stale_before,
        )
        .all()
    )

    for task in stale_tasks:
        crud.update_story_generation_task(
            db,
            task.id,
            status=schemas.GenerationTaskStatus.FAILED,
            current_step=schemas.GenerationTaskStep.FINALIZING,
            error_message=(
                "Worker marked stale in-progress task as failed during "
                "recovery"
            ),
        )
    return len(stale_tasks)


async def run_single_worker_iteration() -> bool:
    """Claim and execute at most one pending story generation task."""

    settings = get_settings()
    db = SessionLocal()
    try:
        crud.upsert_worker_heartbeat(
            db,
            runtime_id=settings.story_worker_runtime_id,
            runtime_role="worker",
            hostname=socket.gethostname(),
        )

        recovered_count = _recover_stale_in_progress_tasks(
            db,
            stale_after_seconds=settings.story_generation_stale_task_timeout_seconds,
        )
        if recovered_count:
            app_logger.warning(
                "Recovered %s stale in-progress story task(s) before polling.",
                recovered_count,
            )

        task = crud.claim_next_pending_story_generation_task(db)
        if task is None:
            return False

        story = crud.get_story(db, task.story_id, task.user_id)
        if story is None:
            crud.update_story_generation_task(
                db,
                task.id,
                status=schemas.GenerationTaskStatus.FAILED,
                current_step=schemas.GenerationTaskStep.FINALIZING,
                error_message="Story shell not found for queued generation task",
            )
            return True

        story_input = story_generation_service.reconstruct_story_input_from_story(
            story,
        )
    finally:
        db.close()

    await story_generation_service.generate_story_as_background_task(
        task.id,
        task.story_id,
        task.user_id,
        story_input,
        task.reservation_id,
    )

    db = SessionLocal()
    try:
        crud.upsert_worker_heartbeat(
            db,
            runtime_id=settings.story_worker_runtime_id,
            runtime_role="worker",
            hostname=socket.gethostname(),
        )
    finally:
        db.close()
    return True


async def run_worker_forever() -> None:
    """Poll the database and process story generation tasks serially."""

    settings = get_settings()
    app_logger.info(
        "Starting story worker in single-worker mode with poll interval %ss.",
        settings.story_generation_worker_poll_interval_seconds,
    )
    while True:
        try:
            processed = await run_single_worker_iteration()
        except Exception as exc:
            error_logger.error(
                "Unhandled error during story worker iteration.",
                exc_info=True,
            )
            send_high_severity_runtime_alert(
                source="worker",
                summary="Unhandled story worker iteration exception",
                details={
                    "runtime_id": settings.story_worker_runtime_id,
                    "exception_type": exc.__class__.__name__,
                    "message": str(exc),
                },
            )
            processed = False

        if not processed:
            await asyncio.sleep(
                settings.story_generation_worker_poll_interval_seconds,
            )


def main() -> None:
    """Run the worker loop as a standalone process."""

    settings = get_settings()
    if settings.story_generation_runtime_role == "api":
        raise RuntimeError(
            "STORY_GENERATION_RUNTIME_ROLE=api cannot run the story worker"
        )
    asyncio.run(run_worker_forever())


if __name__ == "__main__":
    main()