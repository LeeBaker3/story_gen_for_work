from unittest.mock import MagicMock
import pytest

from backend.ai_services import generate_image_for_page
from backend.image_style_mapping import DEFAULT_IMAGE_STYLE_MAP


@pytest.mark.asyncio
async def test_generate_image_for_page_uses_mapped_style(monkeypatch):
    # Enable mapping in settings
    from backend import settings
    # Reset singleton and set env
    import importlib
    import os
    os.environ["ENABLE_IMAGE_STYLE_MAPPING"] = "true"
    importlib.reload(settings)
    from backend.ai_services import _settings as ai_settings
    # Ensure the flag is on in the already-imported ai_services settings
    ai_settings.enable_image_style_mapping = True

    # Arrange
    captured_prompt = {}

    async def fake_to_thread(func, prompt, **kwargs):
        captured_prompt["prompt"] = prompt
        return b"img"

    monkeypatch.setattr(
        "backend.ai_services.asyncio.to_thread", fake_to_thread)
    monkeypatch.setattr("backend.ai_services.os.makedirs",
                        lambda *a, **k: None)

    # Dummy DB session
    mock_db = MagicMock()

    # Pick a style that exists in mapping
    business_style = "Photorealistic"
    mapped_style = DEFAULT_IMAGE_STYLE_MAP[business_style]

    res = await generate_image_for_page(
        page_content="A cat on a sofa",
        style_reference=business_style,
        db=mock_db,
        user_id=1,
        story_id=2,
        page_number=1,
        image_save_path_on_disk="/tmp/x.png",
        image_path_for_db="images/u1/s1/p1.png",
    )

    assert res == "images/u1/s1/p1.png"
    # Verify mapped phrase appears in the prompt
    assert mapped_style in captured_prompt["prompt"]
