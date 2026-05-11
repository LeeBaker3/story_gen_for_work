# UI E2E Test Frame Plan

Last updated: 2026-05-06

## Goal

Build a repeatable cross-stack E2E frame that runs the real FastAPI app, serves
the existing frontend from that server, and verifies the main user journeys
against a dedicated test database.

## Recommended Stack

- Playwright for browser automation.
- pytest-playwright to keep the E2E suite alongside the Python backend tests.
- A temporary file-backed SQLite database for the running server process so the
  app uses the same code paths as production without touching shared state.

## Test Frame

- Start the real FastAPI application in test mode.
- Point the frontend at the running backend and serve the existing frontend
  assets from that server process.
- Seed one admin user, one regular test user, and one completed story before
  each run.
- Disable image generation in the E2E environment so story creation and
  polling stay deterministic in CI.
- Reset the database and temp storage between runs.

## Key Journeys

- Auth: sign in as a regular user and reach the app shell.
- Wizard submit: complete the story wizard and submit a generation request.
- Story library/viewer: open the generated story from the library and verify
  the viewer renders persisted content.
- Character create/list: create a character, then confirm it appears in the
  list and can be reused.
- Generation polling: verify the UI follows the backend status updates until
  the story is complete.
- Admin access: sign in as the admin user and reach the admin area.

## Milestones

### Milestone 1: Environment and bootstrapping

- Define the test app boot path, temp SQLite database, and seed data setup.
- Add Playwright plus pytest-playwright wiring.

Acceptance criteria:
- The real FastAPI app starts in test mode and serves the frontend.
- The suite can create and tear down an isolated temp SQLite database.

### Milestone 2: Core user path

- Implement the auth, wizard submit, and generation polling scenarios.
- Verify the run uses seeded users and a real persisted story record.

Acceptance criteria:
- A regular user can log in, submit a story, and observe completion through the UI.
- The backend writes are visible in the database used by the test run.

### Milestone 3: Content and admin coverage

- Add story library/viewer coverage, character create/list coverage, and admin
  access coverage.
- Keep selectors accessibility-first and assertions focused on user-visible
  behavior.

Acceptance criteria:
- The library, viewer, character list, and admin entry points are exercised by
  browser tests.
- The suite remains deterministic with image generation disabled.

### Milestone 4: CI gate

- Add `.github/workflows/e2e-tests.yml` for the E2E job.
- Mark that job as a required status check before merge once the workflow is
  stable.

Acceptance criteria:
- The E2E workflow runs in CI after the implementation lands.
- The new status check can be enforced as a merge requirement.

## Risks and Constraints

- The suite should avoid mocked API responses for the main path; the value is
  in exercising the full app stack.
- The temp SQLite database must remain isolated per run to avoid test coupling.
- Image generation must stay disabled in this frame to prevent timing and
  content drift.

## Next Steps

- Implement the bootstrapping and seed fixtures.
- Add the first Playwright scenarios.
- Wire the GitHub Actions workflow and promote it to a required check when the
  suite is stable.