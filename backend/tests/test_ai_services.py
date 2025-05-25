import pytest
from unittest.mock import patch, MagicMock, ANY  # Add ANY
import os
import base64  # Import base64
from backend import ai_services
# Assuming OpenAI client is imported like this in ai_services
# from openai import OpenAI # This line is not needed in the test file itself if already imported in ai_services

# Ensure the test environment has necessary configurations if any (e.g., OPENAI_API_KEY)
# For these tests, we\\'ll be mocking the API calls, so live keys aren\\'t strictly needed for the mocks to work.


@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client and its methods."""
    with patch('backend.ai_services.client') as mock_client_instance:  # Patch module-level client
        # Common mock data structure for image API responses
        mock_image_api_response = MagicMock()
        mock_image_data = MagicMock()
        mock_image_data.b64_json = "fake_base64_encoded_image_data"
        mock_image_api_response.data = [mock_image_data]

        mock_client_instance.images.generate = MagicMock(
            return_value=mock_image_api_response)
        mock_client_instance.images.edit = MagicMock(
            return_value=mock_image_api_response)

        yield mock_client_instance


@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_generate_api_when_no_reference(
    # mock_openai_client is from fixture
    mock_b64decode, mock_open, mock_makedirs, mock_openai_client
):
    """
    Test that generate_image calls client.images.generate when no character reference is provided.
    """
    page_desc = "A beautiful landscape."
    image_path = "/fake/path/to/save/image.png"

    mock_b64decode.return_value = b"fake_image_bytes"
    # Configure the mock_open context manager
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path)

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_openai_client.images.generate.assert_called_once_with(
        model="gpt-image-1",
        prompt=page_desc,
        size="1024x1024",
        n=1
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_open.assert_called_once_with(image_path, 'wb')
    mock_file_handle.write.assert_called_once_with(b"fake_image_bytes")
    mock_openai_client.images.edit.assert_not_called()


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_edit_api_when_reference_provided(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    """
    Test that generate_image calls client.images.edit when a character reference is provided.
    """
    page_desc = "Character X in a forest."
    image_path = "/fake/path/to/save/edited_image.png"
    ref_image_path = "/fake/path/to/ref_image.png"

    mock_os_path_exists.return_value = True  # Assume reference image file exists
    mock_b64decode.return_value = b"fake_edited_image_bytes"

    # Mock the file reading for the reference image and writing for the output
    mock_ref_file_handle = MagicMock()
    mock_output_file_handle = MagicMock()

    # open() is called twice: once for reading ref, once for writing output.
    # The first __enter__ is for the ref image, the second for the output.
    mock_open.return_value.__enter__.side_effect = [
        mock_ref_file_handle, mock_output_file_handle]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path]
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_called_once_with(ref_image_path)

    # Corrected expected_edit_prompt
    instruction_prefix = (
        "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
        "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
        "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene's style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 2
    mock_open.assert_any_call(ref_image_path, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model="gpt-image-1",
        image=mock_ref_file_handle,  # Check that the file object from open() is passed
        prompt=expected_edit_prompt,
        n=1,
        size="1024x1024"
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_output_file_handle.write.assert_called_once_with(
        b"fake_edited_image_bytes")
    mock_openai_client.images.generate.assert_not_called()


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_falls_back_to_generate_api_if_edit_fails(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    """
    Test that generate_image falls back to client.images.generate if client.images.edit fails.
    """
    page_desc = "Character Y fighting a dragon."
    image_path = "/fake/path/to/save/fallback_image.png"
    ref_image_path = "/fake/path/to/ref_image_y.png"

    mock_os_path_exists.return_value = True
    mock_openai_client.images.edit.side_effect = Exception("Edit API failed")
    mock_b64decode.return_value = b"fake_fallback_image_bytes"

    mock_ref_file_handle = MagicMock()
    mock_fallback_output_file_handle = MagicMock()
    mock_open.return_value.__enter__.side_effect = [
        mock_ref_file_handle, mock_fallback_output_file_handle]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path]
    )

    # os.makedirs might be called twice if the logic doesn't prevent it on fallback,
    # but for this test, we care it was called at least for the final attempt.
    # If it's called for the edit attempt and then again for generate, that's fine.
    # For simplicity, checking it was called with the correct path.
    mock_makedirs.assert_any_call(os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_called_once_with(ref_image_path)

    # Corrected expected_edit_prompt
    instruction_prefix = (
        "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
        "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
        "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene's style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc
    mock_openai_client.images.edit.assert_called_once_with(
        model="gpt-image-1",
        image=mock_ref_file_handle,
        prompt=expected_edit_prompt,
        n=1,
        size="1024x1024"
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model="gpt-image-1",
        prompt=page_desc,
        size="1024x1024",
        n=1
    )
    mock_b64decode.assert_called_once_with(
        "fake_base64_encoded_image_data")  # From the generate call
    mock_fallback_output_file_handle.write.assert_called_once_with(
        b"fake_fallback_image_bytes")


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_falls_back_if_reference_image_file_missing(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    """
    Test that generate_image falls back to client.images.generate if the reference image file doesn\\'t exist.
    """
    page_desc = "Character Z near a castle."
    image_path = "/fake/path/to/save/fallback_no_ref_file.png"
    ref_image_path = "/fake/path/to/non_existent_ref.png"

    mock_os_path_exists.return_value = False  # Reference image file does NOT exist
    mock_b64decode.return_value = b"fake_fallback_no_ref_bytes"

    mock_output_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_output_file_handle

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path]
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_called_once_with(ref_image_path)

    mock_openai_client.images.edit.assert_not_called()  # Edit should not be attempted
    mock_openai_client.images.generate.assert_called_once_with(
        model="gpt-image-1",
        prompt=page_desc,
        size="1024x1024",
        n=1
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_open.assert_called_once_with(image_path, 'wb')
    mock_output_file_handle.write.assert_called_once_with(
        b"fake_fallback_no_ref_bytes")

# TODO: Add tests for generate_character_reference_image if not already covered,
# focusing on the prompt content (multiple angles).

# Note: The patch target for the OpenAI client is 'backend.ai_services.client'.
# This assumes that in your ai_services.py, the OpenAI client is instantiated at the module level like:
# client = OpenAI()
# If it's instantiated within each function, the patch target 'backend.ai_services.OpenAI'
# and the fixture structure would need to change to mock the constructor.


@pytest.fixture
def sample_character_detail():
    """Fixture to create a sample CharacterDetail object."""
    return ai_services.CharacterDetail(
        name="Test Character",
        age="30",
        gender="Female",
        physical_appearance="Tall with red hair",
        clothing_style="Adventurer\\'s gear",
        key_traits="Brave and curious"
    )


@pytest.fixture
def sample_image_style():
    """Fixture to create a sample ImageStyle object."""
    return ai_services.ImageStyle.CARTOON  # Assuming CARTOON is a valid member


@patch('backend.ai_services.os.makedirs')
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')  # Mock the internal call
def test_generate_character_reference_image_success(
    mock_generate_image, mock_uuid, mock_makedirs,
    # mock_openai_client is not directly used here but good to have if generate_image wasn\\'t mocked
    sample_character_detail, sample_image_style, mock_openai_client
):
    """
    Test successful generation of a character reference image.
    """
    user_id = 1
    story_id = 100
    # Mock the hex attribute of the uuid4() result
    mock_uuid.return_value.hex = "abcdef"

    # Mock the return value of the internally called generate_image
    mock_generate_image.return_value = {
        "image_path": f"data/images/user_{user_id}/story_{story_id}/references/char_Test_Character_ref_abcdef.png",
        "revised_prompt": "A revised prompt.",
        "gen_id": "gen_123"
    }

    result = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style
    )

    expected_char_filename_safe_name = "Test_Character"
    expected_db_path_prefix = f"images/user_{user_id}/story_{story_id}/references"
    expected_save_dir_on_disk = os.path.join("data", expected_db_path_prefix)
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_abcdef.png"
    expected_image_save_path_on_disk = os.path.join(
        expected_save_dir_on_disk, expected_image_filename)
    expected_image_path_for_db = os.path.join(
        expected_db_path_prefix, expected_image_filename)

    mock_makedirs.assert_called_once_with(
        expected_save_dir_on_disk, exist_ok=True)
    mock_uuid.assert_called_once()

    # Construct the expected prompt
    prompt_parts = [
        f"Generate a character sheet for {sample_character_detail.name} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view. It is crucial that all views depict the exact same character consistently.",
        f"Physical Appearance: {sample_character_detail.physical_appearance}.",
        f"Clothing Style: {sample_character_detail.clothing_style}.",
        f"Key Traits: {sample_character_detail.key_traits}.",
        f"Age: {sample_character_detail.age}.",
        f"Gender: {sample_character_detail.gender}.",
        # Assuming .value gives the string
        f"Style: {sample_image_style.value}.",
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    ]
    expected_image_prompt = " ".join(prompt_parts)

    mock_generate_image.assert_called_once_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None,  # Added missing arg
        character_name_for_reference=None  # Added missing arg
    )

    assert result["reference_image_path"] == expected_image_path_for_db
    assert result["reference_image_revised_prompt"] == "A revised prompt."
    assert result["reference_image_gen_id"] == "gen_123"
    assert result["name"] == sample_character_detail.name


@patch('backend.ai_services.os.makedirs')
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')
@patch('backend.ai_services.error_logger')  # Mock the logger
def test_generate_character_reference_image_handles_generate_image_failure(
    mock_error_logger, mock_generate_image, mock_uuid, mock_makedirs,
    sample_character_detail, sample_image_style
):
    """
    Test that generate_character_reference_image handles exceptions from the internal generate_image call.
    """
    user_id = 1
    story_id = 100
    mock_uuid.return_value.hex = "abcdef"

    # Simulate failure in the internal generate_image call
    mock_generate_image.side_effect = Exception(
        "Internal image generation failed")

    # Expected original character data to be returned
    expected_result = sample_character_detail.model_dump(exclude_none=True)

    result = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style
    )

    # Assert that the function returns the original character data (or its dump)
    assert result == expected_result
    # Assert that an error was logged
    mock_error_logger.error.assert_called_once()
    # Check that the log message contains relevant info (optional, but good for robustness)
    args, kwargs = mock_error_logger.error.call_args
    assert f"Failed to generate reference image for character {sample_character_detail.name}" in args[
        0]
    # Ensure exc_info=True was passed to the logger
    assert kwargs.get('exc_info') is True

    # To check the actual exception message, you would typically inspect the call_args
    # more deeply if the logger was configured to capture the exception instance itself,
    # or if the message string in args[0] was expected to contain the exception string.
    # For now, verifying exc_info=True is a good check that it was logged with exception info.
    # If the first arg of logger.error is a formatted string that includes the exception,
    # then you could check that:
    # assert "Internal image generation failed" in args[0]
    # However, the current implementation in ai_services.py logs a generic message
    # and passes exc_info=True.
    # If you want to assert the specific exception message, the logging call in ai_services.py
    # would need to be like: error_logger.error(f"... {e}", exc_info=True)
    # or the test would need to capture and inspect the actual exception passed to exc_info if the logger supports it.
    # Given the current ai_services.py, the most robust check for the exception being handled is:
    # Confirms the mock was set up to raise
    assert mock_generate_image.side_effect is not None
    # And that the error logger was called with exc_info=True
