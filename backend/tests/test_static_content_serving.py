from pathlib import Path

from backend.settings import get_settings
from backend.main import app
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient


def test_static_content_serves_files_from_data_dir():
    settings = get_settings()
    configured_data_dir = Path(settings.data_dir).resolve()

    # Determine which directory /static_content is currently serving
    base_dir = None
    mount_route = next((r for r in app.routes if getattr(
        r, "path", None) == "/static_content"), None)
    if mount_route and hasattr(mount_route, "app") and hasattr(mount_route.app, "directory"):
        try:
            base_dir = Path(mount_route.app.directory).resolve()
        except Exception:
            base_dir = configured_data_dir
    else:
        # Mount if not present
        app.mount("/static_content",
                  StaticFiles(directory=str(configured_data_dir)), name="static_content")
        base_dir = configured_data_dir

    subdir = base_dir / "test_static"
    subdir.mkdir(parents=True, exist_ok=True)
    test_file = subdir / "hello.txt"

    try:
        test_file.write_text("ok", encoding="utf-8")

        # Create a client AFTER mounting so routes are available
        local_client = TestClient(app)
        # Fetch via mounted static route
        resp = local_client.get(
            f"/static_content/test_static/{test_file.name}")
        assert resp.status_code == 200, resp.text
        assert resp.text == "ok"
    finally:
        # Cleanup
        try:
            if test_file.exists():
                test_file.unlink()
            # Remove subdir if empty
            if subdir.exists():
                subdir.rmdir()
        except Exception:
            # Best-effort cleanup; ignore errors
            pass
