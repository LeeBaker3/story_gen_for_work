import os
import json
import time
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# Remove the app import and the module-level client, we will use fixtures
# from backend.main import app
# from backend.database import get_db
from backend.auth import create_access_token
from backend import settings as settings_mod
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


def test_config_diagnostics_endpoint(client, monkeypatch, admin_auth_headers):
    """Validate /config returns masked key and expected fields without leaking secrets."""
    # Ensure OPENAI_API_KEY is present in env for this test
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-abcdefg1234567890")

    fake_settings = SimpleNamespace(
        openai_api_key="sk-test-abcdefg1234567890",
        openai_text_provider="local-llm",
        openai_text_base_url="http://localhost:11434/v1",
        openai_image_provider="openai",
        openai_image_base_url="https://api.openai.com/v1",
        text_model="gpt-5.4-mini",
        image_model="gpt-image-2",
        enable_image_generation=False,
        use_openai_responses_api=False,
        openai_text_enable_fallback=False,
        run_env="test",
        enable_image_style_mapping=False,
        mount_frontend_static=False,
        mount_data_static=False,
        frontend_static_dir="/tmp/frontend",
        data_dir="/tmp/data",
    )

    with patch("backend.monitoring_router.get_settings", return_value=fake_settings):
        with patch("backend.monitoring_router.ai_services.client", object()):
            with patch("backend.monitoring_router.ai_services.image_client", None):
                response = client.get(
                    "/api/v1/admin/monitoring/config",
                    headers=admin_auth_headers,
                )

    assert response.status_code == 200
    data = response.json()

    # Presence flags
    assert "openai_key_present" in data and data["openai_key_present"] is True
    assert "openai_key_masked" in data
    # Masking should only reveal a tiny prefix and then stars (no full key exposure)
    masked = data["openai_key_masked"]
    assert masked.endswith("******")
    assert len(masked) >= 6  # has at least the stars
    assert "*" in masked

    # Expected fields present
    for key in [
        "openai_text_provider", "openai_text_base_url",
        "openai_image_provider", "openai_image_base_url",
        "text_model", "image_model", "enable_image_generation", "run_env",
        "enable_image_style_mapping", "mount_frontend_static",
        "mount_data_static", "frontend_static_dir_exists",
        "data_dir_exists", "logs_dir_exists", "client_initialized",
        "image_client_initialized"
    ]:
        assert key in data

    assert data["openai_text_provider"] == "local-llm"
    assert data["openai_text_base_url"] == "http://localhost:11434/v1"
    assert data["openai_image_provider"] == "openai"
    assert data["openai_image_base_url"] == "https://api.openai.com/v1"
    assert data["enable_image_generation"] is False
    assert isinstance(data["frontend_static_dir_exists"], bool)
    assert isinstance(data["data_dir_exists"], bool)
    assert isinstance(data["logs_dir_exists"], bool)
    assert data["editable_values"]["text_model"] == "gpt-5.4-mini"
    assert data["editable_field_metadata"]["text_model"]["label"] == "Text model"
    assert len(data["config_update_notes"]) >= 1


def test_config_diagnostics_endpoint_omits_directory_paths(
    client,
    admin_auth_headers,
):
    """The diagnostics response should not expose directory paths."""

    response = client.get(
        "/api/v1/admin/monitoring/config",
        headers=admin_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "frontend_static_dir" not in data
    assert "data_dir" not in data
    assert "logs_dir" not in data


def test_config_diagnostics_endpoint_requires_admin(
    client,
    regular_user_auth_headers,
):
    """Regular users must not access admin config diagnostics."""

    response = client.get(
        "/api/v1/admin/monitoring/config",
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 403


def test_update_config_endpoint_validates_payload(
    client,
    admin_auth_headers,
):
    """Only the safe subset with valid values should be accepted."""

    response = client.patch(
        "/api/v1/admin/monitoring/config",
        headers=admin_auth_headers,
        json={
            "openai_api_key": "sk-test-should-not-be-accepted",
            "openai_text_base_url": "ftp://localhost/v1",
        },
    )

    assert response.status_code == 422


def test_update_config_endpoint_persists_safe_overrides(
    client,
    tmp_path,
    monkeypatch,
    admin_auth_headers,
):
    """Safe admin config changes should persist and refresh effective settings."""

    override_path = tmp_path / "admin_config_overrides.json"
    monkeypatch.setenv("ADMIN_CONFIG_OVERRIDE_FILE", str(override_path))
    monkeypatch.setenv("TEXT_MODEL", "env-text-model")
    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")
    settings_mod.reset_settings_cache()

    with patch("backend.monitoring_router.ai_services.refresh_runtime_config") as refresh_mock:
        response = client.patch(
            "/api/v1/admin/monitoring/config",
            headers=admin_auth_headers,
            json={
                "text_model": "gpt-4.1-mini",
                "enable_image_generation": False,
                "openai_text_base_url": "http://localhost:11434/v1/",
            },
        )

    assert response.status_code == 200
    refresh_mock.assert_called_once()

    persisted = json.loads(Path(override_path).read_text(encoding="utf-8"))
    assert persisted == {
        "enable_image_generation": False,
        "openai_text_base_url": "http://localhost:11434/v1",
        "text_model": "gpt-4.1-mini",
    }

    data = response.json()
    assert data["editable_values"]["text_model"] == "gpt-4.1-mini"
    assert data["editable_values"]["enable_image_generation"] is False
    assert data["editable_values"]["openai_text_base_url"] == "http://localhost:11434/v1"
    assert data["override_storage"]["has_overrides"] is True
    assert sorted(data["update_summary"]["updated_fields"]) == [
        "enable_image_generation",
        "openai_text_base_url",
        "text_model",
    ]

    settings_mod.reset_settings_cache()
    refreshed_settings = settings_mod.get_settings()
    assert refreshed_settings.text_model == "gpt-4.1-mini"
    assert refreshed_settings.enable_image_generation is False
    assert refreshed_settings.openai_text_base_url == "http://localhost:11434/v1"
