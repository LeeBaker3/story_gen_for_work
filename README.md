# Story Generator API

FastAPI backend that generates illustrated stories using OpenAI. It handles authentication, story creation, character reference images, per‑page image generation, browsing, and PDF export. A minimal frontend lives under `frontend/` and static content is served by the API when enabled.

## Quick start

Prereqs
- Python 3.13
- OpenAI API key

Setup
- python3.13 -m venv .venv; source .venv/bin/activate
- pip install -r backend/requirements.txt
- Create backend/.env with at least OPENAI_API_KEY and SECRET_KEY

Run (dev)
- uvicorn backend.main:app --reload
- Open http://127.0.0.1:8000/docs for API docs

## API shape and routes
- API prefix: default /api/v1 (configurable)
- Auth: POST /api/v1/token (OAuth2 password) returns bearer token
- Public story flow:
    - POST /api/v1/stories/ to create and start generation (202)
    - GET /api/v1/stories/ to list user stories
    - GET /api/v1/stories/{id} to fetch a story
    - GET /api/v1/stories/generation-status/{task_id} to check background progress
- Health: GET /healthz
- Admin monitoring (admin token required):
    - GET /api/v1/admin/monitoring/logs/ (list .log files)
    - GET /api/v1/admin/monitoring/logs/{file}?lines=N (tail last N lines; bounds 10–5000)
    - GET /api/v1/admin/monitoring/logs/{file}/download (download full log)
    - GET /api/v1/admin/monitoring/stats (basic system stats)
    - GET /api/v1/admin/monitoring/metrics (stubbed counter example)

Static content
- Frontend static (if mounted): GET /static/* serves files from frontend/
- User data (if mounted): GET /static_content/* serves files from DATA_DIR
- Image paths stored in DB are relative to DATA_DIR (e.g., images/user_1/story_2/...)

## Configuration
All configuration is centralized in backend/settings.py and read from environment variables. Sensible defaults are provided. See docs/CONFIG.md for a full guide and .env usage.

Core
- RUN_ENV: dev|test|prod (default: dev). Test disables static mounts unless overridden.
- API_PREFIX: API base path (default: /api/v1)
- SECRET_KEY: JWT signing key (required in production)

Static & storage
- FRONTEND_DIR: directory for frontend static (default: frontend)
- DATA_DIR: base directory for generated data (default: data)
- MOUNT_FRONTEND_STATIC: 1/true to mount /static (default: true unless RUN_ENV=test)
- MOUNT_DATA_STATIC: 1/true to mount /static_content (default: true unless RUN_ENV=test)

Logging
- LOGS_DIR: directory for logs (default: DATA_DIR/logs)
- LOGGING_CONFIG: path to YAML (default: config/logging.yaml)
    - Daily rotation handlers for app, api, error logs
    - Levels can be overridden via env per logger name if configured in YAML

OpenAI models and retries
- OPENAI_API_KEY: key for OpenAI
- TEXT_MODEL: default gpt-4.1-mini
- IMAGE_MODEL: default gpt-image-1
- RETRY_MAX_ATTEMPTS: default 3
- RETRY_BACKOFF_BASE: default 1.5

CORS
- CORS_ORIGINS: comma-separated origins (optional)

Database
- DATABASE_URL: database connection string (default sqlite:///./story_generator.db)
- SQLite is supported out of the box; for Postgres, install a suitable driver (e.g., psycopg)
- Tables auto-created on startup; seed data is applied during app startup lifespan

## Running
Dev server
- From repo root with venv active:
    - uvicorn backend.main:app --reload

Static mounts
- By default, static mounts are enabled unless RUN_ENV=test.
- To force in any environment: set MOUNT_FRONTEND_STATIC=true and/or MOUNT_DATA_STATIC=true.

Docs
- Swagger UI: /docs
- ReDoc: /redoc
 - Configuration Guide: docs/CONFIG.md (env, logging, monitoring endpoints/UI)

## Authentication
- OAuth2 Password Bearer; obtain token via POST /api/v1/token.
- Use Authorization: Bearer <token> for subsequent requests.
- Admin-only endpoints require a user with role=admin.
- A helper script `create_admin.py` exists to create an admin user if needed.

## Testing
Test runner: pytest

Run all tests
- From repo root with venv active: pytest -q

Run a single test
- pytest -q backend/tests/test_public_endpoints.py::test_login_flow

Notes
- Tests use an in-memory SQLite DB and override the app DB dependency; no local DB file is modified.
- Some tests rely on /static_content being mounted. If RUN_ENV=test is set, also set MOUNT_DATA_STATIC=true to enable static serving in tests.
- Integration tests mock OpenAI calls and write small fake image/prompt files under DATA_DIR.

## Storage paths
- Images are stored under DATA_DIR/images/user_{id}/story_{id}/...
- Character references under .../references
- Filenames are sanitized and include short IDs for uniqueness.
- Paths saved to DB are always relative to DATA_DIR, so they can be served at /static_content/...

## Logging
- Configured via YAML at config/logging.yaml with dictConfig.
- Default logs write to DATA_DIR/logs with daily rotation.
- Adjust levels via environment or YAML per logger.
 - Admin UI → System Monitoring can list/tail/download logs; LOGS_DIR is honored.

## Deployment
Minimal
- Set RUN_ENV=prod, provide SECRET_KEY and OPENAI_API_KEY, and point DATA_DIR/LOGS_DIR to writable paths.
- Start with uvicorn:
    - uvicorn backend.main:app --host 0.0.0.0 --port 8000

With a process manager/proxy
- Use systemd, Docker, or a supervisor to run uvicorn/gunicorn.
- Put a reverse proxy (e.g., Nginx) in front for TLS and caching static files.
- Ensure DATA_DIR and LOGS_DIR are persisted (volumes).

## Project structure (high level)
- backend/
    - main.py (includes routers, static mounts, /healthz)
    - public_router.py, admin_router.py, monitoring_router.py
    - ai_services.py, story_generation_service.py, storage_paths.py
    - logging_config.py (+ config/logging.yaml), settings.py
    - auth.py, crud.py, database.py, database_seeding.py, pdf_generator.py
    - tests/
- frontend/ (static assets)
- data/ (generated images, logs; configurable via DATA_DIR)
- story_generator.db (SQLite, dev default)

## CI with GitHub Actions
You can run tests on every push or pull request using GitHub Actions.

Key points
- Python 3.13 runtime
- Install backend requirements only
- Use RUN_ENV=test and enable MOUNT_DATA_STATIC so static routes work in tests
- OpenAI calls are mocked in tests, so no OPENAI_API_KEY is required for CI

Example workflow: .github/workflows/ci.yml
```yaml
name: CI

on:
    push:
        branches: [ main ]
    pull_request:
        branches: [ main ]

jobs:
    test:
        runs-on: ubuntu-latest
        steps:
            - name: Checkout
                uses: actions/checkout@v4

            - name: Set up Python
                uses: actions/setup-python@v5
                with:
                    python-version: '3.13'

            - name: Cache pip
                uses: actions/cache@v4
                with:
                    path: ~/.cache/pip
                    key: ${{ runner.os }}-pip-${{ hashFiles('backend/requirements.txt') }}
                    restore-keys: |
                        ${{ runner.os }}-pip-

            - name: Install dependencies
                run: |
                    python -m pip install --upgrade pip
                    pip install -r backend/requirements.txt

            - name: Run tests
                env:
                    RUN_ENV: test
                    MOUNT_DATA_STATIC: 'true'
                    # Optional: set DATA_DIR to a workspace path if desired
                    # DATA_DIR: data
                run: |
                    pytest -q
```

Notes
- If you later add linting or type checks, append steps before running tests.
- If you add integration tests requiring external services, gate those with a label or separate job.

