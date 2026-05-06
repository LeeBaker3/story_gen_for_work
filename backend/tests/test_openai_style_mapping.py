"""Tests for FR-AI-03 OpenAI image style mapping."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from backend import ai_services
from backend.database import DynamicList, DynamicListItem
from backend.image_style_mapping import get_openai_image_style


def test_get_openai_image_style_defaults_to_vivid(db_session):
    """When no mapping exists, default to vivid."""

    assert get_openai_image_style(
        db=db_session, business_style="Fantasy") == "vivid"


def test_get_openai_image_style_reads_dynamic_list_mapping(db_session):
    """Resolve natural/vivid from DynamicListItem.additional_config."""

    db_session.add(
        DynamicList(
            list_name="image_style_mappings",
            list_label="Image Style → OpenAI Style",
        )
    )
    db_session.add(
        DynamicListItem(
            list_name="image_style_mappings",
            item_value="Fantasy",
            item_label="Fantasy",
            is_active=True,
            additional_config={"openai_style": "natural"},
        )
    )
    db_session.commit()

    assert get_openai_image_style(
        db=db_session, business_style="Fantasy") == "natural"


@patch("backend.ai_services._truncate_prompt", side_effect=lambda p, max_length=4000: p)
@patch("backend.ai_services.client")
def test_generate_image_passes_style_when_supported(mock_openai_client, _mock_truncate):
    """If the model supports `style`, it should be passed through.

    Per OpenAI Images API docs, `style` is only supported for `dall-e-3`.
    """

    prompt = "A test prompt"
    fake_image_bytes = b"img"
    b64_encoded_bytes = base64.b64encode(fake_image_bytes).decode("utf-8")

    mock_image_api_response = MagicMock()
    mock_image_data = MagicMock()
    mock_image_data.b64_json = b64_encoded_bytes
    mock_image_api_response.data = [mock_image_data]
    mock_openai_client.images.generate.return_value = mock_image_api_response

    with patch.object(ai_services, "IMAGE_MODEL", "dall-e-3"):
        result = ai_services.generate_image(
            prompt=prompt, openai_style="vivid")

    mock_openai_client.images.generate.assert_called_once_with(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="auto",
        n=1,
        style="vivid",
    )
    assert result == fake_image_bytes


@patch("backend.ai_services._truncate_prompt", side_effect=lambda p, max_length=4000: p)
@patch("backend.ai_services.client")
def test_generate_image_retries_without_style_on_type_error(
    mock_openai_client, _mock_truncate
):
    """If the SDK rejects `style`, we retry without it.

    This retry logic only applies when using a model that supports the `style`
    parameter (i.e., `dall-e-3`).
    """

    prompt = "A test prompt"
    fake_image_bytes = b"img"
    b64_encoded_bytes = base64.b64encode(fake_image_bytes).decode("utf-8")

    mock_image_api_response = MagicMock()
    mock_image_data = MagicMock()
    mock_image_data.b64_json = b64_encoded_bytes
    mock_image_api_response.data = [mock_image_data]

    def _side_effect(**kwargs):
        if "style" in kwargs:
            raise TypeError("unexpected keyword argument 'style'")
        return mock_image_api_response

    mock_openai_client.images.generate.side_effect = _side_effect

    with patch.object(ai_services, "IMAGE_MODEL", "dall-e-3"):
        result = ai_services.generate_image(
            prompt=prompt, openai_style="vivid")

    assert mock_openai_client.images.generate.call_count == 2
    # First attempt includes style
    first_kwargs = mock_openai_client.images.generate.call_args_list[0].kwargs
    assert first_kwargs.get("style") == "vivid"
    # Second attempt omits it
    second_kwargs = mock_openai_client.images.generate.call_args_list[1].kwargs
    assert "style" not in second_kwargs

    assert result == fake_image_bytes
