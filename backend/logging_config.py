\
import logging
import os
from logging.handlers import RotatingFileHandler

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'logs') # Should point to /data/logs
os.makedirs(LOGS_DIR, exist_ok=True)

# --- General Application Logger ---
app_logger = logging.getLogger("story_generator_app")
app_logger.setLevel(logging.INFO)
app_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# App log file handler
app_log_file = os.path.join(LOGS_DIR, 'app.log')
app_handler = RotatingFileHandler(app_log_file, maxBytes=10*1024*1024, backupCount=5) # 10MB per file, 5 backups
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)
# Console handler for app logger (optional, good for development)
# app_console_handler = logging.StreamHandler()
# app_console_handler.setFormatter(app_formatter)
# app_logger.addHandler(app_console_handler)


# --- API Logger (for OpenAI requests/responses) ---
api_logger = logging.getLogger("story_generator_api")
api_logger.setLevel(logging.DEBUG) # More verbose for API calls
api_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')
# API log file handler
api_log_file = os.path.join(LOGS_DIR, 'api.log')
api_handler = RotatingFileHandler(api_log_file, maxBytes=5*1024*1024, backupCount=3) # 5MB per file, 3 backups
api_handler.setFormatter(api_formatter)
api_logger.addHandler(api_handler)
# Console handler for API logger (optional)
# api_console_handler = logging.StreamHandler()
# api_console_handler.setFormatter(api_formatter)
# api_logger.addHandler(api_console_handler)


# --- Error Logger ---
error_logger = logging.getLogger("story_generator_error")
error_logger.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(funcName)s - line %(lineno)d - %(message)s')
# Error log file handler
error_log_file = os.path.join(LOGS_DIR, 'error.log')
error_handler = RotatingFileHandler(error_log_file, maxBytes=5*1024*1024, backupCount=3)
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)
# Console handler for Error logger (optional)
# error_console_handler = logging.StreamHandler()
# error_console_handler.setFormatter(error_formatter)
# error_logger.addHandler(error_console_handler)

# Example usage:
# from .logging_config import app_logger, api_logger, error_logger
# app_logger.info("User logged in.")
# api_logger.debug("Sent request to OpenAI.")
# error_logger.error("Failed to generate PDF.", exc_info=True) # exc_info=True to log stack trace
