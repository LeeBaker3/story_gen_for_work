import os
from typing import List


class BaseSettings:
    """
    Lightweight settings loader. Reads from environment with sensible defaults.
    Avoids extra dependencies while providing a single source of truth for config.
    """

    def __init__(self):
        # Environment & paths
        self.run_env: str = os.getenv("RUN_ENV", "dev")
        self.api_prefix: str = os.getenv("API_PREFIX", "/api/v1")

        # Static directories to mount
        self.frontend_static_dir: str = os.getenv("FRONTEND_DIR", "frontend")
        self.data_dir: str = os.getenv("DATA_DIR", "data")
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
        self.logs_dir: str = os.getenv(
            "LOGS_DIR", os.path.join(self.data_dir, "logs"))
        self.logging_config_file: str = os.getenv(
            "LOGGING_CONFIG", os.path.join("config", "logging.yaml"))

        # CORS
        origins = os.getenv("CORS_ORIGINS", "")
        self.cors_origins: List[str] = [o.strip()
                                        for o in origins.split(",") if o.strip()]

        # OpenAI / models
        self.openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
        self.text_model: str = os.getenv("TEXT_MODEL", "gpt-4.1-mini")
        self.image_model: str = os.getenv("IMAGE_MODEL", "gpt-image-1")

        # Retry / backoff
        self.retry_max_attempts: int = int(
            os.getenv("RETRY_MAX_ATTEMPTS", "3"))
        self.retry_backoff_base: float = float(
            os.getenv("RETRY_BACKOFF_BASE", "1.5"))

        # Feature flags
        self.enable_image_style_mapping: bool = os.getenv(
            "ENABLE_IMAGE_STYLE_MAPPING", "").lower() in ("1", "true", "yes")


_settings_instance: BaseSettings | None = None


def get_settings() -> BaseSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = BaseSettings()
    return _settings_instance
