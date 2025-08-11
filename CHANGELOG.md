# Changelog

All notable changes to this project will be documented in this file.

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
