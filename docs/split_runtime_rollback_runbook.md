# Split Runtime Rollback Runbook

Use this runbook to move from the split API/worker deployment back to the combined in-process runtime.

## When to use it

- the worker entrypoint is unhealthy
- the split deployment needs to be backed out quickly
- operational complexity needs to be reduced while preserving the existing API contract

## Rollback target

- one FastAPI runtime with `STORY_GENERATION_RUNTIME_ROLE=combined`
- no separate worker process
- existing `POST /api/v1/stories/` behavior resumes in-process background execution

## Procedure

1. Stop the worker process.
2. Redeploy the API with `STORY_GENERATION_RUNTIME_ROLE=combined`.
3. Keep the same database and asset-storage configuration.
4. Verify that new story requests begin execution immediately after the API accepts them.
5. Review any tasks left in `pending` from the split deployment.
   - In the combined runtime, API startup recovery will mark stranded `pending` or `in_progress` tasks failed after a restart.
   - If you need to preserve queued work before restart, drain the queue with the single worker first.

## Data safety notes

- The split-runtime schema change is additive only; no rollback migration is required to resume combined mode.
- If rollback follows a broader staging incident involving database or object-store recovery, use `docs/staging_restore_runbook.md` before restarting traffic.

## Post-rollback checks

- Submit one story request and verify the task progresses without the worker process.
- Confirm no additional worker process remains running.
- Confirm the task status endpoints still return consistent progress and final state.