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

Staging/prod baseline
- RUN_ENV=staging or RUN_ENV=prod
- DATABASE_URL=<Neon Postgres connection string>
- DB_BOOTSTRAP_MODE=migrations
- ASSET_STORAGE_BACKEND=s3
- ASSET_STORAGE_PUBLIC_PREFIX=public
- ASSET_STORAGE_PRIVATE_PREFIX=private
- ASSET_STORAGE_S3_BUCKET=<bucket>
- ASSET_STORAGE_S3_REGION=<region>

Optional low-cost local AI example
- OPENAI_API_KEY=dummy-local-key
- OPENAI_BASE_URL=http://localhost:11434/v1
- TEXT_MODEL=gpt-oss:20b
- ENABLE_IMAGE_GENERATION=false

## Environment variables

Core
- RUN_ENV: dev | test | staging | prod (default: dev)
  - test disables static mounts by default. Override via MOUNT_* flags if needed.
- API_PREFIX: API base path (default: /api/v1)
- SECRET_KEY: JWT signing key (required in prod)

Static & storage
- FRONTEND_DIR: directory to serve at /static (default: frontend)
- DATA_DIR: base directory for generated data (default: data)
- PRIVATE_DATA_DIR: base directory for private user uploads that must not be publicly accessible (default: private_data)
- MAX_UPLOAD_BYTES: maximum allowed size for uploads (default: 10485760 / 10MB)
- MOUNT_FRONTEND_STATIC: "1"/"true" to mount /static (default: true unless RUN_ENV=test)
- MOUNT_DATA_STATIC: "1"/"true" to mount /static_content (default: true unless RUN_ENV=test; forced off when ASSET_STORAGE_BACKEND=s3)
- ASSET_STORAGE_BACKEND: filesystem | s3 (default: filesystem in dev/test, s3 in staging/prod)
- ASSET_STORAGE_PUBLIC_PREFIX: object-storage prefix for public assets (default: public)
- ASSET_STORAGE_PRIVATE_PREFIX: object-storage prefix for private assets (default: private)
- ASSET_STORAGE_S3_BUCKET: bucket/container name required when ASSET_STORAGE_BACKEND=s3
- ASSET_STORAGE_S3_REGION: region required when ASSET_STORAGE_BACKEND=s3
- ASSET_STORAGE_S3_ENDPOINT_URL: optional endpoint override for S3-compatible providers
- ASSET_STORAGE_S3_ACCESS_KEY_ID: optional runtime credential field for later object-storage integration
- ASSET_STORAGE_S3_SECRET_ACCESS_KEY: optional runtime credential field for later object-storage integration

Asset prefix rules
- Public asset keys use `ASSET_STORAGE_PUBLIC_PREFIX/<legacy-relative-path>`.
- Private asset keys use `ASSET_STORAGE_PRIVATE_PREFIX/<legacy-relative-path>`.
- Legacy database values that only contain the relative path remain accepted for local filesystem resolution.
- Story page images remain private from `/static_content`; object-storage mode disables the local `/static_content` mount entirely.

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
- SIGNUP_RATE_LIMIT: rate limit applied to public signup requests (default: 5/hour)
- PASSWORD_RESET_REQUEST_RATE_LIMIT: rate limit applied to password reset requests (default: falls back to LOGIN_RATE_LIMIT)
- PASSWORD_RESET_CONFIRM_RATE_LIMIT: rate limit applied to password reset confirmations (default: 10/hour)
- AUTH_COOKIE_NAME: HttpOnly browser auth cookie name set on successful login (default: story_generator_auth)
- AUTH_COOKIE_SECURE: whether the browser auth cookie requires HTTPS (default: true in prod, false elsewhere)
- AUTH_COOKIE_SAMESITE: SameSite policy for the browser auth cookie (default: lax)
- EXPOSE_PASSWORD_RESET_TOKEN_PREVIEW: when true, include reset_token_preview in password-reset request responses outside tests/dev tooling (default: false)

Authentication notes
- POST /api/v1/token still returns a bearer token for API clients and also sets the configured HttpOnly browser auth cookie.
- Browser flows use same-origin requests with credentials so cookie auth works without exposing the token to frontend JavaScript.
- Password reset requests always return a generic success message to avoid revealing whether an account exists.
- reset_token_preview is intended for tests and local/dev workflows only. In prod-like environments it stays off unless EXPOSE_PASSWORD_RESET_TOKEN_PREVIEW is explicitly enabled.

Billing
- STRIPE_SECRET_KEY: Stripe secret key used for authenticated Checkout and Customer Portal API calls
- STRIPE_WEBHOOK_SECRET: Stripe webhook signing secret used to verify webhook delivery signatures
- STRIPE_MONTHLY_PRICE_ID: Stripe price id for the single monthly beta subscription plan
- STRIPE_CHECKOUT_SUCCESS_URL: redirect URL Stripe uses after successful Checkout completion
- STRIPE_CHECKOUT_CANCEL_URL: redirect URL Stripe uses when Checkout is cancelled
- STRIPE_CUSTOMER_PORTAL_RETURN_URL: return URL used when a customer exits the Stripe billing portal
- STRIPE_MONTHLY_STORY_CREDITS: monthly included story credits granted on each paid invoice (default: 30)
- STRIPE_MONTHLY_IMAGE_CREDITS: monthly included image credits granted on each paid invoice (default: 100)

Billing notes
- Billing is backend-only in this slice: the API exposes authenticated Checkout and Portal session creation plus a Stripe webhook endpoint.
- The application remains entitlement-driven. Stripe events sync `account_entitlements`; app access still reads from `/api/v1/users/me/entitlement`.
- Monthly paid credits are period-scoped. Renewals reset the configured totals and usage is counted only within the current paid billing period.

OpenAI smoke testing (manual)
- SMOKE_EDIT_IMAGE_PATH: local path to a real PNG/JPG/WebP file used by scripts/smoke_test_openai.py to test Images Edits.

CORS
- CORS_ORIGINS: comma-separated list of allowed origins (optional)

Database
- DATABASE_URL: SQLAlchemy URL (default: sqlite:///./story_generator.db)
- DB_BOOTSTRAP_MODE: runtime | migrations (default: runtime in dev/test, migrations in staging/prod)

Story generation runtime
- STORY_GENERATION_RUNTIME_ROLE: api | worker | combined (default: combined)
- STORY_GENERATION_WORKER_POLL_INTERVAL_SECONDS: worker poll interval in seconds for pending tasks (default: 5)
- STORY_GENERATION_STALE_TASK_TIMEOUT_SECONDS: worker-side timeout in seconds before stale `in_progress` tasks are failed during recovery (default: 900)
- STORY_WORKER_RUNTIME_ID: stable worker identifier stored in the shared heartbeat table (default: host name)
- WORKER_HEARTBEAT_STALE_AFTER_SECONDS: heartbeat age threshold used to mark the worker healthy or stale in ops metrics (default: max(STORY_GENERATION_WORKER_POLL_INTERVAL_SECONDS * 3, 30))
- OPS_METRICS_BEARER_TOKEN: dedicated bearer token for `GET /api/v1/ops/metrics`; leave unset to disable the machine-facing scrape path
- RUNTIME_ALERT_WEBHOOK_URL: optional generic outbound webhook for high-severity unhandled worker-loop and API runtime exceptions
- RUNTIME_ALERT_WEBHOOK_TIMEOUT_SECONDS: best-effort webhook timeout in seconds for runtime alerts (default: 2.0)

Story generation runtime notes
- `combined` preserves the existing local-dev behavior: `POST /api/v1/stories/` both enqueues and executes generation in-process.
- `api` keeps the existing request/response contract but only persists the story shell and task record.
- `worker` runs the standalone poller via `python -m backend.story_worker` and executes one task at a time.
- The split runtime is intentionally single-worker only for this slice.
- The worker heartbeat is persisted in the shared database so the API runtime can expose queue state and worker freshness through `/api/v1/ops/metrics` without a direct worker-to-API dependency.
- `/api/v1/admin/monitoring/metrics` remains admin-authenticated and intact; `/api/v1/ops/metrics` is the separate machine-facing scrape surface.
- Runtime alerting in this slice is intentionally minimal: one best-effort JSON webhook for high-severity unhandled failures only, not a full alert engine.

Runtime guarantees
- Staging/prod fail fast if DATABASE_URL points at SQLite.
- Staging/prod fail fast if DB_BOOTSTRAP_MODE is not `migrations`.
- Staging/prod fail fast if ASSET_STORAGE_BACKEND is `filesystem`.
- Any environment using ASSET_STORAGE_BACKEND=`s3` fails fast unless at least `ASSET_STORAGE_S3_BUCKET` and `ASSET_STORAGE_S3_REGION` are set.

Alembic migrations
- The repository now includes a minimal Alembic scaffold rooted at `alembic.ini` and `alembic/`.
- Alembic resolves `DATABASE_URL` from the environment, matching the app's SQLAlchemy connection target.
- Alembic autogenerate uses `backend.database.Base.metadata`, so revisions are based on the existing backend model definitions.
- Runtime bootstrap remains in place for dev/test compatibility only: startup still runs `create_all` and the SQLite `_ensure_*` helpers when `DB_BOOTSTRAP_MODE=runtime`.
- Staging/prod must run Alembic before the app starts; runtime startup no longer bootstraps schema in those environments.
- Typical commands:
  - `./.venv/bin/python -m alembic -c alembic.ini revision --autogenerate -m "describe change"`
  - `./.venv/bin/python -m alembic -c alembic.ini upgrade head`
  - `./.venv/bin/python -m alembic -c alembic.ini downgrade -1`

Staging baseline operations
- Database target: Neon Postgres.
- Asset storage target: S3-compatible object storage.
- Backup retention baseline: keep at least 14 days of restorable Neon backups/PITR and 14 days of object-storage versioned backups or replicated snapshots.
- Initial restore runbook: see `docs/staging_restore_runbook.md`.
- Split runtime deploy runbook: see `docs/split_runtime_deploy_runbook.md`.
- Split runtime rollback runbook: see `docs/split_runtime_rollback_runbook.md`.
- Provider outage runbook: see `docs/provider_outage_runbook.md`.

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
- Local filesystem paths saved in the database remain relative to DATA_DIR and are served under /static_content/ when that mount is enabled.
- Public object-storage keys are expected to live under ASSET_STORAGE_PUBLIC_PREFIX and private keys under ASSET_STORAGE_PRIVATE_PREFIX.
- Uploaded character photos are stored under PRIVATE_DATA_DIR and are never served from /static_content.
- For CI, use OPENAI_API_KEY=dummy-ci-key and mock OpenAI calls in tests (already done in the test suite).

## Migration notes

Previously, some instructions referenced backend/.env. The application now standardizes on a single root-level .env. If you still have backend/.env, move its content to the root .env and delete the backend file to avoid confusion.
