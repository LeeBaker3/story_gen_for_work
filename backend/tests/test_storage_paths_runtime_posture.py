from backend import settings as settings_mod
from backend import storage_paths


def _reset_settings(monkeypatch) -> None:
    """Reset settings so storage helpers pick up test environment changes."""

    monkeypatch.setattr(settings_mod, "_settings_instance", None, raising=False)


def test_storage_key_helpers_round_trip_with_legacy_relative_paths(
    monkeypatch,
    tmp_path,
):
    """Prefix-backed storage keys should preserve legacy relative path access."""

    monkeypatch.setenv("RUN_ENV", "test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ASSET_STORAGE_PUBLIC_PREFIX", "public-assets")
    monkeypatch.setenv("ASSET_STORAGE_PRIVATE_PREFIX", "private-assets")
    _reset_settings(monkeypatch)

    legacy_path = "images/user_7/story_9/page_1.png"
    public_key = storage_paths.public_storage_key(legacy_path)
    private_key = storage_paths.private_storage_key("uploads/user_7/photo.png")

    assert public_key == "public-assets/images/user_7/story_9/page_1.png"
    assert private_key == "private-assets/uploads/user_7/photo.png"
    assert storage_paths.normalize_public_asset_path(public_key) == legacy_path
    assert (
        storage_paths.normalize_private_asset_path(private_key)
        == "uploads/user_7/photo.png"
    )
    assert storage_paths.normalize_public_asset_path(legacy_path) == legacy_path


def test_storage_paths_accept_prefixed_public_keys_for_local_resolution(
    monkeypatch,
    tmp_path,
):
    """Local filesystem resolution should still accept prefixed public keys."""

    monkeypatch.setenv("RUN_ENV", "test")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ASSET_STORAGE_PUBLIC_PREFIX", "public-assets")
    _reset_settings(monkeypatch)

    legacy_path = "images/user_3/story_4/page.png"
    prefixed_path = storage_paths.public_storage_key(legacy_path)

    assert storage_paths.is_private_story_asset_path(legacy_path) is True
    assert storage_paths.is_private_story_asset_path(prefixed_path) is True
    assert storage_paths.resolve_data_path(prefixed_path).endswith(legacy_path)