import logging
import os
from logging.config import dictConfig
from typing import Optional
from datetime import datetime, timezone
import glob
import yaml


class NoB64JsonFilter(logging.Filter):
    """Redacts base64 payloads from 'b64_json' extra field."""

    def filter(self, record: logging.LogRecord) -> bool:
        if 'b64_json' in record.__dict__:
            record.b64_json = '<b64_json_data_redacted>'
        return True


class DailyCounterRotatingFileHandler(logging.FileHandler):
    """
    Backward-compatibility handler used by tests.
    Creates log files named: {name_prefix}_YYYY_MM_DD_CCC_UTC.log in the given directory.
    """

    def __init__(self, log_dir: str, name_prefix: str, mode: str = 'a', encoding: str = 'utf-8'):
        self.log_dir = log_dir
        self.name_prefix = name_prefix
        # Start with a placeholder; open on first emit
        self.base_filename = os.path.join(
            log_dir, f"{name_prefix}_placeholder.log")
        super().__init__(self.base_filename, mode, encoding, delay=True)

    def _next_filename(self) -> str:
        today = datetime.now(timezone.utc).strftime('%Y_%m_%d')
        pattern = os.path.join(
            self.log_dir, f"{self.name_prefix}_{today}_*_UTC.log")
        existing = sorted(glob.glob(pattern))
        if not existing:
            counter = 1
        else:
            try:
                last = os.path.basename(existing[-1])
                counter = int(last.split('_')[-2]) + 1
            except Exception:
                counter = len(existing) + 1
        return os.path.join(self.log_dir, f"{self.name_prefix}_{today}_{counter:03d}_UTC.log")

    def should_rollover(self, record) -> bool:
        today = datetime.now(timezone.utc).strftime('%Y_%m_%d')
        return today not in os.path.basename(self.base_filename)

    def do_rollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        self.base_filename = self._next_filename()
        if self.encoding:
            self.stream = open(self.base_filename, self.mode,
                               encoding=self.encoding)
        else:
            self.stream = open(self.base_filename, self.mode)

    def emit(self, record):
        try:
            if self.stream is None or self.should_rollover(record):
                self.do_rollover()
            super().emit(record)
        except Exception:
            self.handleError(record)


def _load_logging_config(path: Optional[str] = None):
    """Load logging config from YAML and apply via dictConfig."""
    # Prefer BaseSettings values if available; otherwise fall back to env/defaults
    settings_config_path = None
    settings_logs_dir = None
    try:
        # local import to avoid early import cycles
        from backend.settings import get_settings
        _settings = get_settings()
        settings_config_path = getattr(_settings, 'logging_config_file', None)
        settings_logs_dir = getattr(_settings, 'logs_dir', None)
    except Exception:
        pass

    config_path = path or settings_config_path or os.getenv(
        "LOGGING_CONFIG", os.path.join(os.path.dirname(
            os.path.dirname(__file__)), "config", "logging.yaml")
    )
    # Ensure logs dir exists
    logs_dir = settings_logs_dir or os.getenv("LOGS_DIR", os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'data', 'logs'))
    os.makedirs(logs_dir, exist_ok=True)

    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)

    # Replace string-based filter callable with actual class to avoid import-time circulars
    try:
        if 'filters' in cfg and 'redact_b64' in cfg['filters']:
            filt = cfg['filters']['redact_b64'] or {}
            # If YAML specified string path, replace with direct callable
            if isinstance(filt, dict):
                filt['()'] = NoB64JsonFilter
                cfg['filters']['redact_b64'] = filt
    except Exception:
        # Non-fatal; if this fails dictConfig may still work without the filter
        pass

    # If settings provided a logs_dir, rewrite handler filenames to land under that dir
    try:
        if settings_logs_dir and 'handlers' in cfg:
            for key in ('app_file', 'api_file', 'error_file'):
                h = cfg['handlers'].get(key)
                if h and 'filename' in h:
                    base = os.path.basename(h['filename'])
                    h['filename'] = os.path.join(logs_dir, base)
    except Exception:
        # Do not fail if structure differs
        pass

    # Allow simple env overrides for levels and retention without editing YAML
    # e.g., APP_LOG_LEVEL, API_LOG_LEVEL, ERROR_LOG_LEVEL
    def override_level(logger_key: str, env_key: str):
        val = os.getenv(env_key)
        if val and 'loggers' in cfg and logger_key in cfg['loggers']:
            cfg['loggers'][logger_key]['level'] = val.upper()

    override_level('story_generator_app', 'APP_LOG_LEVEL')
    override_level('story_generator_api', 'API_LOG_LEVEL')
    override_level('story_generator_error', 'ERROR_LOG_LEVEL')

    dictConfig(cfg)


# Initialize logging on import
try:
    _load_logging_config()
except Exception as e:
    # Fallback minimal console logger in case config load fails
    logging.basicConfig(level=logging.INFO)
    logging.getLogger(__name__).warning(
        f"Failed to load logging config: {e}. Using basicConfig().")


# Expose named loggers for importers expecting them
app_logger = logging.getLogger("story_generator_app")
api_logger = logging.getLogger("story_generator_api")
error_logger = logging.getLogger("story_generator_error")


def reload_logging_config(path: Optional[str] = None):
    """Re-apply logging configuration (e.g., after changing env vars or file)."""
    _load_logging_config(path)
