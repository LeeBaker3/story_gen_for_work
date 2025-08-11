import os
import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Remove the app import and the module-level client, we will use fixtures
# from backend.main import app
# from backend.database import get_db
from backend.auth import create_access_token
# from backend.monitoring_router import LOG_DIRECTORY # This is also patched

# client = TestClient(app) # REMOVE THIS


def test_list_log_files_no_log_dir(client, monkeypatch, admin_auth_headers):
    """
    Tests the endpoint's response when the configured log directory does not exist.
    It should return a 500 Internal Server Error.
    """
    # Patch the LOG_DIRECTORY to a non-existent path
    monkeypatch.setattr("backend.monitoring_router.LOG_DIRECTORY",
                        "/tmp/non_existent_log_dir_for_test")

    response = client.get("/api/v1/admin/monitoring/logs/",
                          headers=admin_auth_headers)

    assert response.status_code == 500
    assert "Log directory configured incorrectly" in response.json()["detail"]


def test_list_log_files_empty_dir(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests the endpoint's response when the log directory is empty.
    It should return a 200 OK with an empty list.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get("/api/v1/admin/monitoring/logs/",
                          headers=admin_auth_headers)

    assert response.status_code == 200
    assert response.json() == []


def test_list_log_files_with_logs_sorted(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests if the endpoint returns a list of log files, sorted by modification time (newest first).
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Create files with different timestamps
    (log_dir / "api_2025_07_10.log").write_text("log entry 2")
    time.sleep(0.1)  # ensure modification times are distinct
    (log_dir / "app_2025_07_11.log").write_text("log entry 1")

    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get("/api/v1/admin/monitoring/logs/",
                          headers=admin_auth_headers)

    assert response.status_code == 200
    # Newest file should be first
    assert response.json() == ["app_2025_07_11.log", "api_2025_07_10.log"]


def test_get_log_file_content(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests retrieving the content of a specific, existing log file.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "test.log"
    log_file.write_text("Hello, this is a log.")

    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get(
        "/api/v1/admin/monitoring/logs/test.log", headers=admin_auth_headers)

    assert response.status_code == 200
    assert response.text == "Hello, this is a log."


def test_get_log_file_not_found(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests requesting a log file that does not exist.
    It should return a 404 Not Found error.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get(
        "/api/v1/admin/monitoring/logs/nonexistent.log", headers=admin_auth_headers)

    assert response.status_code == 404


def test_get_log_file_path_traversal_attack(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests for path traversal vulnerabilities.
    The test client normalizes the URL, so `../` is resolved.
    The result is a request for a file that doesn't exist in the log dir.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    # Create a sensitive file outside the log directory
    (tmp_path / "secret.txt").write_text("secret data")

    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    # Attempt to access the sensitive file using path traversal
    # TestClient will normalize this to /api/v1/admin/monitoring/logs/secret.txt
    response = client.get(
        "/api/v1/admin/monitoring/logs/../secret.txt", headers=admin_auth_headers)

    # The normalized path will be checked against the log directory, and since
    # 'secret.txt' is not in '.../logs/', it will return 404.
    # This still correctly prevents the traversal.
    assert response.status_code == 404


def test_get_log_file_content_last_1000_lines(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests that the endpoint correctly returns only the last 1000 lines of a large log file.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "long.log"
    lines = [f"Line {i}" for i in range(1500)]
    log_file.write_text("\n".join(lines))

    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get(
        "/api/v1/admin/monitoring/logs/long.log", headers=admin_auth_headers)

    assert response.status_code == 200
    content = response.text
    response_lines = content.splitlines()

    # The backend is configured to read the last 1000 lines.
    assert len(response_lines) == 1000
    assert response_lines[0] == "Line 500"
    assert response_lines[-1] == "Line 1499"


def test_get_log_file_with_custom_tail_length(client, tmp_path, monkeypatch, admin_auth_headers):
    """
    Tests that the endpoint honors the 'lines' query parameter and bounds.
    """
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "short.log"
    lines = [f"Row {i}" for i in range(50)]
    log_file.write_text("\n".join(lines))

    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    # Request last 20 lines
    response = client.get(
        "/api/v1/admin/monitoring/logs/short.log?lines=20", headers=admin_auth_headers)
    assert response.status_code == 200
    response_lines = response.text.splitlines()
    assert len(response_lines) == 20
    assert response_lines[0] == "Row 30"
    assert response_lines[-1] == "Row 49"


def test_system_stats_endpoint(client, tmp_path, monkeypatch, admin_auth_headers):
    """Basic validation that /stats returns expected keys and types."""
    # Point logs directory to a temp path
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(
        "backend.monitoring_router.LOG_DIRECTORY", str(log_dir))

    response = client.get("/api/v1/admin/monitoring/stats",
                          headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    # Check a few key fields
    assert "server_time_utc" in data
    assert isinstance(data["uptime_seconds"], int)
    assert "python_version" in data
    assert data["logs_dir"] == str(log_dir)
