from backend import settings as settings_mod
import json
import pytest


def _reset_settings(monkeypatch) -> None:
    """Reset the cached settings singleton for isolated env-based tests."""

    monkeypatch.setattr(settings_mod, "_settings_instance",
                        None, raising=False)


def _clear_runtime_posture_env(monkeypatch) -> None:
    """Clear posture-related environment variables for isolated tests."""

    for key in [
        "RUN_ENV",
        "DATABASE_URL",
        "DB_BOOTSTRAP_MODE",
        "ASSET_STORAGE_BACKEND",
        "ASSET_STORAGE_PUBLIC_PREFIX",
        "ASSET_STORAGE_PRIVATE_PREFIX",
        "ASSET_STORAGE_S3_BUCKET",
        "ASSET_STORAGE_S3_REGION",
        "ASSET_STORAGE_S3_ENDPOINT_URL",
        "ASSET_STORAGE_S3_ACCESS_KEY_ID",
        "ASSET_STORAGE_S3_SECRET_ACCESS_KEY",
        "MOUNT_DATA_STATIC",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_settings_default_openai_configuration_uses_hosted_defaults(monkeypatch):
    """Hosted OpenAI should remain the default when no overrides are set."""

    for key in [
        "OPENAI_BASE_URL",
        "OPENAI_TEXT_BASE_URL",
        "OPENAI_IMAGE_BASE_URL",
        "OPENAI_TEXT_PROVIDER",
        "OPENAI_IMAGE_PROVIDER",
        "ENABLE_IMAGE_GENERATION",
    ]:
        monkeypatch.delenv(key, raising=False)

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.openai_text_base_url == settings_mod.OPENAI_DEFAULT_BASE_URL
    assert settings.openai_image_base_url == settings_mod.OPENAI_DEFAULT_BASE_URL
    assert settings.openai_text_provider == "openai"
    assert settings.openai_image_provider == "openai"
    assert settings.enable_image_generation is True


def test_settings_support_shared_local_openai_compatible_override(monkeypatch):
    """A shared compatible base URL should apply to both text and image paths."""

    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1/")
    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "false")

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.openai_text_base_url == "http://localhost:11434/v1"
    assert settings.openai_image_base_url == "http://localhost:11434/v1"
    assert settings.openai_text_provider == "openai-compatible"
    assert settings.openai_image_provider == "openai-compatible"
    assert settings.enable_image_generation is False


def test_settings_allow_independent_text_and_image_provider_overrides(monkeypatch):
    """Text and image config should be independently overridable."""

    monkeypatch.setenv("OPENAI_TEXT_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_IMAGE_BASE_URL", "http://localhost:8080/v1/")
    monkeypatch.setenv("OPENAI_TEXT_PROVIDER", "ollama")
    monkeypatch.setenv("OPENAI_IMAGE_PROVIDER", "mock-images")

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.openai_text_base_url == "http://localhost:11434/v1"
    assert settings.openai_image_base_url == "http://localhost:8080/v1"
    assert settings.openai_text_provider == "ollama"
    assert settings.openai_image_provider == "mock-images"


def test_settings_apply_persisted_admin_overrides(monkeypatch, tmp_path):
    """Persisted admin overrides should win over environment defaults."""

    override_path = tmp_path / "admin_config_overrides.json"
    override_path.write_text(
        json.dumps(
            {
                "text_model": "gpt-4.1-mini",
                "enable_image_generation": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ADMIN_CONFIG_OVERRIDE_FILE", str(override_path))
    monkeypatch.setenv("TEXT_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("ENABLE_IMAGE_GENERATION", "true")

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.text_model == "gpt-4.1-mini"
    assert settings.enable_image_generation is False
    assert settings.admin_config_overrides == {
        "text_model": "gpt-4.1-mini",
        "enable_image_generation": False,
    }


@pytest.mark.parametrize("run_env", ["staging", "prod"])
def test_settings_reject_sqlite_outside_local_env(monkeypatch, run_env):
    """Staging and prod must not fall back to SQLite."""

    _clear_runtime_posture_env(monkeypatch)
    monkeypatch.setenv("RUN_ENV", run_env)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./story_generator.db")
    monkeypatch.setenv("ASSET_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("ASSET_STORAGE_S3_BUCKET", "story-assets")
    monkeypatch.setenv("ASSET_STORAGE_S3_REGION", "us-east-1")

    _reset_settings(monkeypatch)
    with pytest.raises(RuntimeError, match="SQLite"):
        settings_mod.get_settings()


def test_settings_reject_filesystem_assets_outside_local_env(monkeypatch):
    """Staging and prod must use the object-storage baseline."""

    _clear_runtime_posture_env(monkeypatch)
    monkeypatch.setenv("RUN_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/app")
    monkeypatch.setenv("DB_BOOTSTRAP_MODE", "migrations")
    monkeypatch.setenv("ASSET_STORAGE_BACKEND", "filesystem")

    _reset_settings(monkeypatch)
    with pytest.raises(RuntimeError, match="ASSET_STORAGE_BACKEND=s3"):
        settings_mod.get_settings()


def test_settings_require_s3_shape_when_object_storage_selected(monkeypatch):
    """Selecting S3 posture should fail fast when required fields are missing."""

    _clear_runtime_posture_env(monkeypatch)
    monkeypatch.setenv("RUN_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/app")
    monkeypatch.setenv("DB_BOOTSTRAP_MODE", "migrations")
    monkeypatch.setenv("ASSET_STORAGE_BACKEND", "s3")
    monkeypatch.delenv("ASSET_STORAGE_S3_BUCKET", raising=False)
    monkeypatch.delenv("ASSET_STORAGE_S3_REGION", raising=False)

    _reset_settings(monkeypatch)
    with pytest.raises(RuntimeError, match="ASSET_STORAGE_S3_BUCKET"):
        settings_mod.get_settings()


def test_settings_disable_data_static_mount_for_object_storage(monkeypatch):
    """Object-storage posture should not mount local data static content."""

    _clear_runtime_posture_env(monkeypatch)
    monkeypatch.setenv("RUN_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/app")
    monkeypatch.setenv("DB_BOOTSTRAP_MODE", "migrations")
    monkeypatch.setenv("ASSET_STORAGE_BACKEND", "s3")
    monkeypatch.setenv("ASSET_STORAGE_S3_BUCKET", "story-assets")
    monkeypatch.setenv("ASSET_STORAGE_S3_REGION", "us-east-1")
    monkeypatch.setenv("MOUNT_DATA_STATIC", "true")

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.asset_storage_backend == "s3"
    assert settings.mount_data_static is False
    assert settings.runtime_schema_bootstrap_enabled is False


def test_settings_keep_local_runtime_bootstrap_defaults(monkeypatch):
    """Local development should keep runtime bootstrap and filesystem storage."""

    _clear_runtime_posture_env(monkeypatch)
    monkeypatch.setenv("RUN_ENV", "dev")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./story_generator.db")

    _reset_settings(monkeypatch)
    settings = settings_mod.get_settings()

    assert settings.database_bootstrap_mode == "runtime"
    assert settings.runtime_schema_bootstrap_enabled is True
    assert settings.asset_storage_backend == "filesystem"
    assert settings.mount_data_static is True
