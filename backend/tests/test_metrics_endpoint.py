"""Tests for Prometheus metrics endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend import database


def test_metrics_endpoint_returns_prometheus_text(client, admin_auth_headers):
    """Ensure `/metrics` returns Prometheus text format and includes key metrics."""

    resp = client.get(
        "/api/v1/admin/monitoring/metrics",
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200

    content_type = resp.headers.get("content-type", "")
    assert content_type.startswith("text/plain")

    # These should always be present as HELP/TYPE lines once metrics are defined.
    body = resp.text
    assert "app_http_requests_total" in body
    assert "app_http_request_duration_seconds" in body
    assert "app_log_files_total" in body
    assert "app_openai_text_requests_total" in body
    assert "app_openai_text_latency_seconds" in body
    assert "app_openai_text_errors_total" in body
    assert "app_story_page_image_retries_total" in body
    assert "app_story_page_image_failures_total" in body


def test_ops_metrics_endpoint_includes_worker_health_and_queue_state(
    client,
    db_session,
    monkeypatch,
):
    """Ops metrics should expose worker heartbeat and queue backlog gauges."""

    owner = db_session.query(database.User).filter(
        database.User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = database.Story(
        title="Ops Metrics Story",
        story_outline="Outline",
        genre="fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.flush()

    db_session.add_all(
        [
            database.StoryGenerationTask(
                id="ops-pending-task",
                story_id=story.id,
                user_id=owner.id,
                status="pending",
                progress=0,
            ),
            database.StoryGenerationTask(
                id="ops-in-progress-task",
                story_id=story.id,
                user_id=owner.id,
                status="in_progress",
                progress=50,
            ),
            database.WorkerHeartbeat(
                runtime_id="worker-test",
                runtime_role="worker",
                hostname="worker-host",
                last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=5),
            ),
        ]
    )
    db_session.commit()

    monkeypatch.setattr(
        "backend.monitoring_router._settings.ops_metrics_bearer_token",
        "ops-secret",
        raising=False,
    )
    monkeypatch.setattr(
        "backend.settings._settings_instance.ops_metrics_bearer_token",
        "ops-secret",
        raising=False,
    )
    monkeypatch.setattr(
        "backend.settings._settings_instance.worker_heartbeat_stale_after_seconds",
        60,
        raising=False,
    )

    resp = client.get(
        "/api/v1/ops/metrics",
        headers={"Authorization": "Bearer ops-secret"},
    )

    assert resp.status_code == 200
    body = resp.text
    assert "app_story_generation_tasks_backlog 1.0" in body
    assert "app_story_generation_tasks_in_progress 1.0" in body
    assert "app_story_worker_registered_runtimes 1.0" in body
    assert "app_story_worker_healthy 1.0" in body
    assert "app_story_worker_heartbeat_age_seconds" in body
