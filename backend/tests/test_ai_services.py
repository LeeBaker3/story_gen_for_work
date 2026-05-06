import base64
from unittest.mock import patch, MagicMock, call
import pytest
import requests
from backend import ai_services
from backend import logging_config


def _build_story_input() -> dict:
    """Return the minimal valid story input for generation tests."""

    return {
        "title": "Moonlit Rescue",
        "genre": "Fantasy",
        "story_outline": "A child helps a lost dragon find its way home.",
        "main_characters": [
            {
                "name": "Mira",
                "description": "A curious child with a lantern.",
                "physical_appearance": "short brown hair and bright eyes",
                "clothing_style": "a blue raincoat",
                "key_traits": "brave and kind",
            }
        ],
        "num_pages": 2,
        "tone": "Hopeful",
        "setting": "A quiet forest village",
        "image_style": "Watercolor",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)",
    }


@patch('backend.ai_services._truncate_prompt', side_effect=lambda p, max_length=4000: p)
@patch('backend.ai_services.image_client')
def test_generate_image(mock_openai_client, mock_truncate_prompt):
    """
    Test that generate_image calls client.images.generate with the correct parameters and returns image bytes.
    """
    prompt = "A beautiful landscape."
    fake_image_bytes = b"fake_image_bytes"
    b64_encoded_bytes = base64.b64encode(fake_image_bytes).decode('utf-8')

    # Mock OpenAI API response
    mock_image_api_response = MagicMock()
    mock_image_data = MagicMock()
    mock_image_data.b64_json = b64_encoded_bytes
    mock_image_api_response.data = [mock_image_data]
    mock_openai_client.images.generate.return_value = mock_image_api_response

    # Call the function
    result_bytes = ai_services.generate_image(prompt=prompt)

    # Assertions
    mock_truncate_prompt.assert_called_once_with(prompt)

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",  # Default size
        quality="auto",
        n=1,
    )

    assert result_bytes == fake_image_bytes


@patch('backend.ai_services.OpenAI')
def test_create_openai_client_uses_configured_base_url(mock_openai_class):
    """Client creation should pass through the configured compatible base URL."""

    with patch.object(ai_services, 'OPENAI_API_KEY', 'dummy-key'):
        client = ai_services._create_openai_client("http://localhost:11434/v1")

    assert client is mock_openai_class.return_value
    mock_openai_class.assert_called_once_with(
        api_key='dummy-key',
        base_url="http://localhost:11434/v1",
    )


@patch('backend.ai_services._truncate_prompt')
def test_generate_image_returns_none_when_disabled(mock_truncate_prompt):
    """Image generation should skip API calls entirely when disabled."""

    with patch.object(ai_services._settings, 'enable_image_generation', False):
        assert ai_services.generate_image(prompt="skip images") is None

    mock_truncate_prompt.assert_not_called()


def test_should_retry_openai_error_excludes_bad_request():
    """Client-side request errors should not be retried."""

    bad_request = ai_services.openai.BadRequestError(
        message="blocked",
        response=MagicMock(request=MagicMock(), status_code=400),
        body={"error": {"code": "moderation_blocked"}},
    )

    assert ai_services._should_retry_openai_error(bad_request) is False


def test_should_retry_openai_error_retries_transport_failures():
    """Transport failures should still be retried."""

    assert ai_services._should_retry_openai_error(
        requests.exceptions.ConnectionError("network")
    ) is True


def test_ai_services_uses_configured_loggers():
    """ai_services should keep the configured logger instances from logging_config."""

    assert ai_services.error_logger is logging_config.error_logger
    assert ai_services.warning_logger is logging_config.warning_logger


@patch('backend.ai_services._generate_story_text_via_chat_completions')
@patch('backend.ai_services._generate_story_text_via_responses')
@patch('backend.ai_services._use_openai_responses_api', return_value=True)
@patch('backend.ai_services._ensure_client_available')
def test_generate_story_from_chatgpt_uses_responses_path(
    mock_ensure_client_available,
    mock_use_openai_responses_api,
    mock_generate_via_responses,
    mock_generate_via_chat_completions,
):
    """Story generation should use Responses API when that path is enabled."""

    mock_generate_via_responses.return_value = (
        '{"Title": "Moonlit Rescue", "Pages": []}'
    )

    result = ai_services.generate_story_from_chatgpt(_build_story_input())

    assert result == {"Title": "Moonlit Rescue", "Pages": []}
    mock_generate_via_responses.assert_called_once()
    mock_generate_via_chat_completions.assert_not_called()


@patch('backend.ai_services.client')
def test_generate_story_text_via_responses_rejects_empty_output(
    mock_openai_client,
):
    """Responses API should fail fast when output_text is empty."""

    mock_openai_client.responses.create.return_value = MagicMock(
        output_text=" ")

    with pytest.raises(ValueError, match="empty output_text"):
        ai_services._generate_story_text_via_responses("prompt text")


@patch('backend.ai_services._generate_story_text_via_chat_completions')
@patch('backend.ai_services._generate_story_text_via_responses')
@patch('backend.ai_services._use_openai_responses_api', return_value=True)
@patch('backend.ai_services._ensure_client_available')
def test_generate_story_from_chatgpt_falls_back_to_chat_completions(
    mock_ensure_client_available,
    mock_use_openai_responses_api,
    mock_generate_via_responses,
    mock_generate_via_chat_completions,
):
    """Fallback should use chat completions after a responses failure."""

    mock_generate_via_responses.side_effect = RuntimeError("responses failed")
    mock_generate_via_chat_completions.return_value = (
        '{"Title": "Recovered", "Pages": []}'
    )

    with patch.object(
        ai_services._settings,
        'openai_text_enable_fallback',
        True,
    ):
        result = ai_services.generate_story_from_chatgpt(_build_story_input())

    assert result == {"Title": "Recovered", "Pages": []}
    mock_generate_via_responses.assert_called_once()
    mock_generate_via_chat_completions.assert_called_once()


@patch('backend.ai_services._generate_story_text_via_chat_completions')
@patch('backend.ai_services._use_openai_responses_api', return_value=False)
@patch('backend.ai_services._ensure_client_available')
def test_generate_story_from_chatgpt_raises_json_decode_error(
    mock_ensure_client_available,
    mock_use_openai_responses_api,
    mock_generate_via_chat_completions,
):
    """Invalid model JSON should surface the JSON decode error."""

    mock_generate_via_chat_completions.return_value = "not valid json"

    with pytest.raises(__import__('json').JSONDecodeError):
        ai_services.generate_story_from_chatgpt(_build_story_input())


@patch('backend.ai_services._generate_story_text_via_chat_completions')
@patch('backend.ai_services._use_openai_responses_api', return_value=False)
@patch('backend.ai_services._ensure_client_available')
def test_generate_story_from_chatgpt_includes_new_wizard_preferences_in_prompt(
    mock_ensure_client_available,
    mock_use_openai_responses_api,
    mock_generate_via_chat_completions,
):
    """Prompt construction should include the new wizard preferences."""

    mock_generate_via_chat_completions.return_value = (
        '{"Title": "Moonlit Rescue", "Pages": []}'
    )
    story_input = _build_story_input()
    story_input['writing_style'] = 'Playful'
    story_input['editor_settings'] = {
        'text_position': 'top-center',
        'image_fit': 'Keep artwork contained',
        'cover_title_placement': 'Top',
        'readability_treatment': 'High-contrast box',
    }

    ai_services.generate_story_from_chatgpt(story_input)

    prompt = mock_generate_via_chat_completions.call_args.args[0]
    assert 'Optional writing style: Playful.' in prompt
    assert 'artwork can sit contained on the page without awkward cropping' in prompt
    assert 'high-contrast text box' in prompt
    assert 'title-page cover guidance' in prompt


@patch('backend.ai_services._truncate_prompt', side_effect=lambda p, max_length=4000: p)
@patch('backend.ai_services.image_client')
def test_generate_image_returns_none_when_moderation_blocked(
    mock_openai_client,
    mock_truncate_prompt,
):
    """Moderation-blocked image requests should degrade to a missing image."""

    bad_request = ai_services.openai.BadRequestError(
        message="blocked",
        response=MagicMock(request=MagicMock(), status_code=400),
        body={
            "error": {
                "code": "moderation_blocked",
                "type": "image_generation_user_error",
                "message": "Rejected by safety system.",
            }
        },
    )
    mock_openai_client.images.generate.side_effect = bad_request

    assert ai_services.generate_image(prompt="blocked prompt") is None
    mock_truncate_prompt.assert_called_once_with("blocked prompt")


@patch('backend.ai_services._truncate_prompt', side_effect=lambda p, max_length=4000: p)
@patch('builtins.open')
@patch('backend.ai_services.os.path.exists', return_value=True)
@patch('backend.ai_services.image_client')
def test_generate_image_uses_edit_for_existing_reference_images(
    mock_openai_client,
    mock_path_exists,
    mock_open,
    mock_truncate_prompt,
):
    """Image generation should use the edit API when references exist."""

    fake_image_bytes = b"edited_image_bytes"
    b64_encoded_bytes = base64.b64encode(fake_image_bytes).decode('utf-8')
    mock_open.side_effect = [MagicMock(), MagicMock()]

    mock_edit_response = MagicMock()
    mock_edit_response.data = [MagicMock(b64_json=b64_encoded_bytes)]
    mock_openai_client.images.edit.return_value = mock_edit_response

    result = ai_services.generate_image(
        prompt="Draw Mira in the forest.",
        reference_image_paths=["/tmp/ref-1.png", "/tmp/ref-2.png"],
    )

    assert result == fake_image_bytes
    mock_openai_client.images.edit.assert_called_once()
    mock_openai_client.images.generate.assert_not_called()
    edit_kwargs = mock_openai_client.images.edit.call_args.kwargs
    assert edit_kwargs["prompt"] == "Draw Mira in the forest."
    assert len(edit_kwargs["image"]) == 2


@patch('backend.ai_services._truncate_prompt', side_effect=lambda p, max_length=4000: p)
@patch('backend.ai_services.os.path.exists', return_value=False)
@patch('backend.ai_services.image_client')
def test_generate_image_falls_back_to_generate_when_references_missing(
    mock_openai_client,
    mock_path_exists,
    mock_truncate_prompt,
):
    """Missing reference files should fall back to normal image generation."""

    fake_image_bytes = b"generated_image_bytes"
    b64_encoded_bytes = base64.b64encode(fake_image_bytes).decode('utf-8')

    mock_generate_response = MagicMock()
    mock_generate_response.data = [MagicMock(b64_json=b64_encoded_bytes)]
    mock_openai_client.images.generate.return_value = mock_generate_response

    result = ai_services.generate_image(
        prompt="Draw Mira in the forest.",
        reference_image_paths=["/tmp/missing-ref.png"],
    )

    assert result == fake_image_bytes
    mock_openai_client.images.edit.assert_not_called()
    mock_openai_client.images.generate.assert_called_once()


@pytest.mark.asyncio
@patch('backend.ai_services.asyncio.to_thread')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open')
async def test_generate_character_reference_image_size(mock_open, mock_makedirs, mock_to_thread):
    """
    Test that generate_character_reference_image calls generate_image with the correct portrait size.
    """
    # Mock inputs
    mock_character = MagicMock()
    mock_character.name = "Lila"
    mock_character.description = "A brave explorer"
    mock_character.physical_appearance = None
    mock_character.clothing_style = None
    mock_character.key_traits = None
    mock_character.model_dump.return_value = {
        'name': 'Lila', 'description': 'A brave explorer'}

    mock_story_input = MagicMock()
    mock_story_input.image_style = "fantasy"

    mock_db = MagicMock()
    user_id = 1
    story_id = 1
    image_save_path = "/fake/path/img.png"
    image_db_path = "images/user_1/story_1/char_1.png"

    # Mock the return value of the generate_image call inside to_thread
    mock_to_thread.return_value = b"fake_image_data"

    # Call the function
    await ai_services.generate_character_reference_image(
        character=mock_character,
        story_input=mock_story_input,
        db=mock_db,
        user_id=user_id,
        story_id=story_id,
        image_save_path_on_disk=image_save_path,
        image_path_for_db=image_db_path
    )

    # Assert that asyncio.to_thread was called with generate_image and the correct size
    mock_to_thread.assert_called_once()
    args, kwargs = mock_to_thread.call_args
    assert args[0] == ai_services.generate_image
    assert 'size' in kwargs
    assert kwargs['size'] == '1024x1536'


@pytest.mark.asyncio
@patch('backend.ai_services.asyncio.to_thread')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
async def test_generate_character_reference_image_prompt_and_file_saving(mock_open, mock_makedirs, mock_to_thread):
    """
    Test that generate_character_reference_image:
    1. Constructs the prompt correctly with the style at the forefront.
    2. Saves the prompt to a corresponding text file.
    """
    # Mock inputs
    mock_character = MagicMock()
    mock_character.name = "Anya"
    mock_character.description = "A mysterious sorceress."
    mock_character.physical_appearance = "tall with silver hair"
    mock_character.clothing_style = "dark robes"
    mock_character.key_traits = "carries a glowing orb"
    mock_character.model_dump.return_value = {
        'name': 'Anya',
        'description': 'A mysterious sorceress.',
        'physical_appearance': 'tall with silver hair',
        'clothing_style': 'dark robes',
        'key_traits': 'carries a glowing orb'
    }

    mock_story_input = MagicMock()
    mock_story_input.image_style = "photorealistic"

    mock_db = MagicMock()
    user_id = 1
    story_id = 1
    image_save_path = "/fake/path/Anya_ref_story_1.png"
    image_db_path = "images/user_1/story_1/char_1.png"
    fake_image_data = b"fake_image_data"
    mock_to_thread.return_value = fake_image_data

    # Create separate mock handles for each file that will be opened
    mock_image_handle = MagicMock()
    mock_prompt_handle = MagicMock()

    # When open is called, return the correct handle based on the file path
    def open_side_effect(path, *args, **kwargs):
        if path == image_save_path:
            return mock_image_handle
        else:
            # The other call is for the prompt file
            return mock_prompt_handle
    mock_open.side_effect = open_side_effect

    # Call the function
    await ai_services.generate_character_reference_image(
        character=mock_character,
        story_input=mock_story_input,
        db=mock_db,
        user_id=user_id,
        story_id=story_id,
        image_save_path_on_disk=image_save_path,
        image_path_for_db=image_db_path
    )

    # 1. Assert prompt construction
    mock_to_thread.assert_called_once()
    args, kwargs = mock_to_thread.call_args
    # The called function is the first arg, the prompt is the second positional argument
    assert args[0] == ai_services.generate_image
    generated_prompt = args[1]

    assert generated_prompt.startswith(
        "A photorealistic style full-body character sheet for Anya")
    assert "tall with silver hair" in generated_prompt
    assert "wearing dark robes" in generated_prompt
    assert "Key traits: carries a glowing orb" in generated_prompt
    assert "A mysterious sorceress." in generated_prompt
    assert "showing front, side, and back views" in generated_prompt

    # 2. Assert file and prompt saving
    prompt_save_path = "/fake/path/Anya_ref_prompt_story_1.txt"

    # Check that open was called for both files
    mock_open.assert_has_calls([
        call(image_save_path, "wb"),
        call(prompt_save_path, "w", encoding='utf-8')
    ], any_order=True)

    # Check that the correct data was written to each mock handle
    mock_image_handle.__enter__().write.assert_called_once_with(fake_image_data)
    mock_prompt_handle.__enter__().write.assert_called_once_with(generated_prompt)


@pytest.mark.asyncio
@patch('backend.ai_services.asyncio.to_thread')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
async def test_generate_image_for_page_saves_prompt(mock_open, mock_makedirs, mock_to_thread):
    """
    Test that generate_image_for_page saves the prompt to a text file.
    """
    # Mock inputs
    page_content = "A dragon flies over a castle."
    style_reference = "fantasy art"
    # This is the exact prompt constructed in the function
    prompt = f"A {style_reference} style image of {page_content}"
    image_save_path = "/fake/path/page_1_image.png"
    prompt_save_path = "/fake/path/page_1_image_prompt.txt"

    mock_db = MagicMock()
    user_id = 1
    story_id = 1
    page_number = 1
    image_db_path = "images/user_1/story_1/page_1.png"
    fake_image_data = b"fake_image_data"

    mock_to_thread.return_value = fake_image_data

    # Create separate mock handles for each file that will be opened
    mock_image_handle = MagicMock()
    mock_prompt_handle = MagicMock()

    # When open is called, return the correct handle based on the file path
    def open_side_effect(path, *args, **kwargs):
        if path == image_save_path:
            return mock_image_handle
        else:
            return mock_prompt_handle
    mock_open.side_effect = open_side_effect

    # Call the function
    await ai_services.generate_image_for_page(
        page_content=page_content,
        style_reference=style_reference,
        db=mock_db,
        user_id=user_id,
        story_id=story_id,
        page_number=page_number,
        image_save_path_on_disk=image_save_path,
        image_path_for_db=image_db_path
    )

    # Assert file writing
    mock_open.assert_has_calls([
        call(image_save_path, "wb"),
        call(prompt_save_path, "w", encoding='utf-8')
    ], any_order=True)

    # Check that the correct data was written to each mock handle
    mock_image_handle.__enter__().write.assert_called_once_with(fake_image_data)
    mock_prompt_handle.__enter__().write.assert_called_once_with(prompt)
