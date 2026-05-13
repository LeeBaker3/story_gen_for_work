from backend import settings as settings_mod
import json


def _reset_settings(monkeypatch) -> None:
    """Reset the cached settings singleton for isolated env-based tests."""

    monkeypatch.setattr(settings_mod, "_settings_instance",
                        None, raising=False)


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
