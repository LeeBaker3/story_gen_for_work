"""
This module provides monitoring endpoints for the application.

It includes routes for listing and retrieving log files, which are
accessible only to authenticated admin users.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
import os
from fastapi.responses import PlainTextResponse, FileResponse, Response
from typing import List, Optional
import sys
import platform
import shutil
import time
from datetime import datetime, timezone

from backend.auth import get_current_admin_user
from backend.logging_config import app_logger, error_logger
from backend.settings import get_settings
from backend import ai_services
from backend.metrics import APP_LOG_FILES_TOTAL

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

_settings = get_settings()
LOG_DIRECTORY = _settings.logs_dir or "data/logs"

monitoring_router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_admin_user)]
)

# Record process start time for uptime calculation
PROCESS_START_TIME = time.time()


@monitoring_router.get("/logs/", response_model=List[str])
def list_log_files():
    """
    Lists all available log files from the log directory.

    This endpoint scans the predefined log directory, filters for files
    ending with '.log', and returns them sorted by modification time
    in descending order (newest first).

    Returns:
        List[str]: A list of log file names.

    Raises:
        HTTPException: 500 error if the log directory is not found or
                       if there's an error reading the directory.
    """
    if not os.path.isdir(LOG_DIRECTORY):
        error_logger.error(f"Log directory not found: {LOG_DIRECTORY}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log directory configured incorrectly."
        )
    try:
        # Collect files matching current and legacy rotation patterns
        all_entries = os.listdir(LOG_DIRECTORY)
        files = []
        for f in all_entries:
            # Include primary .log files and new rotated (name.YYYY-MM-DD.log)
            if f.endswith('.log'):
                files.append(f)
                continue
            # Include legacy rotated files like 'name.log.YYYY-MM-DD'
            if '.log.' in f:
                files.append(f)
        # Sort by modification time, newest first
        files.sort(key=lambda f: os.path.getmtime(
            os.path.join(LOG_DIRECTORY, f)), reverse=True)
        return files
    except Exception as e:
        error_logger.exception("Failed to list log files.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve log files."
        )


@monitoring_router.get("/logs/{log_file}", response_class=PlainTextResponse)
def get_log_file(log_file: str, lines: Optional[int] = Query(default=1000, ge=10, le=5000)):
    """
    Retrieves the content of a specific log file.

    To prevent directory traversal attacks, it validates that the requested
    file is within the configured log directory. It returns the last 1000
    lines of the specified log file.

    Args:
        log_file (str): The name of the log file to retrieve.

    Returns:
        PlainTextResponse: The last 1000 lines of the log file content.

    Raises:
        HTTPException: 400 for an invalid path, 404 if the file is not found,
                       or 500 for read errors.
    """
    # Securely construct the full path to the log file
    log_file_path = os.path.abspath(os.path.join(LOG_DIRECTORY, log_file))

    # Security check to prevent path traversal attacks.
    # Ensures the resolved path is still within the intended directory.
    if not log_file_path.startswith(os.path.abspath(LOG_DIRECTORY)):
        raise HTTPException(status_code=400, detail="Invalid log file path.")

    if not os.path.exists(log_file_path) or not os.path.isfile(log_file_path):
        raise HTTPException(status_code=404, detail="Log file not found.")

    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            content_lines = f.readlines()
            # For performance and readability, return only the tail of the log.
            tail_len = 1000 if lines is None else int(lines)
            return "".join(content_lines[-tail_len:])
    except Exception as e:
        error_logger.exception(f"Failed to read log file: {log_file}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read log file: {log_file}"
        )


@monitoring_router.get("/metrics", response_class=PlainTextResponse)
def metrics_stub():
    """Expose Prometheus metrics.

    This endpoint is admin-authenticated because this router is mounted under
    the admin prefix.
    """
    try:
        count = 0
        if os.path.isdir(LOG_DIRECTORY):
            count = len([f for f in os.listdir(
                LOG_DIRECTORY) if f.endswith(".log")])
        APP_LOG_FILES_TOTAL.set(count)
    except Exception:
        # Never fail metrics endpoint; return metrics with best-effort values.
        APP_LOG_FILES_TOTAL.set(0)

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@monitoring_router.get("/logs/{log_file}/download")
def download_log_file(log_file: str):
    """Download the full log file as an attachment.

    Uses the same secure path checks as the tail endpoint and streams the file.
    """
    # Securely construct the full path to the log file
    log_file_path = os.path.abspath(os.path.join(LOG_DIRECTORY, log_file))

    # Security check to prevent path traversal attacks.
    if not log_file_path.startswith(os.path.abspath(LOG_DIRECTORY)):
        raise HTTPException(status_code=400, detail="Invalid log file path.")

    if not os.path.exists(log_file_path) or not os.path.isfile(log_file_path):
        raise HTTPException(status_code=404, detail="Log file not found.")

    try:
        # Return as attachment to prompt browser download
        return FileResponse(
            path=log_file_path,
            media_type="text/plain; charset=utf-8",
            filename=os.path.basename(log_file_path),
        )
    except Exception:
        error_logger.exception(
            f"Failed to stream log file for download: {log_file}")
        raise HTTPException(
            status_code=500, detail="Could not download log file.")


@monitoring_router.get("/stats")
def system_stats():
    """Return basic system stats for admin monitoring.

    Avoids external dependencies; values may be 'None' if not available on the platform.
    """
    try:
        now = time.time()
        uptime_seconds = int(max(0, now - PROCESS_START_TIME))

        # Disk usage for the logs directory parent, fallback to root
        disk_path = LOG_DIRECTORY if os.path.isdir(
            LOG_DIRECTORY) else os.path.sep
        usage = shutil.disk_usage(disk_path)
        disk_total_gb = round(usage.total / (1024 ** 3), 2)
        disk_used_gb = round(usage.used / (1024 ** 3), 2)
        disk_percent = round((usage.used / usage.total) *
                             100, 2) if usage.total else 0.0

        # Load average on Unix; not available on Windows
        try:
            load_avg = os.getloadavg()
        except (AttributeError, OSError):
            load_avg = None

        # Count log files
        try:
            log_files_count = len([f for f in os.listdir(LOG_DIRECTORY) if f.endswith(
                ".log")]) if os.path.isdir(LOG_DIRECTORY) else 0
        except Exception:
            log_files_count = 0

        return {
            "server_time_utc": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime_seconds,
            "platform": platform.platform(),
            "python_version": sys.version.split(" ")[0],
            "load_average": load_avg,
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_percent": disk_percent,
            "logs_dir": LOG_DIRECTORY,
            "log_files_count": log_files_count,
        }
    except Exception as e:
        error_logger.exception("Failed to compute system stats")
        raise HTTPException(
            status_code=500, detail="Failed to compute system stats")


@monitoring_router.get("/config")
def config_diagnostics():
    """Return safe configuration diagnostics for admins.

    Exposes only non-sensitive, masked details useful for debugging configuration issues.
    """
    try:
        settings = _settings
        raw_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY") or ""
        key_present = bool(raw_key)
        # Only reveal a tiny prefix for debugging (avoid leaking the full key)
        masked = f"{raw_key[:7]}******" if key_present else ""

        # Check if the OpenAI client is initialized without making any calls
        client_initialized = getattr(ai_services, "client", None) is not None

        return {
            "openai_key_present": key_present,
            "openai_key_masked": masked,
            "text_model": settings.text_model,
            "image_model": settings.image_model,
            "run_env": settings.run_env,
            "enable_image_style_mapping": settings.enable_image_style_mapping,
            "mount_frontend_static": settings.mount_frontend_static,
            "mount_data_static": settings.mount_data_static,
            "frontend_static_dir": settings.frontend_static_dir,
            "data_dir": settings.data_dir,
            "logs_dir": LOG_DIRECTORY,
            "client_initialized": client_initialized,
        }
    except Exception:
        error_logger.exception("Failed to build config diagnostics")
        raise HTTPException(
            status_code=500, detail="Failed to load diagnostics")
