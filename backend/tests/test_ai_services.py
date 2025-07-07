import base64
from unittest.mock import patch, MagicMock, call
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
