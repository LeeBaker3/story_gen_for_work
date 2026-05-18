# Split Runtime Deploy Runbook

This runbook covers the smallest supported split for issue #130:

- one API runtime that accepts `POST /api/v1/stories/` and persists the story shell plus task record
- one worker runtime that polls the database and executes story generation serially
- no Redis, Celery, SQS, or multi-worker task leasing

## Runtime assumptions

- Single worker only. Do not run more than one `backend.story_worker` process against the same database.
- The public API contract for `POST /api/v1/stories/` remains unchanged.
- The split runtime relies on the shared database for task state and the persisted story shell for generation input reconstruction.

## Required environment posture

API process:

- `STORY_GENERATION_RUNTIME_ROLE=api`
- `STORY_GENERATION_WORKER_POLL_INTERVAL_SECONDS` may remain set but is ignored by the API process
- `STORY_GENERATION_STALE_TASK_TIMEOUT_SECONDS` may remain set but API startup does not recover queued tasks in this mode

Worker process:

- `STORY_GENERATION_RUNTIME_ROLE=worker`
- `STORY_GENERATION_WORKER_POLL_INTERVAL_SECONDS=5` or another small polling interval appropriate for the environment
- `STORY_GENERATION_STALE_TASK_TIMEOUT_SECONDS=900` or another conservative timeout larger than the longest expected generation window

Shared baseline:

- API and worker must point at the same `DATABASE_URL`
- Run Alembic before starting either process in migration-managed environments
- Keep the existing asset-storage posture unchanged for the target environment

## Deployment procedure

1. Apply database migrations.
   - `./.venv/bin/python -m alembic -c alembic.ini upgrade head`
2. Deploy the API with `STORY_GENERATION_RUNTIME_ROLE=api`.
3. Verify API health.
   - `GET /healthz`
   - submit one story request and confirm the returned task stays `pending` until the worker is started
4. Deploy exactly one worker process.
   - `./.venv/bin/python -m backend.story_worker`
5. Submit one story request and confirm the worker transitions the task through `in_progress` to `completed` or `failed`.
6. Confirm task status via the existing endpoints.
   - `GET /api/v1/stories/generation-status/{task_id}`
   - `GET /api/v1/tasks/{task_id}`

## Recovery notes

- API-only restarts do not fail queued tasks in split mode.
- The worker marks only stale `in_progress` tasks as failed after `STORY_GENERATION_STALE_TASK_TIMEOUT_SECONDS` elapses.
- `pending` tasks remain queued until the single worker claims them.

## Related runbooks

- Rollback: `docs/split_runtime_rollback_runbook.md`
- Provider outage response: `docs/provider_outage_runbook.md`
- Staging restore and restore-target validation: `docs/staging_restore_runbook.md`