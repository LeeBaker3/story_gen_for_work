import os
from typing import Tuple

import pytest

from backend import ai_services
from backend import settings as settings_mod
from backend.database import User


def _reset_settings(monkeypatch, tmp_path, max_upload_bytes: int = 10 * 1024 * 1024) -> Tuple[str, str]:
    """Reset settings to point at temp dirs for DATA_DIR and PRIVATE_DATA_DIR."""
    data_dir = os.path.join(str(tmp_path), "data")
    private_dir = os.path.join(str(tmp_path), "private")
    monkeypatch.setenv("RUN_ENV", "test")
    monkeypatch.setenv("DATA_DIR", data_dir)
    monkeypatch.setenv("PRIVATE_DATA_DIR", private_dir)
    monkeypatch.setenv("MAX_UPLOAD_BYTES", str(max_upload_bytes))

    # Reset settings singleton so subsequent get_settings reads env vars.
    # Important: use monkeypatch so this reset can't leak to other tests.
    monkeypatch.setattr(settings_mod, "_settings_instance",
                        None, raising=False)
    settings_mod.get_settings()
    return data_dir, private_dir


def _get_regular_user_id(db_session) -> int:
    user = db_session.query(User).filter(
        User.username == "user@example.com").first()
    assert user is not None
    return int(user.id)


def _create_character(client, headers) -> int:
    resp = client.post(
        "/api/v1/characters/",
        json={"name": "Alice", "generate_image": False},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return int(resp.json()["id"])


def test_upload_character_photo_stores_privately(
    monkeypatch, tmp_path, client, db_session, regular_user_auth_headers
):
    _, private_dir = _reset_settings(monkeypatch, tmp_path)

    char_id = _create_character(client, regular_user_auth_headers)

    resp = client.post(
        f"/api/v1/characters/{char_id}/photo",
        files={"photo": ("photo.png", b"abc123", "image/png")},
        headers=regular_user_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["character_id"] == char_id
    assert body["size_bytes"] == 6

    user_id = _get_regular_user_id(db_session)
    expected_path = os.path.join(
        private_dir, "uploads", f"user_{user_id}", "characters", str(
            char_id), "photo.png"
    )
    assert os.path.exists(expected_path)


def test_upload_character_photo_rejects_wrong_type(
    monkeypatch, tmp_path, client, regular_user_auth_headers
):
    _reset_settings(monkeypatch, tmp_path)

    char_id = _create_character(client, regular_user_auth_headers)

    resp = client.post(
        f"/api/v1/characters/{char_id}/photo",
        files={"photo": ("photo.txt", b"nope", "text/plain")},
        headers=regular_user_auth_headers,
    )
    assert resp.status_code == 415


def test_upload_character_photo_enforces_size_limit(
    monkeypatch, tmp_path, client, regular_user_auth_headers
):
    _reset_settings(monkeypatch, tmp_path, max_upload_bytes=5)

    char_id = _create_character(client, regular_user_auth_headers)

    resp = client.post(
        f"/api/v1/characters/{char_id}/photo",
        files={"photo": ("photo.png", b"0123456789", "image/png")},
        headers=regular_user_auth_headers,
    )
    assert resp.status_code == 413


def test_upload_character_photo_enforces_ownership(
    monkeypatch, tmp_path, client, regular_user_auth_headers, admin_auth_headers
):
    _reset_settings(monkeypatch, tmp_path)

    char_id = _create_character(client, regular_user_auth_headers)

    resp = client.post(
        f"/api/v1/characters/{char_id}/photo",
        files={"photo": ("photo.png", b"abc123", "image/png")},
        headers=admin_auth_headers,
    )
    # Admin user is a different user; endpoint should not expose existence.
    assert resp.status_code == 404


def test_generate_from_photo_creates_public_reference_image(
    monkeypatch, tmp_path, client, db_session, regular_user_auth_headers
):
    data_dir, private_dir = _reset_settings(monkeypatch, tmp_path)

    char_id = _create_character(client, regular_user_auth_headers)

    upload_resp = client.post(
        f"/api/v1/characters/{char_id}/photo",
        files={"photo": ("photo.png", b"abc123", "image/png")},
        headers=regular_user_auth_headers,
    )
    assert upload_resp.status_code == 200, upload_resp.text

    called = []

    def fake_generate_image(prompt, reference_image_paths=None, size="1024x1024", openai_style=None):
        called.append((prompt, reference_image_paths, size))
        return b"fakepngbytes"

    monkeypatch.setattr(ai_services, "generate_image", fake_generate_image)

    resp = client.post(
        f"/api/v1/characters/{char_id}/generate-from-photo",
        json={"description": "A brave knight", "image_style": "Default"},
        headers=regular_user_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == char_id
    assert body.get("current_image") is not None
    file_path = body["current_image"]["file_path"]

    user_id = _get_regular_user_id(db_session)
    assert file_path.startswith(f"images/user_{user_id}/characters/{char_id}/")

    on_disk = os.path.join(data_dir, file_path)
    assert os.path.exists(on_disk)

    # Ensure reference image generation used the private uploaded photo path.
    assert called
    ref_paths = called[-1][1]
    assert ref_paths and os.path.isabs(ref_paths[0])
    assert ref_paths[0].startswith(private_dir)
