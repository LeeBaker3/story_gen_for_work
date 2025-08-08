"""
This module provides monitoring endpoints for the application.

It includes routes for listing and retrieving log files, which are
accessible only to authenticated admin users.
"""

from fastapi import APIRouter, Depends, HTTPException, status
import os
from fastapi.responses import PlainTextResponse
from typing import List

from backend.auth import get_current_admin_user
from backend.logging_config import app_logger, error_logger

LOG_DIRECTORY = "data/logs"

monitoring_router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_admin_user)]
)


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
        # Filter for .log files and sort them by modification date
        files = [f for f in os.listdir(
            LOG_DIRECTORY) if f.endswith('.log')]
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
def get_log_file(log_file: str):
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
            lines = f.readlines()
            # For performance and readability, return only the tail of the log.
            return "".join(lines[-1000:])
    except Exception as e:
        error_logger.exception(f"Failed to read log file: {log_file}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read log file: {log_file}"
        )
