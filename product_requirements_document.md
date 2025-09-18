# Product Requirements Document (Excerpt)

## Admin Stats Enhancements (2025-09-18)

Summary
- Provide operators with clearer visibility into background story generation by surfacing precise durations and retry behavior.

API: GET /api/v1/admin/stats
- Adds avg_attempts_last_24h: average number of attempts across completed StoryGenerationTask records created within the last 24 hours.
- avg_task_duration_seconds_last_24h now prefers a precise duration captured at completion (duration_ms) with a fallback to updated_at - created_at.

Data Model: StoryGenerationTask
- New fields: attempts, started_at, completed_at, duration_ms, last_error (in addition to legacy error_message).
- attempts increments when a page image retry is performed; duration_ms is set on terminal states.

Frontend UI
- Admin → Admin Stats shows a new card “Avg Attempts (24h)”.

Acceptance Criteria
- When there are completed tasks in the last 24h, avg_attempts_last_24h returns a non-null numeric value rounded to 2 decimals; otherwise null.
- Admin Stats UI renders the value with two decimals (or em dash when null).
