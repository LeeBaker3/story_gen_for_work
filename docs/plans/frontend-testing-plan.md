# Frontend Testing Plan

Goal
- Introduce unit and integration tests for the vanilla JS frontend to reduce regressions in the wizard, Characters library, and modal flows.

Scope (Phase 1)
- Unit and DOM-integration tests with Jest + @testing-library/dom.
- No framework migration. Keep ES modules and current build-less setup.

Milestones
1) Tooling + Scaffolding (Day 0-1)
   - Add dev deps: jest, jest-environment-jsdom, @testing-library/dom, @testing-library/user-event.
   - Add minimal package.json (scripts: test, test:watch).
   - Configure Jest (testEnvironment: jsdom, transform for ES modules if needed using babel-jest or set "type": "module").
   - Create frontend/tests structure.

2) Foundational tests (Day 1-2)
   - Wizard navigation: dots + Next/Back + disabled states; initializes correctly on load and on “Create New Story”.
   - Inline modal status: regenerate button disables buttons, shows spinner+status, re-enables on success/error.
   - Characters list: pagination, search filter, selection persistence across pages.

3) Contracts and fixtures (Day 2)
   - Add small mock helpers for fetch to simulate API responses for characters and story endpoints.
   - Snapshot‑free; assert via roles/labels/text (a11y-friendly queries).

4) CI integration (Day 2)
   - Update GitHub Actions: new job step to run `npm test` (or `npx jest`).

5) Docs (Day 2)
   - README Testing section: how to run Jest locally.

Optional Phase 2 (E2E)
- Add Playwright for login → wizard → generate story → progress checks.
- Run E2E behind a label in CI (opt‑in).

Acceptance Criteria
- Jest configured; `npm test` passes locally on a clean checkout.
- Minimum 6 tests: 2 wizard, 2 modal status, 2 characters list.
- CI executes Jest on PRs; failing tests block merges.

Risks & Mitigations
- ES module imports in tests: use `type: module` or Babel Jest transform.
- DOM timing/race conditions: prefer waitFor and user-event.
- Flaky tests: keep UI delays deterministic; mock fetch.

Next Steps
- Create package.json with the dev deps and jest config.
- Add initial sample tests and a small fetch mock utility.
- Wire CI job in .github/workflows/ci.yml.
