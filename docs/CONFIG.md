# Configuration Guide

This project reads configuration from environment variables with sensible defaults defined in `backend/settings.py`. A subset is also read by `backend/auth.py` (JWT), which calls `load_dotenv()` to make `.env` files convenient in development.

Quick start
- Copy `.env.example` to `.env` in the repository root (recommended), or to `backend/.env`.
- Set SECRET_KEY and (for non-test runs) OPENAI_API_KEY.
- Optionally set DATA_DIR and LOGS_DIR to control storage locations.

Where .env is loaded from
- `backend/auth.py` calls `load_dotenv()` with no path, which loads a `.env` file from the current working directory or its parents.
- Recommended: keep `.env` at the repo root.
- If you keep it at `backend/.env`, start the server with the working directory set to `backend/`, or export the variables in your shell.

Configuration reference (env var → default)
- RUN_ENV → dev
  - dev|test|prod. When `test`, static mounts are disabled by default.
- API_PREFIX → /api/v1
  - Base path for all API routes.
- SECRET_KEY → your-default-secret-key (from auth.py)
  - JWT signing key. REQUIRED in production.
- FRONTEND_DIR → frontend
  - Files served at `/static/*` when mounted.
- DATA_DIR → data
  - Root for generated content (images, prompts, PDFs, etc.). Files are saved under this folder. DB image paths are relative to this folder.
- MOUNT_FRONTEND_STATIC → true unless RUN_ENV=test
  - Set to `true`/`1` to mount `/static` to FRONTEND_DIR.
- MOUNT_DATA_STATIC → true unless RUN_ENV=test
  - Set to `true`/`1` to mount `/static_content` to DATA_DIR for serving generated files.
- LOGS_DIR → <DATA_DIR>/logs
  - Location for rotated log files.
- LOGGING_CONFIG → config/logging.yaml
  - Path to dictConfig YAML.
- CORS_ORIGINS → "" (empty)
  - Comma-separated list of allowed origins.
- OPENAI_API_KEY → unset
  - Required for real AI image/text generation (tests mock these calls and don’t need it).
- TEXT_MODEL → gpt-4.1-mini
- IMAGE_MODEL → gpt-image-1
- RETRY_MAX_ATTEMPTS → 3
- RETRY_BACKOFF_BASE → 1.5
 - ENABLE_IMAGE_STYLE_MAPPING → false
   - When true, maps Story.image_style (e.g., "Photorealistic") to a richer phrase (e.g., "highly detailed photorealistic").

Database
- DATABASE_URL controls the database connection string. Default: `sqlite:///./story_generator.db`.
- SQLite requires `check_same_thread=False` (handled automatically).
- Examples:
  - `sqlite:///./story_generator.db`
  - `sqlite:////absolute/path/to/story_generator.db`
  - `postgresql+psycopg://user:pass@host:5432/dbname` (driver must be installed)

Environment presets
- Local development
  - RUN_ENV=dev
  - MOUNT_FRONTEND_STATIC=true
  - MOUNT_DATA_STATIC=true
  - Set SECRET_KEY and OPENAI_API_KEY
- Test/CI
  - RUN_ENV=test
  - MOUNT_DATA_STATIC=true (so `/static_content/*` is available for tests)
  - OPENAI_API_KEY not required; tests mock AI
- Production
  - RUN_ENV=prod
  - Provide strong SECRET_KEY, set OPENAI_API_KEY
  - Point DATA_DIR and LOGS_DIR to persistent, writable locations
  - Consider restricting CORS_ORIGINS

Static content behavior
- Image and prompt files are stored under `DATA_DIR`.
- The API serves them at `/static_content/*` only when MOUNT_DATA_STATIC is enabled.
- Paths saved in the database are always relative to `DATA_DIR` (e.g., `images/user_1/story_2/page_1.png`).

Logging
- Configured via YAML (`config/logging.yaml`) and written to `LOGS_DIR` with daily rotation.
- You can adjust logger levels and handlers in YAML; environment can override levels if wired in the YAML.

Troubleshooting
- “/static_content not found” in dev/test
  - Ensure MOUNT_DATA_STATIC=true and that your client was created after the mount (tests handle this automatically).
- “.env not loading”
  - Prefer placing `.env` in the repo root. If using `backend/.env`, start the app with working directory `backend/` or export variables.
- “OpenAI calls failing”
  - Verify OPENAI_API_KEY is set. In CI/tests, these calls are mocked and the key isn’t needed.

Related docs
- See README.md for quick start and route details.
 - See backend/image_style_mapping.py for default mappings or to extend them.
