"""
This module provides monitoring endpoints for the application.

It includes routes for listing and retrieving log files, which are
accessible only to authenticated admin users.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
import os
from fastapi.responses import PlainTextResponse, FileResponse, Response
from typing import Dict, List, Optional
import sys
import platform
import shutil
import time
from datetime import datetime, timezone

from backend.auth import get_current_admin_user
from backend.logging_config import app_logger, error_logger
from backend.settings import get_settings
from backend import ai_services, schemas, settings as settings_module
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

ADMIN_CONFIG_FIELD_METADATA: Dict[str, schemas.AdminConfigFieldMetadata] = {
    "openai_text_provider": schemas.AdminConfigFieldMetadata(
        label="Text provider",
        input_type="text",
        help_text="Non-secret provider label used for diagnostics and text client routing.",
    ),
    "openai_text_base_url": schemas.AdminConfigFieldMetadata(
        label="Text base URL",
        input_type="url",
        help_text="OpenAI-compatible base URL for future text requests.",
        can_clear=True,
    ),
    "openai_image_provider": schemas.AdminConfigFieldMetadata(
        label="Image provider",
        input_type="text",
        help_text="Non-secret provider label used for diagnostics and image client routing.",
    ),
    "openai_image_base_url": schemas.AdminConfigFieldMetadata(
        label="Image base URL",
        input_type="url",
        help_text="OpenAI-compatible base URL for future image requests.",
        can_clear=True,
    ),
    "text_model": schemas.AdminConfigFieldMetadata(
        label="Text model",
        input_type="text",
        help_text="Model name used for future story text generation requests.",
    ),
    "image_model": schemas.AdminConfigFieldMetadata(
        label="Image model",
        input_type="text",
        help_text="Model name used for future image generation requests.",
    ),
    "enable_image_generation": schemas.AdminConfigFieldMetadata(
        label="Enable image generation",
        input_type="checkbox",
        help_text="Turns AI image generation on or off for future requests.",
    ),
    "use_openai_responses_api": schemas.AdminConfigFieldMetadata(
        label="Use OpenAI Responses API",
        input_type="checkbox",
        help_text="Switches future text generation to the Responses API path.",
    ),
    "openai_text_enable_fallback": schemas.AdminConfigFieldMetadata(
        label="Enable text fallback",
        input_type="checkbox",
        help_text="Allows the text path to fall back to the alternate OpenAI API on failure.",
    ),
    "enable_image_style_mapping": schemas.AdminConfigFieldMetadata(
        label="Enable image style mapping",
        input_type="checkbox",
        help_text="Controls whether admin image style mapping rules are applied.",
    ),
}

ADMIN_CONFIG_UPDATE_NOTES = [
    "Only a safe non-secret subset is editable here.",
    "Changes are stored in private_data/admin_config_overrides.json and override environment defaults for future requests.",
    "Sensitive values such as OPENAI_API_KEY stay masked and cannot be read or edited from this screen.",
    "Long-running or in-flight tasks keep the config they started with; updated values apply to new requests after save.",
]


def _build_config_diagnostics_payload(
    settings: Optional[settings_module.BaseSettings] = None,
) -> dict:
    """Build the safe config diagnostics payload shared by GET and PATCH."""

    effective_settings = settings or get_settings()
    raw_key = (
        effective_settings.openai_api_key
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    key_present = bool(raw_key)
    masked = f"{raw_key[:7]}******" if key_present else ""
    client_initialized = getattr(ai_services, "client", None) is not None
    image_client_initialized = (
        getattr(ai_services, "image_client", None) is not None
    )

    payload = {
        "openai_key_present": key_present,
        "openai_key_masked": masked,
        "openai_text_provider": effective_settings.openai_text_provider,
        "openai_text_base_url": effective_settings.openai_text_base_url,
        "openai_image_provider": effective_settings.openai_image_provider,
        "openai_image_base_url": effective_settings.openai_image_base_url,
        "text_model": effective_settings.text_model,
        "image_model": effective_settings.image_model,
        "enable_image_generation": effective_settings.enable_image_generation,
        "use_openai_responses_api": effective_settings.use_openai_responses_api,
        "openai_text_enable_fallback": getattr(
            effective_settings, "openai_text_enable_fallback", False
        ),
        "run_env": effective_settings.run_env,
        "enable_image_style_mapping": effective_settings.enable_image_style_mapping,
        "mount_frontend_static": effective_settings.mount_frontend_static,
        "mount_data_static": effective_settings.mount_data_static,
        "frontend_static_dir_exists": os.path.isdir(
            effective_settings.frontend_static_dir
        ) if effective_settings.frontend_static_dir else False,
        "data_dir_exists": os.path.isdir(effective_settings.data_dir)
        if effective_settings.data_dir else False,
        "logs_dir_exists": os.path.isdir(LOG_DIRECTORY)
        if LOG_DIRECTORY else False,
        "client_initialized": client_initialized,
        "image_client_initialized": image_client_initialized,
        "editable_values": {
            field_name: getattr(effective_settings, field_name)
            for field_name in settings_module.ADMIN_CONFIG_EDITABLE_FIELDS
        },
        "editable_field_metadata": {
            field_name: field_meta.model_dump()
            for field_name, field_meta in ADMIN_CONFIG_FIELD_METADATA.items()
        },
        "config_update_notes": list(ADMIN_CONFIG_UPDATE_NOTES),
        "override_storage": {
            "relative_path": getattr(
                effective_settings,
                "admin_config_override_relative_path",
                os.path.join("private_data",
                             settings_module.ADMIN_CONFIG_OVERRIDE_FILENAME),
            ),
            "has_overrides": bool(
                getattr(effective_settings, "admin_config_overrides", {})
            ),
            "applied_fields": list(
                getattr(effective_settings, "config_overrides_applied", [])
            ),
        },
    }
    return payload


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
        return _build_config_diagnostics_payload()
    except Exception:
        error_logger.exception("Failed to build config diagnostics")
        raise HTTPException(
            status_code=500, detail="Failed to load diagnostics")


@monitoring_router.patch("/config")
def update_config(
    config_update: schemas.AdminConfigUpdate,
):
    """Persist and apply the safe admin-editable configuration subset."""

    try:
        updates = config_update.model_dump(exclude_unset=True)
        persisted = settings_module.save_admin_config_overrides(updates)
        settings_module.reset_settings_cache()
        refreshed_settings = get_settings()
        ai_services.refresh_runtime_config()

        payload = _build_config_diagnostics_payload(refreshed_settings)
        payload["update_summary"] = {
            "updated_fields": sorted(
                [field for field, value in updates.items() if value is not None]
            ),
            "cleared_fields": sorted(
                [field for field, value in updates.items() if value is None]
            ),
            "persisted_fields": sorted(persisted.keys()),
        }
        return payload
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        error_logger.exception("Failed to update admin config overrides")
        raise HTTPException(
            status_code=500,
            detail="Failed to update configuration",
        )
