import base64
from unittest.mock import patch, MagicMock
import pytest
from backend import ai_services


@patch('backend.ai_services._truncate_prompt', side_effect=lambda p, max_length=4000: p)
@patch('backend.ai_services.client')
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
async def test_generate_character_reference_image_prompt_construction(mock_to_thread):
    """
    Test that generate_character_reference_image constructs the prompt correctly, including all character details.
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
    image_save_path = "/fake/path/img.png"
    image_db_path = "images/user_1/story_1/char_1.png"

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

    # Assert that asyncio.to_thread was called with a correctly constructed prompt
    mock_to_thread.assert_called_once()
    args, kwargs = mock_to_thread.call_args

    # The prompt is the second positional argument to generate_image
    generated_prompt = args[1]

    expected_prompt_parts = [
        "full-body character sheet for Anya",
        "tall with silver hair",
        "wearing dark robes",
        "Key traits: carries a glowing orb",
        "A mysterious sorceress.",
        ". Style: photorealistic.",
        "showing front, side, and back views"
    ]

    for part in expected_prompt_parts:
        assert part in generated_prompt
