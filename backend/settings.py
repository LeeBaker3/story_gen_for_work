import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is populated from the repo root .env before creating settings.
_here = Path(__file__).resolve().parent
_root_env = _here.parent / ".env"
# Load root .env if present (do not override already-set env vars)
if _root_env.exists():
    load_dotenv(dotenv_path=str(_root_env), override=False)
else:
    # Fallback: attempt default search from CWD/parents
    load_dotenv()


class BaseSettings:
    """
    Lightweight settings loader. Reads from environment with sensible defaults.
    Avoids extra dependencies while providing a single source of truth for config.
    """

    def __init__(self):
        repo_root = _here.parent

        def _resolve_dir(path_value: str) -> str:
            """Resolve a directory path to an absolute path.

            If the provided value is relative, it is resolved relative to the
            repository root (the folder containing `.env`).
            """
            if not path_value:
                return str(repo_root)
            p = Path(path_value)
            return str(p if p.is_absolute() else (repo_root / p).resolve())

        # Environment & paths
        self.run_env: str = os.getenv("RUN_ENV", "dev")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api/v1")

        # Static directories to mount
        self.frontend_static_dir: str = _resolve_dir(
            os.getenv("FRONTEND_DIR", "frontend")
        )
        self.data_dir: str = _resolve_dir(os.getenv("DATA_DIR", "data"))

        # Private storage (never mounted publicly). Use for user uploads that must
        # not be publicly accessible.
        self.private_data_dir: str = _resolve_dir(
            os.getenv("PRIVATE_DATA_DIR", "private_data")
        )

        # Upload limits
        self.max_upload_bytes: int = int(
            os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
        # Whether to mount static in this environment
        self.mount_frontend_static: bool = os.getenv(
            "MOUNT_FRONTEND_STATIC", "").lower() in ("1", "true", "yes")
        self.mount_data_static: bool = os.getenv(
            "MOUNT_DATA_STATIC", "").lower() in ("1", "true", "yes")
        # Default behavior: mount unless RUN_ENV == test
        if os.getenv("MOUNT_FRONTEND_STATIC") is None:
            self.mount_frontend_static = self.run_env != "test"
        if os.getenv("MOUNT_DATA_STATIC") is None:
            self.mount_data_static = self.run_env != "test"

        # Logging
        logs_dir_env = os.getenv("LOGS_DIR")
        self.logs_dir: str = _resolve_dir(logs_dir_env) if logs_dir_env else os.path.join(
            self.data_dir, "logs"
        )
        self.logging_config_file: str = os.getenv(
            "LOGGING_CONFIG", os.path.join("config", "logging.yaml"))

        # CORS
        origins = os.getenv("CORS_ORIGINS", "")
        self.cors_origins: List[str] = [o.strip()
                                        for o in origins.split(",") if o.strip()]

        # OpenAI / models
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.text_model: str = os.getenv("TEXT_MODEL", "gpt-5-mini")
        self.image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-1.5")

        # Retry / backoff
        self.retry_max_attempts: int = int(
            os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        self.retry_backoff_base: float = float(
            os.getenv("RETRY_BACKOFF_BASE", "1.5"))

        # Feature flags
        # When enabled, story text generation uses the OpenAI Responses API.
        # Default is disabled for incremental migration.
        self.use_openai_responses_api: bool = os.getenv(
            "USE_OPENAI_RESPONSES_API", ""
        ).lower() in ("1", "true", "yes")

        # Optional resilience: when enabled, fall back to the other text path
        # (Responses <-> Chat Completions) if the primary path errors.
        self.openai_text_enable_fallback: bool = os.getenv(
            "OPENAI_TEXT_ENABLE_FALLBACK", ""
        ).lower() in ("1", "true", "yes")

        self.enable_image_style_mapping: bool = os.getenv(
            "ENABLE_IMAGE_STYLE_MAPPING", "").lower() in ("1", "true", "yes")


_settings_instance: BaseSettings | None = None


def get_settings() -> BaseSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = BaseSettings()
    return _settings_instance
