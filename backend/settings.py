import json
import os
from typing import Any, Dict, List
from pathlib import Path
from dotenv import load_dotenv

OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
ADMIN_CONFIG_OVERRIDE_FILENAME = "admin_config_overrides.json"
ADMIN_CONFIG_EDITABLE_FIELDS = (
    "openai_text_provider",
    "openai_text_base_url",
    "openai_image_provider",
    "openai_image_base_url",
    "text_model",
    "image_model",
    "enable_image_generation",
    "use_openai_responses_api",
    "openai_text_enable_fallback",
    "enable_image_style_mapping",
)

# Ensure environment is populated from the repo root .env before creating settings.
_here = Path(__file__).resolve().parent
_root_env = _here.parent / ".env"
# Load root .env if present (do not override already-set env vars)
if _root_env.exists():
    load_dotenv(dotenv_path=str(_root_env), override=False)
else:
    # Fallback: attempt default search from CWD/parents
    load_dotenv()


def _parse_bool_env(value: str | None, default: bool = False) -> bool:
    """Parse a boolean environment flag with a fallback default."""

    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


def _resolve_repo_path(repo_root: Path, path_value: str) -> str:
    """Resolve a path relative to the repository root when needed."""

    if not path_value:
        return str(repo_root)
    path = Path(path_value)
    return str(path if path.is_absolute() else (repo_root / path).resolve())


def _resolve_admin_config_override_path(
    repo_root: Path,
    private_data_dir: str,
) -> str:
    """Return the file path used for persisted admin-safe config overrides."""

    override_path = os.getenv("ADMIN_CONFIG_OVERRIDE_FILE")
    if override_path:
        return _resolve_repo_path(repo_root, override_path)
    return str(Path(private_data_dir) / ADMIN_CONFIG_OVERRIDE_FILENAME)


def load_admin_config_overrides(path: str | None = None) -> Dict[str, Any]:
    """Load persisted admin-safe config overrides from disk."""

    repo_root = _here.parent
    target_path = path or _resolve_admin_config_override_path(
        repo_root,
        _resolve_repo_path(repo_root, os.getenv(
            "PRIVATE_DATA_DIR", "private_data")),
    )
    if not os.path.exists(target_path):
        return {}

    try:
        with open(target_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    return {
        key: value
        for key, value in payload.items()
        if key in ADMIN_CONFIG_EDITABLE_FIELDS
    }


def save_admin_config_overrides(
    values: Dict[str, Any],
    path: str | None = None,
) -> Dict[str, Any]:
    """Persist validated admin-safe config overrides to disk."""

    repo_root = _here.parent
    target_path = path or _resolve_admin_config_override_path(
        repo_root,
        _resolve_repo_path(repo_root, os.getenv(
            "PRIVATE_DATA_DIR", "private_data")),
    )
    overrides = load_admin_config_overrides(target_path)

    for key, value in values.items():
        if key not in ADMIN_CONFIG_EDITABLE_FIELDS:
            raise ValueError(f"Unsupported admin config field: {key}")

        if value is None:
            overrides.pop(key, None)
        else:
            overrides[key] = value

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    if overrides:
        with open(target_path, "w", encoding="utf-8") as handle:
            json.dump(overrides, handle, indent=2, sort_keys=True)
            handle.write("\n")
    elif os.path.exists(target_path):
        os.remove(target_path)

    return overrides


def reset_settings_cache() -> None:
    """Reset the cached settings singleton."""

    global _settings_instance
    _settings_instance = None


def _normalize_openai_base_url(value: str | None) -> str:
    """Return a normalized OpenAI-compatible base URL.

    Production behavior remains unchanged when no override is supplied.
    """

    raw_value = str(value or "").strip()
    if not raw_value:
        return OPENAI_DEFAULT_BASE_URL
    return raw_value.rstrip("/")


def _default_openai_provider(base_url: str) -> str:
    """Return a safe provider label derived from the active base URL."""

    if base_url.rstrip("/") == OPENAI_DEFAULT_BASE_URL:
        return "openai"
    return "openai-compatible"


class BaseSettings:
    """
    Lightweight settings loader. Reads from environment with sensible defaults.
    Avoids extra dependencies while providing a single source of truth for config.
    """

    def __init__(self):
        repo_root = _here.parent

        # Environment & paths
        self.run_env: str = os.getenv("RUN_ENV", "dev")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api/v1")

        # Static directories to mount
        self.frontend_static_dir: str = _resolve_repo_path(
            repo_root,
            os.getenv("FRONTEND_DIR", "frontend")
        )
        self.data_dir: str = _resolve_repo_path(
            repo_root,
            os.getenv("DATA_DIR", "data"),
        )

        # Private storage (never mounted publicly). Use for user uploads that must
        # not be publicly accessible.
        self.private_data_dir: str = _resolve_repo_path(
            repo_root,
            os.getenv("PRIVATE_DATA_DIR", "private_data")
        )
        self.admin_config_override_path: str = _resolve_admin_config_override_path(
            repo_root,
            self.private_data_dir,
        )
        self.admin_config_override_relative_path: str = os.path.relpath(
            self.admin_config_override_path,
            repo_root,
        )
        admin_overrides = load_admin_config_overrides(
            self.admin_config_override_path,
        )
        self.admin_config_overrides: Dict[str, Any] = dict(admin_overrides)
        self.config_overrides_applied: List[str] = sorted(
            admin_overrides.keys())

        # Upload limits
        self.max_upload_bytes: int = int(
            os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
        self.trial_access_days: int = int(
            os.getenv("TRIAL_ACCESS_DAYS", "7")
        )
        self.trial_story_credits: int = int(
            os.getenv("TRIAL_STORY_CREDITS", "3")
        )
        self.trial_image_credits: int = int(
            os.getenv("TRIAL_IMAGE_CREDITS", "10")
        )
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
        self.logs_dir: str = _resolve_repo_path(
            repo_root,
            logs_dir_env,
        ) if logs_dir_env else os.path.join(
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
        shared_openai_base_url = _normalize_openai_base_url(
            os.getenv("OPENAI_BASE_URL")
        )
        self.openai_text_base_url: str = _normalize_openai_base_url(
            admin_overrides.get("openai_text_base_url")
            or os.getenv("OPENAI_TEXT_BASE_URL")
            or shared_openai_base_url
        )
        self.openai_image_base_url: str = _normalize_openai_base_url(
            admin_overrides.get("openai_image_base_url")
            or os.getenv("OPENAI_IMAGE_BASE_URL")
            or shared_openai_base_url
        )
        self.openai_text_provider: str = (
            admin_overrides.get("openai_text_provider")
            or os.getenv("OPENAI_TEXT_PROVIDER")
            or _default_openai_provider(self.openai_text_base_url)
        )
        self.openai_image_provider: str = (
            admin_overrides.get("openai_image_provider")
            or os.getenv("OPENAI_IMAGE_PROVIDER")
            or _default_openai_provider(self.openai_image_base_url)
        )
        self.text_model: str = str(
            admin_overrides.get("text_model")
            or os.getenv("TEXT_MODEL", "gpt-5.4-mini")
        )
        self.image_model: str = str(
            admin_overrides.get("image_model")
            or os.getenv("IMAGE_MODEL", "gpt-image-2")
        )
        if "enable_image_generation" in admin_overrides:
            self.enable_image_generation = bool(
                admin_overrides["enable_image_generation"]
            )
        else:
            self.enable_image_generation = _parse_bool_env(
                os.getenv("ENABLE_IMAGE_GENERATION"),
                default=True,
            )

        # Retry / backoff
        self.retry_max_attempts: int = int(
            os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        self.retry_backoff_base: float = float(
            os.getenv("RETRY_BACKOFF_BASE", "1.5"))

        # Feature flags
        # When enabled, story text generation uses the OpenAI Responses API.
        # Default is disabled for incremental migration.
        if "use_openai_responses_api" in admin_overrides:
            self.use_openai_responses_api = bool(
                admin_overrides["use_openai_responses_api"]
            )
        else:
            self.use_openai_responses_api = _parse_bool_env(
                os.getenv("USE_OPENAI_RESPONSES_API")
            )

        # Optional resilience: when enabled, fall back to the other text path
        # (Responses <-> Chat Completions) if the primary path errors.
        if "openai_text_enable_fallback" in admin_overrides:
            self.openai_text_enable_fallback = bool(
                admin_overrides["openai_text_enable_fallback"]
            )
        else:
            self.openai_text_enable_fallback = _parse_bool_env(
                os.getenv("OPENAI_TEXT_ENABLE_FALLBACK")
            )

        if "enable_image_style_mapping" in admin_overrides:
            self.enable_image_style_mapping = bool(
                admin_overrides["enable_image_style_mapping"]
            )
        else:
            self.enable_image_style_mapping = _parse_bool_env(
                os.getenv("ENABLE_IMAGE_STYLE_MAPPING")
            )

        self.enable_telemetry: bool = _parse_bool_env(
            os.getenv("ENABLE_TELEMETRY")
        )

        # Authentication rate limiting
        self.login_rate_limit: str = os.getenv(
            "LOGIN_RATE_LIMIT",
            "10/minute",
        )
        self.signup_rate_limit: str = os.getenv(
            "SIGNUP_RATE_LIMIT",
            "5/hour",
        )
        self.password_reset_request_rate_limit: str = os.getenv(
            "PASSWORD_RESET_REQUEST_RATE_LIMIT",
            self.login_rate_limit,
        )
        self.password_reset_confirm_rate_limit: str = os.getenv(
            "PASSWORD_RESET_CONFIRM_RATE_LIMIT",
            "10/hour",
        )

        # Auth cookies and browser-session security defaults
        self.auth_cookie_name: str = os.getenv(
            "AUTH_COOKIE_NAME",
            "story_generator_auth",
        )
        self.auth_cookie_secure: bool = _parse_bool_env(
            os.getenv("AUTH_COOKIE_SECURE"),
            default=self.run_env == "prod",
        )
        self.auth_cookie_samesite: str = os.getenv(
            "AUTH_COOKIE_SAMESITE",
            "lax",
        ).strip().lower() or "lax"
        self.expose_password_reset_token_preview: bool = _parse_bool_env(
            os.getenv("EXPOSE_PASSWORD_RESET_TOKEN_PREVIEW"),
            default=False,
        )


_settings_instance: BaseSettings | None = None


def get_settings() -> BaseSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = BaseSettings()
    return _settings_instance
