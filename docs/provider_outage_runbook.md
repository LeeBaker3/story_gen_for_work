# Provider Outage Runbook

This runbook covers temporary outages or sustained failures from story-generation providers while using the split API/worker runtime.

## Symptoms

- queued tasks accumulate in `pending`
- tasks fail with provider error messages during text or image generation
- worker logs show repeated provider exceptions or retries exhausting
- `/api/v1/ops/metrics` shows backlog growth or a stale worker heartbeat

## Immediate actions

1. Confirm the provider issue is external rather than local configuration.
2. Leave the API running so requests can continue to enqueue only if the business decision is to preserve backlog.
3. If backlog growth is not acceptable, temporarily stop accepting new story requests at the deployment layer or switch traffic away from the affected environment.
4. Keep only one worker process. Do not scale out workers to compensate.
5. If configured, watch the generic high-severity runtime alert webhook for worker-loop exceptions while triaging the outage.

## Worker handling guidance

- If the provider outage is brief, leave the worker running and let normal task failure semantics apply.
- If the outage is sustained and you do not want repeated failures, stop the worker process temporarily.
- Stopped-worker behavior is explicit: tasks remain `pending` until the worker resumes.

## Recovery procedure

1. Restore provider connectivity or configuration.
2. Restart the single worker if it was stopped.
3. Watch one queued task move from `pending` to `completed`.
4. Review tasks that failed during the outage and decide whether to retry them manually or recreate them through the existing API flow.
5. Recheck `/api/v1/ops/metrics` and confirm `app_story_worker_healthy` returns to `1` and backlog stops growing.

## Notes

- The worker only auto-recovers stale `in_progress` tasks after the configured timeout.
- The system does not implement automatic requeueing of failed tasks in this slice.
- The runtime alert webhook is best-effort only. Use it as a pager/input signal, not as a guaranteed audit trail.
- If the outage coincides with a staging environment recovery or restore exercise, use `docs/staging_restore_runbook.md` for the database and asset posture first.