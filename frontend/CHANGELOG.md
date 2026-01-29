# Changelog

## Unreleased

### Changed
- No user-visible frontend changes; documentation/config references updated to align with new OpenAI defaults and toggles.

## [0.6.0](https://github.com/LeeBaker3/story_gen_for_work/compare/frontend-v0.5.0...frontend-v0.6.0) (2026-01-05)


### Features

* **admin:** show Avg Attempts (24h) in Admin Stats UI

	- Add new card rendering with two-decimal formatting
	- Keep success-rate card styling index stable
	- Tests: update admin stats test and ensure polling tests remain green ([a7f3049](https://github.com/LeeBaker3/story_gen_for_work/commit/a7f3049cb6d2a4d8b03874d8da252ec44202daa9))
* **characters:** add private photo upload + from-photo reference wizard ([97d782d](https://github.com/LeeBaker3/story_gen_for_work/commit/97d782d78e18800b552b634c1bf5c863b8e99744))
* **frontend,a11y:** add aria-live and aria-busy to generation progress UI ([d73deb9](https://github.com/LeeBaker3/story_gen_for_work/commit/d73deb97051f47bf52ec155e4deb5ebdbf60aa1b))
* **frontend:** add polling backoff and expose test hook for story generation status ([7ba515f](https://github.com/LeeBaker3/story_gen_for_work/commit/7ba515f874ac8a1db105c3bb3ac217ef34fb84bf))


### Bug Fixes

* **frontend:** align status polling with backend fields; use last_error and step-based messages ([ef72d26](https://github.com/LeeBaker3/story_gen_for_work/commit/ef72d262368ccdf8fa301196c5e3f00910d32137))

## [0.5.0](https://github.com/LeeBaker3/story_gen_for_work/compare/frontend-v0.4.4...frontend-v0.5.0) (2025-09-16)


### Features

* Add story generation progress UI and backend support ([9f2afce](https://github.com/LeeBaker3/story_gen_for_work/commit/9f2afcea2eb7afb6742f45f8eabd233a1fe8d28c))
* Dynamically set API_BASE_URL for dev/prod ([f9f6273](https://github.com/LeeBaker3/story_gen_for_work/commit/f9f627338981cdace9175bfcef890293cd4b7ab4))
* Implement admin user management features ([e7c4517](https://github.com/LeeBaker3/story_gen_for_work/commit/e7c4517d15206b98e366e02544e724d3e7bf2abe))
* Implement AI title page generation in ai_services ([dcbf299](https://github.com/LeeBaker3/story_gen_for_work/commit/dcbf2993a187a45413457f928a251e92b73b1315))
* Implement CRUD unit tests and update PRD ([da5a5cb](https://github.com/LeeBaker3/story_gen_for_work/commit/da5a5cb67ed277cbcc1486db59a3df0097f08493))
* Implement Drafts & Template functionality, Fix UI freeze ([3cba6db](https://github.com/LeeBaker3/story_gen_for_work/commit/3cba6dbf38a08861c0ce776d28eba762f8c5fccd))


### Bug Fixes

* Correct PDF page numbering and add frontend icon links ([fcc4718](https://github.com/LeeBaker3/story_gen_for_work/commit/fcc47188440752ea48895e022f8a93d6834b3aad))
* Improve PDF image path resolution and AI title handling ([2caf207](https://github.com/LeeBaker3/story_gen_for_work/commit/2caf207d3f20950391d44a6572c51338fac12666))
* Improve story preview readability and image alignment ([f86b90d](https://github.com/LeeBaker3/story_gen_for_work/commit/f86b90defaf458fa0db50cbc4e1c88bc870b62e2))
* Resolve JS errors, improve UX and logging, update PRD ([1c76a56](https://github.com/LeeBaker3/story_gen_for_work/commit/1c76a56daa6b6c9e83c0076babf5e2dd87e9d1ad))

## Frontend Changelog

All notable changes to the frontend will be documented in this file.

This file is maintained by release-please.
