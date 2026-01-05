"""Prometheus metrics helpers.

This module centralizes Prometheus metric definitions so they can be used across
routers, middleware, and background tasks without creating import cycles.

Notes:
- We intentionally keep label cardinality low.
- For HTTP metrics, we prefer the *route template* (e.g. `/stories/{id}`) when
  available; we fall back to the raw URL path.
"""

from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Gauge, Histogram


HTTP_REQUESTS_TOTAL = Counter(
    "app_http_requests_total",
    "Total HTTP requests processed by the API.",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "app_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)

APP_LOG_FILES_TOTAL = Gauge(
    "app_log_files_total",
    "Number of .log files present in the configured logs directory.",
)

STORY_GENERATION_TASKS_TOTAL = Counter(
    "app_story_generation_tasks_total",
    "Total story generation tasks finished.",
    ["status"],
)

STORY_GENERATION_DURATION_SECONDS = Histogram(
    "app_story_generation_duration_seconds",
    "Duration of story generation tasks in seconds.",
    ["status"],
)

PAGE_IMAGE_RETRIES_TOTAL = Counter(
    "app_story_page_image_retries_total",
    "Total retry attempts for page image generation.",
)


def observe_story_generation(*, status: str, duration_seconds: float) -> None:
    """Record completion metrics for a story generation task.

    Parameters:
        status: Task outcome (e.g., "completed" or "failed").
        duration_seconds: Duration in seconds.
    """

    # Ensure labels are created even if duration is 0.
    STORY_GENERATION_TASKS_TOTAL.labels(status=status).inc()
    STORY_GENERATION_DURATION_SECONDS.labels(status=status).observe(
        max(0.0, float(duration_seconds))
    )


def normalize_http_path(*, raw_path: str, route_template: Optional[str]) -> str:
    """Normalize an HTTP path label to keep cardinality low.

    Prefer the FastAPI/Starlette route template when available (e.g.,
    `/stories/{story_id}`) and fall back to the raw path.
    """

    if route_template:
        return route_template
    return raw_path
