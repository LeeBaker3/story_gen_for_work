import os
import shutil
from typing import Optional

import pytest
from fastapi.testclient import TestClient


def _cleanup_generated_file(file_path_for_db: Optional[str]):
    """Remove any generated image file and its parent folder under data/ to keep tests tidy."""
    if not file_path_for_db:
        return
    abs_path = os.path.join("data", file_path_for_db)
    try:
        if os.path.isfile(abs_path):
            base_dir = os.path.dirname(abs_path)
            # Remove the whole character image folder to avoid residue
            shutil.rmtree(base_dir, ignore_errors=True)
    except Exception:
        # Best-effort cleanup; don't fail tests on cleanup issues
        pass


def test_create_character_without_image(client: TestClient, regular_user_auth_headers: dict):
    payload = {
        "name": "Test Char",
        "description": "A brave hero",
        "age": 12,
        "gender": "female",
        "clothing_style": "cloak",
        "key_traits": "curious, kind",
        "image_style": "Cartoon",
        "generate_image": False,
    }

    res = client.post("/api/v1/characters/", json=payload,
                      headers=regular_user_auth_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["current_image"] is None


def test_create_character_with_image_generation_mocked(client: TestClient, regular_user_auth_headers: dict, monkeypatch):
    # Mock image generation to return deterministic bytes
    def _fake_generate_image(prompt, style, size):  # signature aligned with usage
        return b"\x89PNG\r\n\x1a\nFAKEPNGDATA"

    monkeypatch.setattr(
        "backend.ai_services.generate_image", _fake_generate_image)

    payload = {
        "name": "Image Char",
        "description": "With image",
        "generate_image": True,
    }
    res = client.post("/api/v1/characters/", json=payload,
                      headers=regular_user_auth_headers)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["current_image"] is not None
    file_path_for_db = data["current_image"]["file_path"]
    assert file_path_for_db.startswith("images/user_")
    assert "/characters/" in file_path_for_db
    assert file_path_for_db.endswith(".png")

    # Verify file exists on disk relative to data/
    abs_path = os.path.join("data", file_path_for_db)
    assert os.path.exists(abs_path)

    # Cleanup
    _cleanup_generated_file(file_path_for_db)


@pytest.mark.parametrize("style,byte_sig", [
    ("Cartoon", b"\x89PNG\r\n\x1a\nCARTOON"),
    ("Watercolor", b"\x89PNG\r\n\x1a\nWATER"),
    ("Photorealistic", b"\x89PNG\r\n\x1a\nPHOTO"),
])
def test_create_character_with_various_styles(client: TestClient, regular_user_auth_headers: dict, monkeypatch, style, byte_sig):
    def _fake_generate_image(prompt, style_param, size):  # style_param unused in test
        return byte_sig

    monkeypatch.setattr(
        "backend.ai_services.generate_image", _fake_generate_image)
    res = client.post(
        "/api/v1/characters/",
        json={"name": f"Styled {style}",
              "image_style": style, "generate_image": True},
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["current_image"] is not None
    assert data["current_image"]["file_path"].endswith(".png")
    # cleanup
    _cleanup_generated_file(data["current_image"]["file_path"])


def test_get_character_by_id_and_scope(client: TestClient, regular_user_auth_headers: dict, admin_auth_headers: dict):
    # Create as regular user
    res_create = client.post(
        "/api/v1/characters/",
        json={"name": "Scoped Char"},
        headers=regular_user_auth_headers,
    )
    assert res_create.status_code == 201
    char_id = res_create.json()["id"]

    # Regular user can access
    res_get_user = client.get(
        f"/api/v1/characters/{char_id}", headers=regular_user_auth_headers)
    assert res_get_user.status_code == 200

    # Admin should not access another user's character (scoped per owner)
    res_get_admin = client.get(
        f"/api/v1/characters/{char_id}", headers=admin_auth_headers)
    assert res_get_admin.status_code == 404


def test_update_character_fields(client: TestClient, regular_user_auth_headers: dict):
    res_create = client.post(
        "/api/v1/characters/",
        json={"name": "Updatable", "description": "first"},
        headers=regular_user_auth_headers,
    )
    assert res_create.status_code == 201
    char_id = res_create.json()["id"]

    res_update = client.put(
        f"/api/v1/characters/{char_id}",
        json={"description": "second", "clothing_style": "armor"},
        headers=regular_user_auth_headers,
    )
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["description"] == "second"
    assert updated["clothing_style"] == "armor"


def test_list_characters_with_search_and_pagination(client: TestClient, regular_user_auth_headers: dict):
    # Create multiple characters
    names = ["Alice", "Bob", "Alicia", "Charlie"]
    for n in names:
        client.post("/api/v1/characters/",
                    json={"name": n}, headers=regular_user_auth_headers)

    # Search for 'Ali'
    res_search = client.get(
        "/api/v1/characters?q=Ali&page=1&page_size=10", headers=regular_user_auth_headers)
    assert res_search.status_code == 200
    payload = res_search.json()
    # Should match Alice and Alicia, but not Bob/Charlie
    found_names = [item["name"] for item in payload["items"]]
    assert set(found_names).issubset({"Alice", "Alicia"})
    assert payload["total"] >= 2
    assert payload["page"] == 1

    # Pagination: page_size=1 should return 1 item
    res_page = client.get(
        "/api/v1/characters?page=1&page_size=1", headers=regular_user_auth_headers)
    assert res_page.status_code == 200
    assert len(res_page.json()["items"]) == 1


def test_regenerate_image_sets_current_image(client: TestClient, regular_user_auth_headers: dict, monkeypatch):
    def _fake_generate_image(prompt, style, size):
        return b"\x89PNG\r\n\x1a\nREGENPNG"

    monkeypatch.setattr(
        "backend.ai_services.generate_image", _fake_generate_image)

    # Create without image
    res_create = client.post(
        "/api/v1/characters/",
        json={"name": "Regen Char", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert res_create.status_code == 201
    char = res_create.json()
    assert char["current_image"] is None
    char_id = char["id"]

    # Regenerate -> should create first image
    res_regen1 = client.post(
        f"/api/v1/characters/{char_id}/regenerate-image",
        json={"description": "new look", "image_style": "Cartoon"},
        headers=regular_user_auth_headers,
    )
    assert res_regen1.status_code == 200, res_regen1.text
    ch1 = res_regen1.json()
    assert ch1["current_image"] is not None
    fp1 = ch1["current_image"]["file_path"]
    assert os.path.exists(os.path.join("data", fp1))

    # Change the mock to produce a different byte sequence (not necessary but illustrative)
    def _fake_generate_image_v2(prompt, style, size):
        return b"\x89PNG\r\n\x1a\nREGENPNGv2"

    monkeypatch.setattr("backend.ai_services.generate_image",
                        _fake_generate_image_v2)

    # Regenerate again -> current image should change (new path)
    res_regen2 = client.post(
        f"/api/v1/characters/{char_id}/regenerate-image",
        json={},
        headers=regular_user_auth_headers,
    )
    assert res_regen2.status_code == 200, res_regen2.text
    ch2 = res_regen2.json()
    fp2 = ch2["current_image"]["file_path"]
    assert fp2 != fp1
    assert os.path.exists(os.path.join("data", fp2))

    # Cleanup both images
    _cleanup_generated_file(fp1)
    _cleanup_generated_file(fp2)


def test_delete_character(client: TestClient, regular_user_auth_headers: dict):
    res_create = client.post(
        "/api/v1/characters/",
        json={"name": "Delete Me"},
        headers=regular_user_auth_headers,
    )
    assert res_create.status_code == 201
    char_id = res_create.json()["id"]

    res_del = client.delete(
        f"/api/v1/characters/{char_id}", headers=regular_user_auth_headers)
    assert res_del.status_code == 204

    res_get = client.get(
        f"/api/v1/characters/{char_id}", headers=regular_user_auth_headers)
    assert res_get.status_code == 404


def test_update_nonexistent_character_returns_404(client: TestClient, regular_user_auth_headers: dict):
    res = client.put(
        "/api/v1/characters/9999",
        json={"description": "ghost"},
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"].lower().startswith("character not found")


def test_delete_nonexistent_character_returns_404(client: TestClient, regular_user_auth_headers: dict):
    res = client.delete(
        "/api/v1/characters/9999",
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"].lower().startswith("character not found")


def test_regenerate_nonexistent_character_returns_404(client: TestClient, regular_user_auth_headers: dict):
    res = client.post(
        "/api/v1/characters/9999/regenerate-image",
        json={"description": "does not exist"},
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 404
    assert res.json()["detail"].lower().startswith("character not found")


def test_regenerate_image_permission_denied_other_user(client: TestClient, regular_user_auth_headers: dict, admin_auth_headers: dict, monkeypatch):
    """Ensure a user cannot regenerate an image for a character they don't own (gets 404 due to scoping)."""
    # Create character as regular user
    res_create = client.post(
        "/api/v1/characters/",
        json={"name": "OwnedByRegular"},
        headers=regular_user_auth_headers,
    )
    assert res_create.status_code == 201
    char_id = res_create.json()["id"]

    # Mock generate to ensure if wrongly called it would still work; we just check status
    monkeypatch.setattr(
        "backend.ai_services.generate_image", lambda *a, **kw: b"\x89PNG\r\n\x1a\nPERM"
    )

    # Attempt regenerate as admin (different user) should return 404 (not found due to owner scoping)
    res_regen = client.post(
        f"/api/v1/characters/{char_id}/regenerate-image",
        json={"description": "should fail"},
        headers=admin_auth_headers,
    )
    assert res_regen.status_code == 404


def test_list_ordering_reflects_updated_at(client: TestClient, regular_user_auth_headers: dict):
    # Create two characters
    res1 = client.post(
        "/api/v1/characters/",
        json={"name": "First"},
        headers=regular_user_auth_headers,
    )
    assert res1.status_code == 201
    id1 = res1.json()["id"]
    res2 = client.post(
        "/api/v1/characters/",
        json={"name": "Second"},
        headers=regular_user_auth_headers,
    )
    assert res2.status_code == 201
    id2 = res2.json()["id"]

    # Update the first one to bump its updated_at
    res_update = client.put(
        f"/api/v1/characters/{id1}",
        json={"description": "bumped"},
        headers=regular_user_auth_headers,
    )
    assert res_update.status_code == 200

    # List should show the first character before the second (most recently updated first)
    res_list = client.get(
        "/api/v1/characters?page=1&page_size=10",
        headers=regular_user_auth_headers,
    )
    assert res_list.status_code == 200
    items = res_list.json()["items"]
    names_in_order = [i["name"]
                      for i in items if i["name"] in {"First", "Second"}]
    assert names_in_order[0] == "First"
