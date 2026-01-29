# Story Generator API ![coverage](coverage_badge.svg) [![Release](https://img.shields.io/github/v/release/LeeBaker3/story_gen_for_work?display_name=tag&sort=semver)](https://github.com/LeeBaker3/story_gen_for_work/releases/latest)

FastAPI backend that generates illustrated stories using OpenAI. It handles authentication, story creation, character reference images, per‑page image generation, browsing, and PDF export. A modern frontend lives under `frontend/` with a wizard, Characters library, inline status feedback, and static content served by the API when enabled.

## Releases
- Automated with Release Please (manifest mode) covering three components:
    - Root (tag: vX.Y.Z)
    - Backend (tag: backend-vX.Y.Z; version source: `backend/version.py`)
    - Frontend (tag: frontend-vX.Y.Z; version source: `frontend/version.json`)
- Triggered on merge to main; versions are inferred from Conventional Commits.
- Manual run (optional): GitHub Actions → “Release Please” → Run workflow; you can provide an optional release_as version override.

Latest releases
- Root: https://github.com/LeeBaker3/story_gen_for_work/releases/latest
- Backend: https://github.com/LeeBaker3/story_gen_for_work/releases/tag/backend-v0.5.0
- Frontend: https://github.com/LeeBaker3/story_gen_for_work/releases/tag/frontend-v0.5.0

## Quick start

Prereqs
- Python 3.13
- OpenAI API key

Setup
- python3.13 -m venv .venv; source .venv/bin/activate
- pip install -r backend/requirements.txt
- Copy `.env.example` to `.env` in the repo root and set at least OPENAI_API_KEY and SECRET_KEY (see CONFIG.md)

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
    - GET /api/v1/admin/monitoring/metrics (Prometheus exposition)

Admin monitoring UI highlights
- Persisted preferences: selected log file, tail length, auto‑refresh, and filters are saved to localStorage.
- Follow tail: when enabled, the viewer auto‑scrolls to the bottom after each refresh.
- Client‑side filtering: plain text or regex, with invert option.

Admin Stats
- Endpoint: GET /api/v1/admin/stats (admin only)
- Metrics: users (total/active), stories (total/generated/drafts), total characters, task breakdown for last 24h (total/completed/failed/in-progress), average task duration for last 24h (prefers precise duration_ms, falls back to timestamps), success rate (completed / (completed + failed)), and average attempts over completed tasks in the last 24h.

Admin user management
- List users: GET /api/v1/admin/management/users/ (excludes soft-deleted by default)
- Get user: GET /api/v1/admin/management/users/{id}
- Update user: PUT /api/v1/admin/management/users/{id}
- Soft delete user: DELETE /api/v1/admin/management/users/{id} (cannot delete self)

Admin content moderation
- List stories for moderation: GET /api/v1/admin/moderation/stories
    - Query params: page, page_size, user_id, status_filter, created_from, created_to, include_hidden, include_deleted
    - Returns Story items; hidden/deleted included only if flags are set
- Hide/unhide a story: PATCH /api/v1/admin/moderation/stories/{id}/hide with body { is_hidden: boolean }
- Soft delete a story: DELETE /api/v1/admin/moderation/stories/{id}
Notes
- Soft-deleted users are excluded from admin lists by default but remain in the database for auditability.
- Stories support moderation flags is_hidden and is_deleted; hidden stories remain visible to admins but are suppressed from public/user listings.

Static content
- Frontend static (if mounted): GET /static/* serves files from frontend/
- User data (if mounted): GET /static_content/* serves files from DATA_DIR
- Image paths stored in DB are relative to DATA_DIR (e.g., images/user_1/story_2/...)

## Configuration
All configuration is centralized in backend/settings.py and read from environment variables. Sensible defaults are provided. Use a single root-level `.env`. See CONFIG.md for a full guide and .env usage.

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
- TEXT_MODEL: default gpt-5-mini
- IMAGE_MODEL: default gpt-image-1.5
- USE_OPENAI_RESPONSES_API: 1/true to use Responses API for story text (default: false)
- OPENAI_TEXT_ENABLE_FALLBACK: 1/true to fall back to the other text path if the primary fails (default: false)
- RETRY_MAX_ATTEMPTS: default 3
- RETRY_BACKOFF_BASE: default 1.5

CORS
- CORS_ORIGINS: comma-separated origins (optional)

Database
- DATABASE_URL: database connection string (default sqlite:///./story_generator.db)
- SQLite is supported out of the box; for Postgres, install a suitable driver (e.g., psycopg)
- Tables auto-created on startup; seed data is applied during app startup lifespan
 - In dev/test, startup helpers idempotently add new columns (task tracking, soft-delete/moderation). Use proper migrations (e.g., Alembic) for production.

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
 - Configuration Guide: CONFIG.md (env, logging, monitoring endpoints/UI)
 - API Contracts: see docs/PRODUCT_REQUIREMENTS_DOCUMENT.md (Section 6)

## Authentication
- OAuth2 Password Bearer; obtain token via POST /api/v1/token.
- Use Authorization: Bearer <token> for subsequent requests.
- Admin-only endpoints require a user with role=admin.
- A helper script `create_admin.py` exists to create an admin user if needed.

## Testing
Test runner: pytest

Run all tests
- From repo root with venv active: pytest -q

Run with coverage (terminal + XML, updates coverage.xml; badge manual regeneration):
- pytest --cov=backend --cov-report=term-missing --cov-report=xml:coverage.xml

Automated badge: GitHub Action (coverage.yml) runs on pushes/PRs to main, regenerating coverage.xml and coverage_badge.svg.

Run a single test
- pytest -q backend/tests/test_public_endpoints.py::test_login_flow

Notes
- Tests use an in-memory SQLite DB and override the app DB dependency; no local DB file is modified.
- Some tests rely on /static_content being mounted. If RUN_ENV=test is set, also set MOUNT_DATA_STATIC=true to enable static serving in tests.
 - Integration tests mock OpenAI calls and write small fake image/prompt files under DATA_DIR.

### OpenAI smoke test (manual)
Use the real-API smoke test to validate your API key, text generation, and image endpoints:
- Run: `python scripts/smoke_test_openai.py`
- If you want to test Images Edits, set `SMOKE_EDIT_IMAGE_PATH` to a real local PNG/JPG/WebP file.

### Frontend tests (Jest)
- Location: `frontend/tests`
- Uses jsdom + @testing-library/dom + @testing-library/user-event.
- `.nvmrc` enforces a consistent Node major version (run `nvm use`).

#### Quick start
```bash
# Ensure correct Node version
nvm use

# Install dependencies (first time or after updates)


# Run only frontend tests (serial to reduce flake)
## Storage paths

# Watch mode for development
npm run test:frontend:watch

# Backend tests (pytest) via npm convenience script
npm run test:backend

# Run all (frontend then backend)
- Images are stored under DATA_DIR/images/user_{id}/story_{id}/...
```

#### Node version management
- The file `.nvmrc` (currently `22`) specifies the expected Node major.
- Add to your shell profile to auto-switch:
    ```bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    cd /path/to/repo && nvm use
    ```
- Optional: `nvm alias default $(cat .nvmrc)` to make it the default.

#### Troubleshooting
| Symptom | Fix |
|---------|-----|
| `command not found: jest` | Run `nvm use && npm install` |
| Version mismatch / unexpected crashes | Confirm `node -v` matches `.nvmrc`; reinstall deps after switching versions |
| Hanging tests | Use `--runInBand` (already in `test:frontend`) |
| Flaky DOM timing | Keep serial execution; add explicit `await waitFor(...)` in tests |
| Stale node_modules after Node upgrade | `rm -rf node_modules package-lock.json && npm install` |

#### If Node / npm are missing
Use the portable bootstrap (downloads a local Node under `.node-runtime/`):

```bash
bash scripts/bootstrap-node.sh
eval "$(bash scripts/bootstrap-node.sh env)"
npm install
npm test
```

The `pretest` script automatically calls the bootstrap, so a simple `npm test` will attempt to provision Node if absent.

After the first bootstrap you can also:
```bash
source ./activate-node.sh   # Adds portable Node to PATH for this shell
```

Shortcut (single command):

```bash
bash scripts/run-frontend-tests.sh
```

#### Portable runtime details & best practices
The script `scripts/bootstrap-node.sh` supports two modes:
- Normal: attempts to use existing Node (system or nvm) that satisfies `engines.node`.
- Portable: forced when you set `PORTABLE_INSTALL=1`, downloading a tarball into `.node-runtime/`.

Common workflows
```bash
# Force a specific full version (skips network index lookup):
NODE_VERSION=22.10.0 PORTABLE_INSTALL=1 bash scripts/bootstrap-node.sh

# Add portable Node to current shell (idempotent):
source ./activate-node.sh

# Run tests (bootstrap runs again but is a fast no-op once version resolved)
npm test
```

Skip index.json fetch
- If you pass a full semver in `NODE_VERSION` (e.g. `22.10.0`) the bootstrap script no longer attempts to fetch `index.json` to resolve the latest patch.
- Using only a major (e.g. `.nvmrc` = `22`) triggers a (fast) lookup unless offline; on network failure it falls back to `22.0.0`.

Recommended `pretest` hard‑pin (optional improvement)
- To avoid any network during CI/local pretest you can change the `pretest` script to:
    ```json
    "pretest": "NODE_VERSION=22.10.0 bash scripts/bootstrap-node.sh"
    ```
- This is intentionally not committed yet to keep the repo flexible while patch cadence is high; update when you want to lock the patch version.

Manual fallback (air‑gapped / repeated network failures)
```bash
mkdir -p .node-runtime && cd .node-runtime
curl -fSLO https://nodejs.org/dist/v22.10.0/node-v22.10.0-darwin-arm64.tar.gz
tar -xzf node-v22.10.0-darwin-arm64.tar.gz
cd ..
cat > activate-node.sh <<'EOF'
#!/usr/bin/env bash
export PATH="$(pwd)/.node-runtime/node-v22.10.0-darwin-arm64/bin:$PATH"
EOF
chmod +x activate-node.sh
source ./activate-node.sh
node -v && npm -v
```

Suppress expected console noise in tests (optional)
- The frontend tests purposefully mount only minimal HTML, so warnings like missing dropdowns/buttons are expected and do not fail the suite.
- To silence them you can add a filter in `frontend/tests/setup-tests.mjs`:
    ```js
    const noisy = [/Select element with ID/, /not found; .* will not work/, /CRITICAL ERROR:/];
    const origError = console.error;
    console.error = (...args) => {
        if (noisy.some(r => r.test(args[0]))) return; // swallow expected noise
        origError(...args);
    };
    ```
- Keep at least one path (e.g. real exceptions) visible to avoid hiding regressions.

#### CI artifacts
`npm run test:frontend:ci` generates:
- JUnit XML: `frontend/test-results/junit.xml`
- Coverage: `frontend/coverage/`

GitHub Actions uploads these for PR visibility.

#### CI
- If adding a workflow, ensure it runs `nvm install` / `nvm use` or uses `actions/setup-node` with the version in `.nvmrc`.
- Cache `~/.npm` based on `package-lock.json` hash.
- Character references under .../references
- Filenames are sanitized and include short IDs for uniqueness.
- Paths saved to DB are always relative to DATA_DIR, so they can be served at /static_content/...

## Characters import (JSON)
You can bulk add or update characters from a JSON file via the Characters page in the frontend.

Where to start
- Open the app and navigate to Characters.
- Click "Import from JSON" and select a file.
- The importer accepts either a single object or an array of objects.

Sample file
- See frontend/samples/characters_import.sample.json for a ready-to-use example.

Accepted fields per character
- name (required): string. Used for per-user, case-insensitive deduping/upserts.
- description: string. If missing, physical_appearance is used when present.
- age: number or string (will be parsed to int when possible).
- gender: string.
- clothing_style: string.
- key_traits: string. If missing, traits is used when present.
- image_style: string. Should match one of the dynamic list values under "image_styles".
- generate_image: boolean (default false). When true, triggers image generation for the character.

Behavior
- Import performs an upsert by name (case-insensitive) for the current user; existing characters are updated.
- Items without a name are skipped.
- After import, the list refreshes and a snackbar shows counts of saved vs failed items.

Related API
- POST /api/v1/characters/ with the fields above. The backend applies the same name-based dedupe per user.

## Frontend overview
- Wizard flow with steps: Basics → Characters → Options → Review
- Characters library: search, pagination, edit/duplicate, regenerate image
- Inline status messages in modals to avoid hidden snackbars
- Sticky glass header, themed buttons, animated progress bar (respects reduced motion)

## Screenshots

![Wizard](docs/screenshots/wizard.svg)

![Characters](docs/screenshots/characters.svg)

![Progress](docs/screenshots/progress.svg)

How to update these
- Replace the files under `docs/screenshots/` with real screenshots (keep the same filenames).
- Recommended captures:
    - Wizard: step indicators + form + Character Library panel.
    - Characters: grid + open modal with inline status.
    - Progress: generation progress area visible during polling.

## How to run the frontend via backend static mounts

The backend can serve the frontend directly using static mounts.

Quick start
1) Create and activate a venv, then install deps.
2) Copy `.env.example` to `.env` in repo root and set required values.
3) Ensure static mounts are enabled (default in dev) or export flags.
4) Start the API server and open the served frontend.

Example

```bash
# from repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Root .env is preferred. Enable static mounts if needed.
export RUN_ENV=dev MOUNT_FRONTEND_STATIC=1 MOUNT_DATA_STATIC=1

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Visit
- Frontend: http://127.0.0.1:8000/static/index.html
- User data (images): http://127.0.0.1:8000/static_content/

Notes
- In dev, static mounts are on by default; in tests they’re off unless explicitly enabled.
- Image paths in the DB are relative to `DATA_DIR` and resolve under `/static_content/` when mounted.

## Troubleshooting 401s (OpenAI)

If you see 401 responses when generating content:
- Single source of truth: ensure OPENAI_API_KEY is set in the root `.env` (not `backend/.env`).
- Restart the server after changing `.env` so settings reload.
- Verify via admin diagnostics: GET `/api/v1/admin/monitoring/config` (admin auth) — it shows whether a key is present (masked).
- Confirm no stray environment variables override the key; root `.env` loads first, then shell env, then any backend fallback.
- In CI/tests, a dummy key is fine; calls are mocked. For local real calls, use a valid key and ensure your network doesn’t block API access.

## Admin diagnostics
- Endpoint: GET /api/v1/admin/monitoring/config (admin only)
- Purpose: Verify configuration quickly without exposing secrets
    - Shows whether OPENAI_API_KEY is present (masked prefix only)
    - Displays selected models, mounts, and directories
    - Indicates if the OpenAI client is initialized
    - Useful for resolving 401/ENV issues (see CONFIG.md)

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
- .devcontainer/ (VS Code Dev Container configuration for reproducible Python + Node environment)

## Dev Container (Reproducible Environment)
You can develop inside a container with consistent Python (3.13) and Node (22) versions without installing them locally.

Prereqs
- VS Code + Dev Containers extension (or GitHub Codespaces)

Usage
1. Open the repository in VS Code.
2. Run: Command Palette → Dev Containers: Reopen in Container.
3. On first build it will:
    - Build the base image (Ubuntu + Python 3.13 + Node 22.10.0)
    - Create a `.venv` virtual environment
    - Install backend requirements and npm dependencies
4. Once the container is ready:
    - Run backend: `uvicorn backend.main:app --reload --host 0.0.0.0` (port 8000 is forwarded)
    - Run tests: `pytest -q` or `npm test`

Notes
- Adjust pinned Node version by editing `ARG NODE_VERSION` in `.devcontainer/Dockerfile`.
- If you change dependencies, re-run `postCreateCommand` tasks manually or rebuild the container.
- The portable bootstrap script still works inside the container; normally not needed since Node is system-installed there.


## CI with GitHub Actions
You can run tests on every push or pull request using GitHub Actions.

Key points
- Python 3.13 runtime
- Install backend requirements only
- Use RUN_ENV=test and enable MOUNT_DATA_STATIC so static routes work in tests
- OpenAI calls are mocked in tests. A harmless dummy OPENAI_API_KEY is set to avoid import‑time checks.
- Async tests: pytest‑asyncio is included so async tests run under pytest.

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
                    OPENAI_API_KEY: 'dummy-ci-key'
                    # Optional: set DATA_DIR to a workspace path if desired
                    # DATA_DIR: data
                run: |
                    pytest -q
```

Notes
- If you later add linting or type checks, append steps before running tests.
- If you add integration tests requiring external services, gate those with a label or separate job.

