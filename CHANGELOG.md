# Changelog

All notable changes to this project will be documented in this file.

## [0.4.4] - 2025-08-22
### Added
- Frontend testing scaffold with Jest + Testing Library.
- Added jest.config.mjs, tests setup file, utility mocks, and an initial sanity test.
- CI workflow to run frontend tests on push and PR.

### Changed
- README updated with instructions for running frontend tests.

## [0.4.3] - 2025-08-21
### Added
- PRD: Added explicit API Contracts section aligned with current routers and schemas (auth, stories, characters, dynamic lists, admin users, monitoring).

## [0.4.2] - 2025-07-11
### Added
- Inline status feedback in Character modal (Regenerate, Save, Save as New) with spinner and aria-live.
- Admin diagnostics endpoint: /api/v1/admin/monitoring/config (masked key presence, models, mounts, dirs).
- CONFIG.md at repo root; standardized on single root .env.

### Changed
- Sticky glass header and animated progress bar; reduced-motion fallback.
- Restored right-aligned modal actions; moved inline status below buttons.
- README updated to reference CONFIG.md and frontend overview.

### Fixed
- "Use as Template" ReferenceError by hoisting resetFormAndState; wizard nav wiring.
- Removed transient spinner for story generation; rely on progress UI.
- OpenAI 401s by consolidating env loading and lazy client init.

## [0.4.1] - 2025-07-10
### Added
- Admin monitoring UI enhancements:
  - Persist monitoring preferences (selected log, tail length, auto-refresh, filter text/regex/invert) in localStorage.
  - Follow tail mode for logs (auto-scroll to bottom after refresh).
- Frontend signup UX: added Confirm Password field and client-side validation to prevent mismatches.

### Changed
- README and docs updated to reflect monitoring UI details and CI/testing notes.

### Fixed
- ai_services no longer raises at import time if OPENAI_API_KEY is missing; client is lazily initialized with guards around API usage.
- CI: set a dummy OPENAI_API_KEY to avoid import-time checks; ensured async tests run by adding pytest-asyncio to backend requirements.

## [0.4.0] - 2025-07-08
- Previous release with logging fixes, admin monitoring endpoints, and PDF export alignment.
