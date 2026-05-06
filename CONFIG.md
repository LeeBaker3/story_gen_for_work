# Configuration Guide

This project reads configuration from environment variables (typically via a root-level .env file) and sane in-code defaults. Use this guide to configure local dev, CI, and production environments.

Recommended: create a .env file in the repository root (NOT in backend/). The backend loads the root .env early during import so values are available for settings and AI services.

## Quick .env example

Copy .env.example to .env and adjust values as needed.

Key minimums for local dev
- SECRET_KEY=change-me
- OPENAI_API_KEY=your-key (required for real AI calls; tests can use a dummy)
- RUN_ENV=dev
- MOUNT_FRONTEND_STATIC=true
- MOUNT_DATA_STATIC=true

Optional low-cost local AI example
- OPENAI_API_KEY=dummy-local-key
- OPENAI_BASE_URL=http://localhost:11434/v1
- TEXT_MODEL=gpt-oss:20b
- ENABLE_IMAGE_GENERATION=false

## Environment variables

Core
- RUN_ENV: dev | test | prod (default: dev)
  - test disables static mounts by default. Override via MOUNT_* flags if needed.
- API_PREFIX: API base path (default: /api/v1)
- SECRET_KEY: JWT signing key (required in prod)

Static & storage
- FRONTEND_DIR: directory to serve at /static (default: frontend)
- DATA_DIR: base directory for generated data (default: data)
- PRIVATE_DATA_DIR: base directory for private user uploads that must not be publicly accessible (default: private_data)
- MAX_UPLOAD_BYTES: maximum allowed size for uploads (default: 10485760 / 10MB)
- MOUNT_FRONTEND_STATIC: "1"/"true" to mount /static (default: true unless RUN_ENV=test)
- MOUNT_DATA_STATIC: "1"/"true" to mount /static_content (default: true unless RUN_ENV=test)

Logging
- LOGS_DIR: directory for logs (default: DATA_DIR/logs)
- LOGGING_CONFIG: path to logging YAML (default: config/logging.yaml)

OpenAI models and retries
- OPENAI_API_KEY: API key for OpenAI
- OPENAI_BASE_URL: optional shared OpenAI-compatible base URL override for local/self-hosted providers (default: hosted OpenAI)
- OPENAI_TEXT_BASE_URL: optional text-generation base URL override; takes precedence over OPENAI_BASE_URL
- OPENAI_IMAGE_BASE_URL: optional image-generation base URL override; takes precedence over OPENAI_BASE_URL
- OPENAI_TEXT_PROVIDER: optional diagnostic label for the active text provider (default: inferred from base URL)
- OPENAI_IMAGE_PROVIDER: optional diagnostic label for the active image provider (default: inferred from base URL)
- TEXT_MODEL: LLM for story text (default: gpt-5.4-mini)
- IMAGE_MODEL: image model (default: gpt-image-2)
- ENABLE_IMAGE_GENERATION: "1"/"true" to enable AI image generation; set to false for lower-cost local dev/test text-only workflows (default: true)
- USE_OPENAI_RESPONSES_API: "1"/"true" to use the Responses API for story text generation (default: false)
- OPENAI_TEXT_ENABLE_FALLBACK: "1"/"true" to fall back to the other text path if the primary fails (default: false)
- RETRY_MAX_ATTEMPTS: API retry attempts (default: 3)
- RETRY_BACKOFF_BASE: exponential backoff base seconds (default: 1.5)
- ENABLE_IMAGE_STYLE_MAPPING: "1"/"true" to map friendly style names to richer prompts (default: false)

Provider notes
- If no base URL override is supplied, both text and image generation use hosted OpenAI defaults.
- For local OpenAI-compatible text providers, point OPENAI_BASE_URL or OPENAI_TEXT_BASE_URL at the local endpoint and keep IMAGE generation disabled unless that provider also supports the image API your workflow needs.
- Admin monitoring exposes the active provider labels and normalized base URLs at `/api/v1/admin/monitoring/config` without exposing secrets.

Authentication
- LOGIN_RATE_LIMIT: rate limit applied to login attempts (default: 10/minute)

OpenAI smoke testing (manual)
- SMOKE_EDIT_IMAGE_PATH: local path to a real PNG/JPG/WebP file used by scripts/smoke_test_openai.py to test Images Edits.

CORS
- CORS_ORIGINS: comma-separated list of allowed origins (optional)

Database
- DATABASE_URL: SQLAlchemy URL (default: sqlite:///./story_generator.db)

Alembic migrations
- The repository now includes a minimal Alembic scaffold rooted at `alembic.ini` and `alembic/`.
- Alembic resolves `DATABASE_URL` from the environment, matching the app's SQLAlchemy connection target.
- Alembic autogenerate uses `backend.database.Base.metadata`, so revisions are based on the existing backend model definitions.
- Current runtime bootstrap remains in place for dev/test compatibility: startup still runs `create_all` and the SQLite `_ensure_*` helpers.
- Typical commands:
  - `./.venv/bin/python -m alembic -c alembic.ini revision --autogenerate -m "describe change"`
  - `./.venv/bin/python -m alembic -c alembic.ini upgrade head`
  - `./.venv/bin/python -m alembic -c alembic.ini downgrade -1`

## Admin bootstrap (create first admin)

Use `create_admin.py` to create the first admin user, or to promote an existing
user. The script is idempotent and will not reset passwords unless you request
it.

Typical local usage (recommended)
- Create admin (username defaults to email) and prompt for password:
  - `python create_admin.py --email admin@example.com --prompt-password`

Promote an existing user
- Promote by username/email without changing password:
  - `python create_admin.py --username existing@example.com --no-create-if-missing`

Reset password (explicit)
- Update password for an existing user (requires `--set-password`):
  - `python create_admin.py --email admin@example.com --set-password --prompt-password`

Database selection
- By default, uses `DATABASE_URL` (or SQLite fallback).
- Override for a single run:
  - `python create_admin.py --email admin@example.com --prompt-password --db-url sqlite:///./story_generator.db`
- For non-interactive environments, you may provide `ADMIN_PASSWORD` instead of
  prompting.

## Dynamic Lists Reference

Dynamic lists are admin-editable option sets that populate dropdowns in the story wizard, editor, and PDF export. They are managed in the Admin Panel under **Dynamic Lists** and seeded with sensible defaults on first startup.

Use the admin panel to add, disable, or reorder items without restarting the app. Disabling an item hides it from new story creation but does not affect existing stories that already reference it.

> **Note:** Removing or renaming a `font_families` value requires that the corresponding font is registered in the PDF generator. Test PDF export after any font-family changes.

### Seeded lists

| List name | Admin label | Purpose |
|---|---|---|
| `genres` | Genres | Story genre (e.g., Fantasy, Sci-Fi) used in wizard Step 3 and image prompts |
| `image_styles` | Image Styles | Visual style for AI image generation (e.g., Watercolor, Pixel Art) |
| `tones` | Tones | Narrative tone (e.g., Humorous, Serious) |
| `settings` | Settings | Story setting (e.g., Forest, Space Station) |
| `writing_styles` | Writing Styles | Writing style (e.g., Descriptive, Minimalist) |
| `text_positions` | Text Positions | Default placement of text on a page in the wizard, editor, and PDF export |
| `font_families` | Font Families | Default document typography applied in the editor and PDF export |

### `text_positions` — Text Positions

Controls where text is positioned on a page by default. Chosen in the wizard (Step 3) and editable per-page in the story editor. The value is also passed to image generation prompts so the AI can leave suitable visual space.

Default seeded values:

| Value | Label | Notes |
|---|---|---|
| `top` | Top | Text at the top of the page |
| `bottom` | Bottom | Text at the bottom of the page |
| `left` | Left | Text in a left-side column |
| `right` | Right | Text in a right-side column |
| `center` | Center | Text overlaid in the centre |

Affects: wizard Step 3 dropdown, editor page-level override, PDF layout, image generation prompt guidance.

### `font_families` — Font Families

Controls the default document typography. Chosen in the wizard (Step 3) and editable as a document-wide default in the story editor.

Default seeded values:

| Value | Label | Notes |
|---|---|---|
| `storybook` | Storybook | Friendly, rounded font suited to children's stories |
| `classic` | Classic | Traditional serif font |
| `modern` | Modern | Clean sans-serif font |
| `handwritten` | Handwritten | Script-style font |
| `dyslexia-friendly` | Dyslexia-friendly | High-legibility font designed for readability |
| `large print` | Large print | Larger base size for low-vision readers |

Affects: wizard Step 3 dropdown, editor document defaults, PDF export font selection.

> **Important:** Adding a new font-family item requires registering the corresponding font file in the PDF generator (`backend/pdf_generator.py`). Disabling an item is safe; it will be hidden from new stories but existing stories are not affected.

## Notes & safe defaults

- The backend prefers the repository root .env. If backend/.env also exists, it is only used to fill missing values (never overriding root or shell env).
- Paths saved in the database are relative to DATA_DIR, so they are served under /static_content/ consistently.
- Uploaded character photos are stored under PRIVATE_DATA_DIR and are never served from /static_content.
- For CI, use OPENAI_API_KEY=dummy-ci-key and mock OpenAI calls in tests (already done in the test suite).

## Migration notes

Previously, some instructions referenced backend/.env. The application now standardizes on a single root-level .env. If you still have backend/.env, move its content to the root .env and delete the backend file to avoid confusion.
