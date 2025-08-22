# UI Modernization and Character Reuse Plan

Last updated: 2025-08-11

## Goals

- Modernize the UI with a cohesive theme, tasteful animations, and micro‑interactions.
- Introduce a story creation wizard.
- Add a reusable Characters library with reference image generation and regeneration.
- Maintain accessibility, performance, and CI stability.

## Phases Overview

1) Phase 1 — Modern UI polish (low-risk, high-impact)
2) Phase 2 — Characters domain: data model + backend API
3) Phase 3 — Story creation wizard with character reuse and image regeneration
4) Phase 4 — Docs, QA, CI
5) Phase 5 — Nice-to-haves

---

## Phase 1 — Modern UI polish

Scope
- Theme tokens: CSS variables for colors, radii, shadows, motion.
- Sticky glass header with animated accent underline.
- Pill/gradient buttons with subtle hover/active transitions.
- Toast notifications (non-blocking message UX) while keeping legacy inline messages for compatibility.
- Skeleton loaders for lists and image areas.
- Improved progress bar styling (animated gradient, easing).
- Respect `prefers-reduced-motion`.

Files
- `frontend/style.css`: add tokens and component styles; progressive overrides to avoid layout churn.
- `frontend/index.html`: add toast container and password toggles markup (auth only).
- `frontend/script.js`: toast helper; password toggle + strength meter; skeleton injection in stories loading.

Acceptance
- No functional changes to flows; UI feels modern and responsive.
- Screen-reader and keyboard navigation preserved; focus ring visible.

---

## Phase 2 — Characters domain: data model + backend API

Schema (new tables)
- characters: `id`, `user_id` (FK), `name`, `description`, `age?`, `gender?`, `clothing_style?`, `traits?` (text/json), `image_style?`, `current_image_id?`, `created_at`, `updated_at`.
- character_images: `id`, `character_id` (FK), `file_path`, `prompt_used` (text), `image_style`, `created_at`.

Storage
- Save files under `data/images/user_{user_id}/characters/{character_id}/{image_id}.png`.

API (under `/api/v1/characters`)
- POST `/` — create character. Body: name, description, optional attrs; optional `generate_image`, `image_style`.
- GET `/` — list user’s characters. Query: `q`, `page`, `page_size`.
- GET `/{id}` — fetch character with current image and image history count.
- PUT `/{id}` — update character fields (no image gen).
- POST `/{id}/regenerate-image` — optional new `description`/`image_style`; creates a new version and sets it current.
- DELETE `/{id}` — optional soft-delete (can defer).

Implementation
- `backend/schemas.py`: Pydantic models for CharacterCreate/Update/Out, CharacterImageOut, pagination envelope.
- `backend/database.py`: models/DDL for characters and character_images.
- `backend/crud.py`: CRUD and image creation helpers.
- `backend/ai_services.py`: `generate_character_image(prompt, style)` reusing ImageStyle mapping and lazy client guard.
- `backend/characters_router.py` (new) or in `public_router.py`: secure, user-scoped endpoints.
- Tests: CRUD + API; image API mocked.

Acceptance
- Users can create/list/update characters and regenerate images; only owners can access.
- Paths and storage consistent with existing static mounts.

---

## Phase 3 — Story creation wizard with character reuse

Wizard steps
1. Basics — title (optional), genre, outline.
2. Characters — pick from library or create new; view/update description; generate/regenerate reference image; select 1+ to include.
3. Options — pages, tone, setting, text density, word-to-picture ratio, image style.
4. Review — summary and confirm.

UI behaviors
- Skeletons while loading; toasts for actions; localStorage for last-used options and selections.
- Inline “Regenerate image” for selected character; preview is updated on success.

Frontend
- `frontend/index.html`: group existing form into steps; character library panel with search/pagination and detail panel/modal.
- `frontend/script.js`: wizard state machine; Characters API client; renderers for list/detail; optimistic previews; inject `character_ids` into story payload.
- `frontend/style.css`: stepper styles, card grid, preview area, modal.

Backend
- Story generation request accepts `character_ids: []`.
- `backend/schemas.py`: update story create schema.
- `backend/story_generation_service.py`: incorporate selected characters’ descriptions.

Acceptance
- Users can reuse characters and regenerate/reference images during story creation.

---

## Phase 4 — Docs, QA, CI

- README: wizard/characters overview and screenshots.
- PRD: user stories and flows.
- CHANGELOG: version bump and features.
- Tests: unit (CRUD, API) and integration (wizard; mocked image gen).
- CI: keep dummy OPENAI_API_KEY; ensure async tests run.

---

## Phase 5 — Nice-to-haves

- Character tags/favorites; multiple current images (chooser).
- Import/export characters as JSON.
- Admin metrics for characters and generated images.

---

## Contracts (abridged)

POST `/api/v1/characters`
- In: `{ name, description, age?, gender?, clothing_style?, traits?, image_style?, generate_image? }`
- Out: `{ id, name, description, image: { id, url }, created_at, updated_at }`

GET `/api/v1/characters?q=&page=&page_size=`
- Out: `{ items: [ { id, name, thumbnail_url, updated_at } ], total, page, page_size }`

POST `/api/v1/characters/{id}/regenerate-image`
- In: `{ description?, image_style? }`
- Out: `{ image: { id, url, created_at } }`

---

## Quality Gates

- Build: PASS
- Lint/Typecheck: PASS
- Unit tests: PASS (CRUD/API; mocks for OpenAI)
- Smoke: create → regenerate → select → generate story
