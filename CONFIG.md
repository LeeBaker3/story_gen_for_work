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

## Environment variables

Core
- RUN_ENV: dev | test | prod (default: dev)
  - test disables static mounts by default. Override via MOUNT_* flags if needed.
- API_PREFIX: API base path (default: /api/v1)
- SECRET_KEY: JWT signing key (required in prod)

Static & storage
- FRONTEND_DIR: directory to serve at /static (default: frontend)
- DATA_DIR: base directory for generated data (default: data)
- MOUNT_FRONTEND_STATIC: "1"/"true" to mount /static (default: true unless RUN_ENV=test)
- MOUNT_DATA_STATIC: "1"/"true" to mount /static_content (default: true unless RUN_ENV=test)

Logging
- LOGS_DIR: directory for logs (default: DATA_DIR/logs)
- LOGGING_CONFIG: path to logging YAML (default: config/logging.yaml)

OpenAI models and retries
- OPENAI_API_KEY: API key for OpenAI
- TEXT_MODEL: LLM for story text (default: gpt-4.1-mini)
- IMAGE_MODEL: image model (default: gpt-image-1)
- RETRY_MAX_ATTEMPTS: API retry attempts (default: 3)
- RETRY_BACKOFF_BASE: exponential backoff base seconds (default: 1.5)
- ENABLE_IMAGE_STYLE_MAPPING: "1"/"true" to map friendly style names to richer prompts (default: false)

CORS
- CORS_ORIGINS: comma-separated list of allowed origins (optional)

Database
- DATABASE_URL: SQLAlchemy URL (default: sqlite:///./story_generator.db)

## Notes & safe defaults

- The backend prefers the repository root .env. If backend/.env also exists, it is only used to fill missing values (never overriding root or shell env).
- Paths saved in the database are relative to DATA_DIR, so they are served under /static_content/ consistently.
- For CI, use OPENAI_API_KEY=dummy-ci-key and mock OpenAI calls in tests (already done in the test suite).

## Migration notes

Previously, some instructions referenced backend/.env. The application now standardizes on a single root-level .env. If you still have backend/.env, move its content to the root .env and delete the backend file to avoid confusion.
