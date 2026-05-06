from pathlib import Path

from backend.settings import get_settings
from backend.main import app
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
        raise AssertionError("/static_content mount must exist for this test")

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


def test_static_content_blocks_story_image_paths_but_keeps_other_assets_public():
    settings = get_settings()
    configured_data_dir = Path(settings.data_dir).resolve()
    mount_route = next((r for r in app.routes if getattr(
        r, "path", None) == "/static_content"), None)
    assert mount_route is not None
    base_dir = Path(mount_route.app.directory).resolve() if hasattr(
        mount_route.app, "directory") else configured_data_dir

    story_dir = base_dir / "images" / "user_1" / "story_99"
    character_dir = base_dir / "images" / "user_1" / "characters" / "7"
    story_dir.mkdir(parents=True, exist_ok=True)
    character_dir.mkdir(parents=True, exist_ok=True)
    story_file = story_dir / "page.png"
    character_file = character_dir / "thumb.png"

    try:
        story_file.write_bytes(b"story-image")
        character_file.write_bytes(b"character-image")

        local_client = TestClient(app)

        story_response = local_client.get(
            "/static_content/images/user_1/story_99/page.png"
        )
        character_response = local_client.get(
            "/static_content/images/user_1/characters/7/thumb.png"
        )

        assert story_response.status_code == 404
        assert character_response.status_code == 200
        assert character_response.content == b"character-image"
    finally:
        for path in (story_file, character_file):
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        for directory in (story_dir, character_dir):
            try:
                if directory.exists():
                    directory.rmdir()
            except Exception:
                pass
