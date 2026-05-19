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

STORY_GENERATION_TASKS_BACKLOG = Gauge(
    "app_story_generation_tasks_backlog",
    "Number of pending story generation tasks waiting for the worker.",
)

STORY_GENERATION_TASKS_IN_PROGRESS = Gauge(
    "app_story_generation_tasks_in_progress",
    "Number of story generation tasks currently in progress.",
)

STORY_WORKER_REGISTERED_RUNTIMES = Gauge(
    "app_story_worker_registered_runtimes",
    "Number of worker runtimes that have persisted a heartbeat row.",
)

STORY_WORKER_HEARTBEAT_AGE_SECONDS = Gauge(
    "app_story_worker_heartbeat_age_seconds",
    "Age in seconds of the most recent worker heartbeat, or -1 when absent.",
)

STORY_WORKER_HEALTHY = Gauge(
    "app_story_worker_healthy",
    "Worker heartbeat health state where 1 is healthy and 0 is stale or absent.",
)

STORY_WORKER_LAST_HEARTBEAT_TIMESTAMP_SECONDS = Gauge(
    "app_story_worker_last_heartbeat_timestamp_seconds",
    "Unix timestamp for the most recent persisted worker heartbeat.",
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

PAGE_IMAGE_FAILURES_TOTAL = Counter(
    "app_story_page_image_failures_total",
    "Total page image generation failures after retries are exhausted.",
)


OPENAI_TEXT_REQUESTS_TOTAL = Counter(
    "app_openai_text_requests_total",
    "Total OpenAI text-generation requests issued by the app.",
    ["path", "outcome"],
)


OPENAI_TEXT_ERRORS_TOTAL = Counter(
    "app_openai_text_errors_total",
    "Total OpenAI text-generation errors by path and error type.",
    ["path", "error_type"],
)


OPENAI_TEXT_LATENCY_SECONDS = Histogram(
    "app_openai_text_latency_seconds",
    "Latency of OpenAI text-generation calls in seconds.",
    ["path", "outcome"],
)


def observe_openai_text_call(
    *,
    path: str,
    outcome: str,
    duration_seconds: float,
    error_type: str | None = None,
) -> None:
    """Record metrics for an OpenAI text-generation call.

    Parameters:
        path: The text API path used ("responses" or "chat_completions").
        outcome: "success" or "error".
        duration_seconds: Duration in seconds.
        error_type: Exception class name when outcome is "error".
    """

    safe_path = (path or "unknown").strip().lower()
    safe_outcome = (outcome or "unknown").strip().lower()
    OPENAI_TEXT_REQUESTS_TOTAL.labels(
        path=safe_path, outcome=safe_outcome).inc()
    OPENAI_TEXT_LATENCY_SECONDS.labels(path=safe_path, outcome=safe_outcome).observe(
        max(0.0, float(duration_seconds))
    )
    if safe_outcome == "error":
        et = (error_type or "unknown").strip()[:64]
        OPENAI_TEXT_ERRORS_TOTAL.labels(path=safe_path, error_type=et).inc()


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
