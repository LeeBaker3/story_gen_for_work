# 1. Purpose

The Story Generator Web App is a web-based application that allows users to generate custom illustrated stories using AI. It leverages the OpenAI ChatGPT API for story generation and an AI image generation model for generating corresponding illustrations. Users can log in, input story parameters, preview, edit, and export stories as PDFs.

# 2. Features and Functionality

## 2.1 User Interface (UI)
*   **Homepage:**
    *   Modern, clean design.
    *   Options to:
        *   Create a new story.
        *   Log in / Sign up.
        *   Browse previously created stories.
*   **Story Creation Form:**
    *   Select story genre (Children’s, Sci-Fi, Drama, Horror, Action). Dropdowns (e.g., genre) support alphabetical/numerical sorting.
    *   Enter:
        *   Story Title (Optional. If left blank, a title will be AI-generated. Can be edited later).
        *   Story outline.
        *   Main characters (name, personality, background).
        *   Includes a collapsible, detailed character creation section. Users can specify attributes like age, gender, physical appearance (hair color, eye color, ethnicity, build), clothing style, and key personality traits. The system will provide defaults or tips to guide users. This information is used to generate upfront character reference images to guide the AI image generation model for consistent character depiction throughout the story.
        *   Number of pages.
        *   Option to select a writing style for the story (e.g., narrative, descriptive, poetic, humorous, formal).
        *   Option to adjust word-to-picture ratio (e.g., one image every X words/paragraphs, or one image per page as default).
        *   Option to select an image style for story illustrations (e.g., cartoon, watercolor, photorealistic).
    *   Additional optional fields (tone, setting, etc.).
*   **Story Preview Page:**
    *   Displays the story, starting with a Title Page featuring the story title and a cover image.
    *   Displays generated story per page, with accompanying image.
    *   Navigation between pages.
    *   Export options (PDF).
    *   Option to edit story title, page text, and regenerate pages/images.
*   **Authentication:**
    *   Secure login and session management for regular and admin users. Admin users have distinct privileges.
    *   User dashboard showing saved stories.
    *   Forgot Password functionality.
    # 1. Purpose

    Updated: 2025-08-21
*   **Admin Panel:** (New Section for FR-ADM-01, FR-ADM-05, FR-ADM-06)
    *   Accessible only to users with admin privileges.
    *   Interface for managing application-wide settings and dynamic content.
    *   Functionality to manage dropdown list items (e.g., genres, image styles).
    *   Interface for User Management (activate, deactivate, delete users).
    *   Interface for Content Moderation (review and remove stories).
    *   Interface for System Monitoring (view basic health, usage stats, logs). The logs viewer provides:
        *   Tail length selection and auto-refresh.
        *   Follow tail (auto-scroll) behavior when enabled.
        *   Client-side filtering with plain text or regex, plus invert option.
    *   **Story Creation Wizard:**
        *   Step 1 — Basics: Title (optional; AI if blank), Genre, Outline.
        *   Step 2 — Characters: Pick from saved Characters or create new; view/update description; generate/regenerate reference image; select one or more to include.
        *   Step 3 — Options: Pages, Tone, Setting, Text Density, Word-to-Picture Ratio, Image Style, Writing Style.
        *   Step 4 — Review: Summary and confirm.
        *   UI polish: sticky glass header, animated progress bar (with reduced-motion fallback), toasts, and inline status feedback inside modals (no hidden snackbars behind modals).
        *   Characters page features: search, pagination, selection, and modal-based image regenerate with buttons disabled and status shown during action.
    *   **Characters Library:**
        *   Standalone list of saved characters with thumbnails.
        *   CRUD: create, update, regenerate image (new version becomes current), optional duplicate/save-as-new.
        *   Storage uses per-user folders; thumbnails/reference images are served from static mounts.
    *   If no title is provided by the user, generates a suitable story title based on the outline and other parameters.
    *   Parses and stores story (including title), pages (with a dedicated title page as the first page), and image metadata in a SQLite database.
    *   Generates a cover image for the title page using the AI image generation model, based on the final story title, overall themes, and main character descriptions.
    *   Generates PDF combining story text and locally stored images.
    *   Provides an endpoint to retrieve a list of stories for the authenticated user.
        *   Manage dynamic list items (e.g., genres, image styles) used by forms.
        *   User Management (activate, deactivate, delete users).
    *   Manages adjustable word-to-picture ratios for story layout.
    *   Supports different selectable writing styles for ChatGPT, with styles potentially managed dynamically.
    *   Implements a secure 'Forgot Password' mechanism (e.g., token-based).
    *   Implements role-based access control (RBAC) to differentiate between regular users and admins.
    *   Provides CRUD endpoints for managing dynamic list content (e.g., genres, image styles) accessible only by admins.
    *   Handles user-defined story titles, allowing for creation and updates.
        *   Configuration Diagnostics endpoint: `/api/v1/admin/monitoring/config` returns masked key presence, model names, mount flags, paths, and whether the OpenAI client is initialized (no secrets leaked).
    *   Securely stores and manages API keys (e.g., OpenAI API Key), accessible/modifiable only by admins.
    *   Provides mechanisms to ensure data integrity when dynamic list items (e.g., genres, styles) are modified or deleted by an admin. This includes strategies like soft deletes, preventing deletion of in-use items, or indicating usage to the admin.
    *   Provides endpoints for admins to manage users (view, activate, deactivate, delete).
    *   Provides endpoints for admins to moderate content (list all stories, delete stories).
    *   Provides endpoints for admins to view system statistics and access application logs.
        *   Text model (default: gpt-4.1-mini): Returns story content in structured JSON format.
        *   Image model (default: gpt-image-1): Generates images based on page-specific prompts.
## 3.2 Frontend
*   Technologies: HTML, CSS (site-wide), JavaScript
*   Modern responsive design using CSS for theming.
*   Form validation and dynamic content updates.

# Product Requirements Document (PRD)

Updated: 2025-08-21

## 1. Purpose

The Story Generator Web App allows users to generate custom illustrated stories using AI. It leverages OpenAI for story text and images. Users can log in, use a multi-step wizard, reuse saved Characters (with reference images), preview, edit, and export stories as PDFs.

## 2. Features and Functionality

### 2.1 User Interface (UI)
- Homepage
    - Modern, clean design with options to create a story, log in / sign up, and browse stories.
- Story Creation Wizard
    - Step 1 — Basics: Title (optional; AI if blank), Genre, Outline.
    - Step 2 — Characters: Pick from saved Characters or create new; view/update description; generate/regenerate reference image; select 1+ to include.
    - Step 3 — Options: Pages, Tone, Setting, Text Density, Word-to-Picture Ratio, Image Style, Writing Style.
    - Step 4 — Review: Summary and confirm.
    - Polish: sticky glass header, animated progress bar (reduced-motion fallback), toasts, and inline modal status feedback (no hidden snackbars).
    - Characters page: search, pagination, selection, modal-based image regenerate with disabled buttons and inline status while busy.
- Characters Library
    - Saved characters with thumbnails; create/update; regenerate image (new version becomes current); optional duplicate/save-as-new.
- Story Preview Page
    - Title page with cover image; per-page text + image; navigation; edit title/page text; regenerate content; export PDF.
- Authentication
    - Secure login/session; admin role; signup confirmation (double password with client-side validation); forgot password (planned).
- Admin Panel
    - Manage dynamic lists (genres, image styles) used by forms; user management; content moderation; monitoring (logs, basic stats); diagnostics endpoint for safe configuration checks.

### 2.2 Frontend
- HTML/CSS/JS (vanilla) with semantic HTML, scoped queries, and ES6 modules.
- Wizard state machine; Characters API client; optimistic updates; inline modal status with spinner and aria-live; reduced-motion respected.

### 2.3 Backend
- FastAPI with SQLAlchemy and Pydantic v2.
- Text model default: gpt-4.1-mini; image model default: gpt-image-1 (configurable via env).
- Story generation background task; per-page prompts and images saved to disk under `data/` and served under `/static_content/`.
- Characters domain: CRUD; regenerate image; per-user storage paths; thumbnails/current image.
- Admin monitoring: logs list/tail/download; stats; config diagnostics at `/api/v1/admin/monitoring/config` (masked key presence, models, mounts, dirs, client init flag).

### 2.4 Database (SQLite)
- Users: username, hashed_password, email, role, is_active.
- Stories: title, outline, genre, image_style, word_to_picture_ratio, text_density, main_characters JSON, is_draft, generated_at, timestamps.
- Pages: story_id, page_number, text, image_description, image_path.
- DynamicList: list_name, list_label, description.
- DynamicListItem: list_name, item_value, item_label, is_active, sort_order, additional_config.
- StoryGenerationTask: id, story_id, user_id, status, progress, current_step, error_message.
- Characters: id, user_id, name, description, age, gender, clothing_style, key_traits, image_style, current_image_id.
- CharacterImages: id, character_id, file_path, prompt_used, image_style.

### 2.5 Logging & Error Handling
- Rotating logs under `data/logs`; app/api/error; redact sensitive payloads.
- Graceful messages for API timeouts, image errors, invalid JSON.

### 2.6 State Management & Recovery (Story Generation)
- Track progress, current step, attempts.
- Smart retries with backoff and attempt caps; resume on retryable errors.

## 3. Functional Requirements

### 3.1 Core Application & Backend
- FR-CORE-01: Generate and store story text/images in SQLite.
- FR-CORE-02: All images stored locally.
- FR-CORE-03: Comprehensive logging.
- FR-CORE-04: Fully functioning local backend and frontend.

### 3.2 UI & UX
- FR-UI-01: Story preview and PDF export.
- FR-UI-02: Sortable dropdowns (e.g., genres) alphabetically/numerically.
- FR-UI-03: Wizard navigation and status polish (dots, Next/Back, reduced-motion, inline modal status, toasts).

### 3.3 User Management & Authentication
- FR-AUTH-01/02/03: Register, login, session management.
- FR-AUTH-04: Forgot password (planned).
- FR-AUTH-05/06: Token refresh (if added) and clear 401 handling.

### 3.4 Story Creation & Management
- FR-STORY-01/02: Input story data; each page has an image (including title page).
- FR-STORY-03: Detailed character attributes and upfront reference images.
- FR-STORY-04: Adjustable word-to-picture ratio.
- FR-STORY-05: Selectable image styles.
- FR-STORY-06/07/08: Edit title; dedicated title page; cover image.
- FR-STORY-09: Use story as template.
- FR-STORY-10: Save draft and resume.
- FR-STORY-11: Reusable Characters (implemented).
- FR-STORY-12: Wizard reliability (step sync, init, template fix).

### 3.5 AI Model Integration
- FR-AI-01: JSON output includes Title, Page, Image_description.
- FR-AI-02: Defaults to gpt-4.1-mini (text) and gpt-image-1 (image); configurable.
- FR-AI-03: Optional style mapping flag to adjust API style/prompts; future admin UI may manage.

### 3.6 Administration
- FR-ADM-01/02/03/04: Admin role, user management, moderation, monitoring.
- FR-ADM-05/06: Manage dynamic lists and populate dropdowns from DB (implemented).
- FR-ADM-07: Configuration diagnostics endpoint (admin-only); full editable config UI is future work.
- FR-ADM-08: Log viewing and filtering.
- FR-ADM-09/10: Broadcasts and analytics (future).
- FR-ADM-11: Data integrity on dynamic content changes (soft delete, in-use indicators, historical value strategy).

### 3.7 Testing
- FR-TEST-01: Unit tests for CRUD, AI service interactions, API endpoints.
- Coverage includes characters CRUD/API (mocked OpenAI), admin lists, monitoring (logs/stats/config), seeding, story generation, and core endpoints.

## 4. Deployment & Environment
- Runs locally: FastAPI, SQLite, HTML/CSS/JS, filesystem for images/logs.
- Configuration via root `.env`; `backend/settings.py` centralizes defaults.
- Static mounts `/static` (frontend) and `/static_content` (data) on by default in dev; off in tests by default.
- Admin diagnostics at `/api/v1/admin/monitoring/config` for safe verification.

## 5. Development Progress

- Q2 2025: Core fixes (auth errors, OpenAI client import guards), PDF/export polish, story draft/template features, and session timeout handling.
- Q3 2025: Characters domain (CRUD, regenerate, storage, thumbnails), wizard integration and reliability, inline modal status with accessibility, sticky glass header and progress bar with reduced-motion fallback, environment consolidation to root .env, admin config diagnostics, docs updates.

Status highlights
- Admin: dynamic lists and monitoring implemented; diagnostics endpoint live.
- Characters: reusable with regenerate; wizard integration complete.
- Tests: comprehensive and green; CI uses dummy OPENAI_API_KEY.
- Pending: forgot password, enhanced analytics/broadcasts, optional image style mapping UI, expanded screenshots in docs.
*   **FR-TEST-01:** Unit Tests: Implement comprehensive unit tests for all backend modules (CRUD operations, AI service interactions, API endpoints). (Previously FR10)



## 6. API Contracts

All endpoints are JSON over HTTP and, unless noted, require a Bearer token in the Authorization header. Base API prefix is `/api/v1`. Admin endpoints are under `/api/v1/admin` and require an admin token. Errors follow FastAPI’s default shape: `{ "detail": string }` with appropriate HTTP status codes.

### 6.1 Authentication

- POST `/api/v1/users/` — Register
    - Body: UserCreate { username, password, email? }
    - 200 OK → User; 400 on duplicate username/email

- POST `/api/v1/token` — Login
    - Body: form-data { username, password }
    - 200 OK → Token { access_token, token_type: "bearer" }; 401 on invalid creds

- GET `/api/v1/users/me/` — Current user
    - 200 OK → User

### 6.2 Stories

- POST `/api/v1/stories/` — Start generation
    - Body: StoryCreate (includes optional `character_ids` merge and wizard options)
    - 202 Accepted → StoryGenerationTask { id, story_id, user_id, status, progress, current_step, created_at, updated_at }
    - 400 if duplicate title; 401 if not authenticated

- GET `/api/v1/stories/generation-status/{task_id}` — Poll status
    - 200 OK → StoryGenerationTask; 404 if not found; 403 if not owner

- GET `/api/v1/stories/` — List user stories
    - Query: skip, limit, include_drafts (bool)
    - 200 OK → List[Story]

- GET `/api/v1/stories/{story_id}` — Get a story
    - 200 OK → Story; 404 if not found/unauthorized

- GET `/api/v1/stories/{story_id}/pdf` — Export PDF
    - 200 OK → application/pdf (download); 404 if not found/unauthorized

Note: Legacy/developer utility endpoints under `/stories/*` (no `/api/v1` prefix) may exist for drafts/backfill and are not part of the public contract.

### 6.3 Characters

Base path: `/api/v1/characters`

- POST `/` — Create or upsert by name
    - Body: CharacterCreate { name, description?, age?, gender?, clothing_style?, key_traits?, image_style?, generate_image? }
    - 201 Created → CharacterOut (optionally with generated `current_image`)

- GET `/` — List with search and pagination
    - Query: q?, page (>=1), page_size (1–100)
    - 200 OK → PaginatedCharacters { items: [ { id, name, updated_at, thumbnail_path? } ], total, page, page_size }

- GET `/{char_id}` — Get one
    - 200 OK → CharacterOut; 404 if not found

- PUT `/{char_id}` — Update
    - Body: CharacterUpdate (all fields optional)
    - 200 OK → CharacterOut; 404 if not found

- POST `/{char_id}/regenerate-image` — New image version, becomes current
    - Body: RegenerateImageRequest { description?, image_style? }
    - 200 OK → CharacterOut (refreshed); 401/503 for OpenAI auth/config issues; 500 on generation error

- DELETE `/{char_id}` — Delete
    - 204 No Content; 404 if not found

### 6.4 Dynamic Lists (public)

- GET `/api/v1/dynamic-lists/{list_name}/active-items`
    - 200 OK → List[DynamicListItemPublic { item_value, item_label }]; 404 if list doesn’t exist

### 6.5 Admin — Dynamic Lists

Base path: `/api/v1/admin/dynamic-lists`

- POST `/` — Create list
    - Body: DynamicListCreate { list_name, list_label?, description? }
    - 201 Created → DynamicList

- GET `/` — List lists
    - 200 OK → List[DynamicList]

- GET `/{list_name}` — Get one
    - 200 OK → DynamicList; 404 if not found

- PUT `/{list_name}` — Update metadata
    - Body: DynamicListUpdate { list_label?, description? }
    - 200 OK → DynamicList; 404 if not found

- DELETE `/{list_name}` — Delete
    - 204 No Content; 409 if any items are in use; 404 if not found

- POST `/{list_name}/items` — Create item
    - Body: DynamicListItemCreate { list_name, item_value, item_label, is_active?, sort_order?, additional_config? }
    - 201 Created → DynamicListItem; 400 if duplicate value

- GET `/{list_name}/items` — List items
    - Query: skip, limit, only_active?
    - 200 OK → List[DynamicListItem]

- GET `/items/{item_id}` — Get item
    - 200 OK → DynamicListItem; 404 if not found

- PUT `/items/{item_id}` — Update item
    - Body: DynamicListItemUpdate
    - 200 OK → DynamicListItem; 400 if new value duplicates another in same list; 404 if not found

- DELETE `/items/{item_id}` — Delete item
    - 204 No Content; 409 if in use; 404 if not found

- GET `/items/{item_id}/in-use` — Usage check
    - 200 OK → DynamicListItemUsage { is_in_use: bool, details: string[] }

### 6.6 Admin — Users Management

Base path: `/api/v1/admin/management/users`

- GET `/` — List users → List[User]
- GET `/{user_id}` — Get one → User; 404 if not found
- PUT `/{user_id}` — Update username/email/role/is_active → User; guards prevent self-demotion/deactivation; 400/403/404 on invalid ops

### 6.7 Admin — Monitoring

Base path: `/api/v1/admin/monitoring`

- GET `/logs/` — List log files → string[]
- GET `/logs/{log_file}` — Tail content; query `lines` (10–5000) → text/plain
- GET `/logs/{log_file}/download` — Download full file
- GET `/stats` — Basic system stats → JSON
- GET `/metrics` — Prometheus-style stub → text/plain
- GET `/config` — Safe config diagnostics → { openai_key_present, openai_key_masked, text_model, image_model, run_env, enable_image_style_mapping, mount_frontend_static, mount_data_static, frontend_static_dir, data_dir, logs_dir, client_initialized }

Schemas
- The canonical schema definitions live in `backend/schemas.py`. Fields in responses map 1:1 to those Pydantic models unless otherwise noted above.
