"""Fixtures for browser-level UI E2E tests against the real FastAPI app."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator
from urllib.error import URLError
from urllib.request import urlopen

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


def _pick_free_port() -> int:
    """Return an available localhost TCP port."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: float = 20.0) -> None:
    """Wait until the spawned FastAPI server responds to the health check."""

    deadline = time.time() + timeout_seconds
    health_url = f"{base_url}/healthz"
    while time.time() < deadline:
        try:
            with urlopen(health_url) as response:  # noqa: S310
                if response.status == 200:
                    return
        except URLError:
            time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for server at {health_url}")


@pytest.fixture(scope="session")
def e2e_environment(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Create per-session temp paths and environment for the live E2E server."""

    workspace = tmp_path_factory.mktemp("ui-e2e")
    database_path = workspace / "story-e2e.sqlite3"
    data_dir = workspace / "data"
    private_data_dir = workspace / "private_data"
    logs_dir = workspace / "logs"
    port = _pick_free_port()

    env = os.environ.copy()
    env.update(
        {
            "TESTING": "true",
            "RUN_ENV": "test",
            "RUN_UI_E2E": "true",
            "SECRET_KEY": "e2e-secret-key",
            "DATABASE_URL": f"sqlite:///{database_path}",
            "DATA_DIR": str(data_dir),
            "PRIVATE_DATA_DIR": str(private_data_dir),
            "LOGS_DIR": str(logs_dir),
            "MOUNT_FRONTEND_STATIC": "true",
            "MOUNT_DATA_STATIC": "true",
            "ENABLE_IMAGE_GENERATION": "false",
            "OPENAI_API_KEY": "e2e-placeholder-key",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": str(REPO_ROOT),
        }
    )

    seed_command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "seed_e2e_db.py"),
        "--database-url",
        env["DATABASE_URL"],
        "--data-dir",
        env["DATA_DIR"],
        "--private-data-dir",
        env["PRIVATE_DATA_DIR"],
    ]
    subprocess.run(seed_command, check=True, cwd=REPO_ROOT, env=env)

    return {
        "base_url": f"http://127.0.0.1:{port}",
        "port": str(port),
        "workspace": str(workspace),
        "database_path": str(database_path),
        "logs_path": str(workspace / "uvicorn.log"),
        "env": env,
    }


@pytest.fixture(scope="session")
def live_server(e2e_environment: dict[str, str]) -> Iterator[str]:
    """Start the real FastAPI app and yield its base URL."""

    env = dict(e2e_environment["env"])
    log_path = Path(e2e_environment["logs_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log_handle:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                e2e_environment["port"],
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )

        try:
            _wait_for_server(e2e_environment["base_url"])
            yield e2e_environment["base_url"]
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.fixture(scope="session")
def app_base_url(live_server: str) -> str:
    """Expose the base URL of the running E2E server."""

    return live_server
