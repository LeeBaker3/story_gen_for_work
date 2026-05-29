"""Best-effort runtime alert delivery for high-severity failures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

import requests

from backend.logging_config import error_logger
from backend.settings import get_settings


def send_high_severity_runtime_alert(
    *,
    source: str,
    summary: str,
    details: Mapping[str, Any] | None = None,
) -> bool:
    """Send one best-effort alert payload for a high-severity runtime failure."""

    settings = get_settings()
    webhook_url = settings.runtime_alert_webhook_url
    if not webhook_url:
        return False

    payload = {
        "event_type": "runtime_failure",
        "severity": "high",
        "source": source,
        "summary": summary,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "details": dict(details or {}),
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=settings.runtime_alert_webhook_timeout_seconds,
        )
        response.raise_for_status()
        return True
    except Exception:
        error_logger.warning(
            "Best-effort runtime alert delivery failed for %s.",
            source,
            exc_info=True,
        )
        return False