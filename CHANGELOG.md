# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0](https://github.com/LeeBaker3/story_gen_for_work/compare/v0.4.4...v0.5.0) (2025-09-16)


### Features

* Add story generation progress UI and backend support ([9f2afce](https://github.com/LeeBaker3/story_gen_for_work/commit/9f2afcea2eb7afb6742f45f8eabd233a1fe8d28c))
* Dynamically set API_BASE_URL for dev/prod ([f9f6273](https://github.com/LeeBaker3/story_gen_for_work/commit/f9f627338981cdace9175bfcef890293cd4b7ab4))
* Enhance character reference image generation during draft finalization and update related tests ([f8479b4](https://github.com/LeeBaker3/story_gen_for_work/commit/f8479b44ec6c912b3f0b92974457c135545746dd))
* Enhance character reference image prompt construction with detailed attributes ([3569af9](https://github.com/LeeBaker3/story_gen_for_work/commit/3569af9a670dd1da80c450bae6525d1bc1002e94))
* Implement admin user management features ([e7c4517](https://github.com/LeeBaker3/story_gen_for_work/commit/e7c4517d15206b98e366e02544e724d3e7bf2abe))
* Implement AI title page generation in ai_services ([dcbf299](https://github.com/LeeBaker3/story_gen_for_work/commit/dcbf2993a187a45413457f928a251e92b73b1315))
* Implement CRUD unit tests and update PRD ([da5a5cb](https://github.com/LeeBaker3/story_gen_for_work/commit/da5a5cb67ed277cbcc1486db59a3df0097f08493))
* Implement daily rotating file handler and b64_json redaction filter for logging ([67b6490](https://github.com/LeeBaker3/story_gen_for_work/commit/67b64908c6753401e9b1369b270e6afb48368be4))
* Implement Drafts & Template functionality, Fix UI freeze ([3cba6db](https://github.com/LeeBaker3/story_gen_for_work/commit/3cba6dbf38a08861c0ce776d28eba762f8c5fccd))
* Implement Phase 1 of admin functionality ([784a74a](https://github.com/LeeBaker3/story_gen_for_work/commit/784a74a8dfd1c055931b38e7a07225f5758d3f54))
* Update dynamic list endpoints for clarity and enhance character reference image prompt construction ([b035a79](https://github.com/LeeBaker3/story_gen_for_work/commit/b035a791cb0a0a7b97e6d7c4fd7788678a0d53f0))
* Update project with schema, docs, tests, and image model ([91578d7](https://github.com/LeeBaker3/story_gen_for_work/commit/91578d79be8faa90342993cee797f87ebd0e1847))
* Update text generation model to gpt-4.1-mini ([c6e55f1](https://github.com/LeeBaker3/story_gen_for_work/commit/c6e55f13348eabb565b466a5a41111e94794fc37))


### Bug Fixes

* Add created_at to Story model and handle DB schema update ([bf1b6b4](https://github.com/LeeBaker3/story_gen_for_work/commit/bf1b6b490599ce859c559e46b2e3da823bfc313b))
* Add created_at to Story schema for frontend display ([dda5189](https://github.com/LeeBaker3/story_gen_for_work/commit/dda5189df74e16bdf0062442d6e27e76eaca47c8))
* Correct draft tests and update schemas ([662a8c6](https://github.com/LeeBaker3/story_gen_for_work/commit/662a8c63ff965e0e21cf3127628662477004c3bf))
* Correct PDF page numbering and add frontend icon links ([fcc4718](https://github.com/LeeBaker3/story_gen_for_work/commit/fcc47188440752ea48895e022f8a93d6834b3aad))
* Improve PDF image path resolution and AI title handling ([2caf207](https://github.com/LeeBaker3/story_gen_for_work/commit/2caf207d3f20950391d44a6572c51338fac12666))
* Improve story preview readability and image alignment ([f86b90d](https://github.com/LeeBaker3/story_gen_for_work/commit/f86b90defaf458fa0db50cbc4e1c88bc870b62e2))
* Resolve 405 error for Edit Draft by adding GET /stories/drafts/{story_id} endpoint ([499f9b2](https://github.com/LeeBaker3/story_gen_for_work/commit/499f9b23e863d7a09f7c32ed5f335a9d580ead8d))
* Resolve JS errors, improve UX and logging, update PRD ([1c76a56](https://github.com/LeeBaker3/story_gen_for_work/commit/1c76a56daa6b6c9e83c0076babf5e2dd87e9d1ad))
* resolved reference image generation logic ([1e90af7](https://github.com/LeeBaker3/story_gen_for_work/commit/1e90af77f1f3004493641bd71833b07f946ae4d6))
* Update .gitignore and backend requirements ([7ac40a2](https://github.com/LeeBaker3/story_gen_for_work/commit/7ac40a292edcebe7a9719bf3a0a2e5d6292f229d))
* Update character reference image generation logic to ensure consistency and resolve TypeError during draft finalization ([9d700fb](https://github.com/LeeBaker3/story_gen_for_work/commit/9d700fbf2a75dc0ce50e3a4ef718df25b7a92bef))
* Update image generation to use gpt-image-1 and remove unsupported parameters ([ed7f78d](https://github.com/LeeBaker3/story_gen_for_work/commit/ed7f78de2e109cfe653f05a075c30ded0aa6817c))

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
