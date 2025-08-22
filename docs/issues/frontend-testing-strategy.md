# Issue: Frontend testing strategy is missing

Summary
- There is no documented or implemented test strategy for the frontend (vanilla JS, HTML/CSS) part of the project. This increases risk of regressions across core flows (wizard, Characters library, modals, inline status, admin monitoring UI) and slows refactoring.

Impact
- Harder to verify UI behavior and state transitions.
- Increased chance of breaking changes going unnoticed.
- Slower iteration due to manual QA burden.

Proposal
1) Establish testing stack
   - Unit: Jest (jsdom) for pure functions and small DOM-manipulating modules.
   - Integration: @testing-library/dom for DOM queries and user-event (no React required).
   - E2E (optional, phased): Playwright for critical user journeys (login, story creation flow, character regen).

2) Project scaffolding
   - Add dev deps: jest, @testing-library/dom, @testing-library/user-event, jest-environment-jsdom, eslint-plugin-jest (optional).
   - Create frontend/tests with sample tests for:
     - Wizard step transitions (dots, Next/Back, disabled states)
     - Characters library list pagination + search
     - Modal regenerate flow: disables buttons, shows inline status, re-enables on completion
     - Notifications: snackbar vs inline status pattern

3) Scripts
   - Add npm-like scripts via a minimal package.json for running Jest, or run via npx.

4) CI
   - Extend GitHub Actions workflow to run frontend Jest tests.

5) Documentation
   - Add a short section to README under Testing → Frontend tests.

Acceptance criteria
- At least 5 Jest tests covering wizard navigation, modal inline status, and character list filtering.
- CI job running Jest on PRs.
- README updated with instructions to run frontend tests locally.

Out of scope (separate follow-ups)
- Visual regression tests.
- E2E Playwright flows (tracked in a separate issue once Jest unit/integration tests land).
