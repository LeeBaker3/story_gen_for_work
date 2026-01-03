"""Tests for Prometheus metrics endpoint."""

from __future__ import annotations


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
