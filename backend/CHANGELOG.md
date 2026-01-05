# Changelog

## [0.6.0](https://github.com/LeeBaker3/story_gen_for_work/compare/backend-v0.5.0...backend-v0.6.0) (2026-01-05)


### Features

* **api:** add avg_attempts_last_24h to admin stats and prefer duration_ms for averages\n\n- AdminStats schema: add avg_attempts_last_24h\n- /api/v1/admin/stats returns avg_attempts_last_24h (rounded)\n- Prefer precise duration_ms with fallback to timestamps\n- Update StoryGenerationTask tracking and lifecycle handling\n- Tests: extend admin stats expectations; lifecycle coverage ([2a828b9](https://github.com/LeeBaker3/story_gen_for_work/commit/2a828b9ab6347562a8471bc873789b4f7e34e8ec))
* **characters:** add private photo upload + from-photo reference wizard ([97d782d](https://github.com/LeeBaker3/story_gen_for_work/commit/97d782d78e18800b552b634c1bf5c863b8e99744))

## [0.5.0](https://github.com/LeeBaker3/story_gen_for_work/compare/backend-v0.4.4...backend-v0.5.0) (2025-09-16)


### Features

* Add story generation progress UI and backend support ([9f2afce](https://github.com/LeeBaker3/story_gen_for_work/commit/9f2afcea2eb7afb6742f45f8eabd233a1fe8d28c))
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
* Resolve 405 error for Edit Draft by adding GET /stories/drafts/{story_id} endpoint ([499f9b2](https://github.com/LeeBaker3/story_gen_for_work/commit/499f9b23e863d7a09f7c32ed5f335a9d580ead8d))
* Resolve JS errors, improve UX and logging, update PRD ([1c76a56](https://github.com/LeeBaker3/story_gen_for_work/commit/1c76a56daa6b6c9e83c0076babf5e2dd87e9d1ad))
* resolved reference image generation logic ([1e90af7](https://github.com/LeeBaker3/story_gen_for_work/commit/1e90af77f1f3004493641bd71833b07f946ae4d6))
* Update .gitignore and backend requirements ([7ac40a2](https://github.com/LeeBaker3/story_gen_for_work/commit/7ac40a292edcebe7a9719bf3a0a2e5d6292f229d))
* Update image generation to use gpt-image-1 and remove unsupported parameters ([ed7f78d](https://github.com/LeeBaker3/story_gen_for_work/commit/ed7f78de2e109cfe653f05a075c30ded0aa6817c))

## Backend Changelog

All notable changes to the backend will be documented in this file.

This file is maintained by release-please.
