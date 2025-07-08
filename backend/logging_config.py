import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import glob
from typing import Dict, Any


class NoB64JsonFilter(logging.Filter):
    """
    Custom logging filter to redact b64_json data from log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # The 'extra' dict is merged into the record's __dict__.
        if 'b64_json' in record.__dict__:
            # To be safe, we create a copy of the args if it's a tuple
            # and then modify the record's __dict__
            record.b64_json = '<b64_json_data_redacted>'
        return True


class DailyCounterRotatingFileHandler(logging.FileHandler):
    """
    Custom log handler that creates a new log file for each day,
    with an incrementing counter. Filename format: name_YYYY_MM_DD_CCC_UTC.log
    """

    def __init__(self, log_dir, name_prefix, mode='a', encoding='utf-8'):
        self.log_dir = log_dir
        self.name_prefix = name_prefix
        # The filename is determined on the first emit, so we start with a placeholder.
        # This avoids creating an empty file if the logger is configured but not used.
        self.base_filename = os.path.join(
            log_dir, f"{name_prefix}_placeholder.log")
        self._is_initialized = False
        # Always use delay=True to defer file opening until the first emit call,
        # when we can determine the correct filename.
        super().__init__(self.base_filename, mode, encoding, delay=True)

    def _get_next_log_filename(self):
        """
        Calculates the next available log filename for the current UTC day.
        """
        today_utc_str = datetime.now(timezone.utc).strftime('%Y_%m_%d')
        pattern = os.path.join(
            self.log_dir, f"{self.name_prefix}_{today_utc_str}_*_UTC.log")
        existing_files = sorted(glob.glob(pattern))

        if not existing_files:
            next_counter = 1
        else:
            try:
                last_file = os.path.basename(existing_files[-1])
                # Extracts the counter part (e.g., '001')
                last_counter_str = last_file.split('_')[-2]
                next_counter = int(last_counter_str) + 1
            except (ValueError, IndexError):
                # Fallback if parsing fails
                next_counter = len(existing_files) + 1

        return os.path.join(
            self.log_dir,
            f"{self.name_prefix}_{today_utc_str}_{next_counter:03d}_UTC.log"
        )

    def _rollover(self):
        """Close the current stream and open the new one."""
        if self.stream:
            self.stream.close()
            self.stream = None
        self.base_filename = self._get_next_log_filename()
        # Explicitly open the stream for the new file.
        self.stream = self._open()

    def emit(self, record):
        """
        Emit a record. Handles rollover if the date has changed or the stream
        is not yet open.
        """
        try:
            # Determine if a rollover is needed before acquiring the lock.
            # A rollover is needed if the stream isn't open yet, or if the date has changed.
            if self.stream is None or self.should_rollover(record):
                self.do_rollover()

            # The original FileHandler's emit method handles the actual writing.
            super().emit(record)
        except Exception:
            self.handleError(record)

    def should_rollover(self, record):
        """
        Determine if rollover should occur.

        For this handler, rollover is based on the date.
        """
        today_utc_str = datetime.now(timezone.utc).strftime('%Y_%m_%d')
        # self.base_filename will be the placeholder on first call, so this check works.
        return today_utc_str not in os.path.basename(self.base_filename)

    def do_rollover(self):
        """
        Does a rollover, as described in __init__().
        """
        # This is a simplified version of the logic from the standard library's
        # RotatingFileHandler, adapted for our daily counter logic.
        if self.stream:
            self.stream.close()
            self.stream = None

        self.base_filename = self._get_next_log_filename()
        # The delay=True in __init__ means we have to explicitly open the stream.
        if self.encoding:
            self.stream = open(self.base_filename, self.mode,
                               encoding=self.encoding)
        else:
            self.stream = open(self.base_filename, self.mode)


# Ensure logs directory exists
# Should point to /data/logs
LOGS_DIR = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), 'data', 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# --- General Application Logger ---
app_logger = logging.getLogger("story_generator_app")
app_logger.setLevel(logging.INFO)
app_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# App log file handler
app_handler = DailyCounterRotatingFileHandler(LOGS_DIR, 'app')
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)


# --- API Logger (for OpenAI requests/responses) ---
api_logger = logging.getLogger("story_generator_api")
api_logger.setLevel(logging.DEBUG)  # More verbose for API calls
api_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
# API log file handler
api_handler = DailyCounterRotatingFileHandler(LOGS_DIR, 'api')
# Add the filter to the API handler
api_handler.addFilter(NoB64JsonFilter())
api_handler.setFormatter(api_formatter)
api_logger.addHandler(api_handler)


# --- Error Logger ---
error_logger = logging.getLogger("story_generator_error")
error_logger.setLevel(logging.ERROR)
error_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(funcName)s - line %(lineno)d - %(message)s')
# Error log file handler
error_handler = DailyCounterRotatingFileHandler(LOGS_DIR, 'error')
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)

# Example usage:
# from .logging_config import app_logger, api_logger, error_logger
# app_logger.info("User logged in.")
# api_logger.debug("Sent request to OpenAI.")
# error_logger.error("Failed to generate PDF.", exc_info=True) # exc_info=True to log stack trace
