import pytest
from unittest.mock import patch, MagicMock, ANY
import os
import base64
from backend import ai_services
from backend.schemas import CharacterDetail, ImageStyle

# Assuming OpenAI client is imported like this in ai_services
# from openai import OpenAI # This line is not needed in the test file itself if already imported in ai_services

# Ensure the test environment has necessary configurations if any (e.g., OPENAI_API_KEY)
# For these tests, we\'ll be mocking the API calls, so live keys aren\'t strictly needed for the mocks to work.


@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client and its methods."""
    with patch('backend.ai_services.client') as mock_client_instance:
        mock_image_api_response = MagicMock()
        mock_image_data = MagicMock()
        mock_image_data.b64_json = "fake_base64_encoded_image_data"
        mock_image_api_response.data = [mock_image_data]

        mock_client_instance.images.generate = MagicMock(
            return_value=mock_image_api_response)
        mock_client_instance.images.edit = MagicMock(
            return_value=mock_image_api_response)
        yield mock_client_instance


@pytest.fixture
def sample_image_style():  # Fixture for ImageStyle
    """Provides a sample ImageStyle enum for tests."""
    return ImageStyle.DEFAULT


@pytest.fixture
def sample_character_detail():
    """Provides a sample CharacterDetail object for tests."""
    return CharacterDetail(
        name="Test Character",
        description="A brave adventurer.",
        age=30,
        gender="Non-binary",
        physical_appearance="Tall with a keen gaze.",
        clothing_style="Practical leather armor.",
        key_traits="Resourceful and courageous.",
        background="Mysterious origins."
    )


@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_generate_api_when_no_reference(
    mock_b64decode, mock_open, mock_makedirs, mock_openai_client
):
    """
    Test that generate_image calls client.images.generate when no character reference is provided.
    """
    page_desc = "A beautiful landscape."
    image_path = "/fake/path/to/save/image.png"
    openai_style = "vivid"
    quality_param = "standard"  # Default quality used by generate_image in ai_services.py

    mock_b64decode.return_value = b"fake_image_bytes"
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path, openai_style=openai_style, quality=quality_param
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        size=ai_services.IMAGE_SIZE,
        quality=quality_param,
        style=openai_style,
        n=1,
        response_format="b64_json"
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_open.assert_called_once_with(image_path, 'wb')
    mock_file_handle.write.assert_called_once_with(b"fake_image_bytes")
    mock_openai_client.images.edit.assert_not_called()


@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_generate_api_with_natural_style(
    mock_b64decode, mock_open, mock_makedirs, mock_openai_client
):
    """
    Test generate_image with openai_style set to "natural".
    """
    page_desc = "A serene forest scene."
    image_path = "/fake/path/to/save/natural_image.png"
    openai_style = "natural"
    quality_param = "standard"  # Default quality

    mock_b64decode.return_value = b"fake_natural_image_bytes"
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path, openai_style=openai_style, quality=quality_param
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        size=ai_services.IMAGE_SIZE,
        quality=quality_param,
        style=openai_style,
        n=1,
        response_format="b64_json"
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_open.assert_called_once_with(image_path, 'wb')
    mock_file_handle.write.assert_called_once_with(b"fake_natural_image_bytes")
    mock_openai_client.images.edit.assert_not_called()


@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_generate_api_defaults_to_vivid_style_if_none_provided(
    mock_b64decode, mock_open, mock_makedirs, mock_openai_client
):
    """
    Test generate_image defaults to "vivid" style if openai_style is None.
    """
    page_desc = "A futuristic city."
    image_path = "/fake/path/to/save/default_style_image.png"
    openai_style_passed = None  # Pass None to test defaulting
    expected_api_style = "vivid"  # Expected default in ai_services.py
    quality_param = "standard"  # Default quality

    mock_b64decode.return_value = b"fake_default_style_image_bytes"
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path, openai_style=openai_style_passed, quality=quality_param
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        size=ai_services.IMAGE_SIZE,
        quality=quality_param,
        style=expected_api_style,
        n=1,
        response_format="b64_json"
    )
    mock_b64decode.assert_called_once_with("fake_base64_encoded_image_data")
    mock_open.assert_called_once_with(image_path, 'wb')
    mock_file_handle.write.assert_called_once_with(
        b"fake_default_style_image_bytes")
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
    Tests with a single reference image.
    """
    page_desc = "Character X in a forest."
    image_path = "/fake/path/to/save/edited_image.png"
    ref_image_path_1 = "/fake/path/to/ref_image1.png"
    openai_style = "vivid"

    mock_os_path_exists.return_value = True
    mock_b64decode.return_value = b"fake_edited_image_bytes"

    returned_ref_handle = MagicMock(name="ReturnedRefHandle")
    mock_ref_file_cm = MagicMock(name="RefFileContextManager")
    mock_ref_file_cm.__enter__.return_value = returned_ref_handle
    mock_ref_file_cm.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm.close = MagicMock()

    mock_output_file_handle = MagicMock(name="DummyOutputHandle")
    mock_output_file_cm = MagicMock(name="OutputFileContextManager")
    mock_output_file_cm.__enter__.return_value = mock_output_file_handle
    mock_output_file_cm.__exit__ = MagicMock(return_value=None)
    mock_open.side_effect = [mock_ref_file_cm, mock_output_file_cm]

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path, character_reference_image_paths=[
            ref_image_path_1], openai_style=openai_style
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_called_once_with(ref_image_path_1)

    instruction_prefix = (
        "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
        "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
        "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene's style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 2
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm,
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE,
        style=openai_style,
        response_format="b64_json"
    )
    mock_ref_file_cm.close.assert_called_once()
    mock_output_file_cm.__enter__.assert_called_once()
    mock_output_file_handle.write.assert_called_once_with(
        b"fake_edited_image_bytes")
    mock_output_file_cm.__exit__.assert_called_once()


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_uses_edit_api_with_multiple_references(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    page_desc = "Character X and Y in a castle."
    image_path = "/fake/path/to/save/edited_multi_ref_image.png"
    ref_image_path_1 = "/fake/path/to/ref_image1.png"
    ref_image_path_2 = "/fake/path/to/ref_image2.png"
    openai_style = "natural"

    mock_os_path_exists.side_effect = lambda path: True
    mock_b64decode.return_value = b"fake_edited_multi_ref_image_bytes"

    returned_ref_handle_1 = MagicMock(name="ReturnedRefHandle1")
    mock_ref_file_cm_1 = MagicMock(name="RefFileContextManager1")
    mock_ref_file_cm_1.__enter__.return_value = returned_ref_handle_1
    mock_ref_file_cm_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_1.close = MagicMock()

    returned_ref_handle_2 = MagicMock(name="ReturnedRefHandle2")
    mock_ref_file_cm_2 = MagicMock(name="RefFileContextManager2")
    mock_ref_file_cm_2.__enter__.return_value = returned_ref_handle_2
    mock_ref_file_cm_2.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_2.close = MagicMock()

    mock_output_file_handle_multi = MagicMock(name="DummyOutputHandleMulti")
    mock_output_file_cm = MagicMock(name="OutputFileContextManagerMulti")
    mock_output_file_cm.__enter__.return_value = mock_output_file_handle_multi
    mock_output_file_cm.__exit__ = MagicMock(return_value=None)
    mock_open.side_effect = [mock_ref_file_cm_1,
        mock_ref_file_cm_2, mock_output_file_cm]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2],
        openai_style=openai_style
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_any_call(ref_image_path_1)
    mock_os_path_exists.assert_any_call(ref_image_path_2)
    assert mock_os_path_exists.call_count == 2

    num_references = 2
    other_refs_desc = f" Additionally, consider {num_references - 1} other guiding reference concepts implied by the context of this request."
    instruction_prefix = (
        f"IMPORTANT: Use the primary provided image as a strict visual reference for a key character. "
        f"This character in the output image MUST visually match this primary reference (face, hair, build).{other_refs_desc} "
        f"This visual guidance takes precedence. Integrate this character into the following scene. Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 3
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(ref_image_path_2, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm_1,
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE,
        style=openai_style,
        response_format="b64_json"
    )
    mock_ref_file_cm_1.close.assert_called_once()
    mock_ref_file_cm_2.close.assert_called_once()

    mock_output_file_cm.__enter__.assert_called_once()
    mock_output_file_handle_multi.write.assert_called_once_with(
        b"fake_edited_multi_ref_image_bytes")
    mock_output_file_cm.__exit__.assert_called_once()


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_falls_back_to_generate_api_if_edit_fails(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    page_desc = "Character Y fighting a dragon."
    image_path = "/fake/path/to/save/fallback_image.png"
    ref_image_path_1 = "/fake/path/to/ref_image_y1.png"
    ref_image_path_2 = "/fake/path/to/ref_image_y2.png"
    openai_style_for_attempt = "vivid"

    mock_os_path_exists.side_effect = lambda path: True
    mock_openai_client.images.edit.side_effect = Exception("Edit API failed")
    mock_b64decode.return_value = b"fake_fallback_image_bytes"

    returned_ref_handle_fb_1 = MagicMock(name="ReturnedRefHandleFb1")
    mock_ref_file_cm_fb_1 = MagicMock(name="RefFileContextManagerFb1")
    mock_ref_file_cm_fb_1.__enter__.return_value = returned_ref_handle_fb_1
    mock_ref_file_cm_fb_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_fb_1.close = MagicMock()

    returned_ref_handle_fb_2 = MagicMock(name="ReturnedRefHandleFb2")
    mock_ref_file_cm_fb_2 = MagicMock(name="RefFileContextManagerFb2")
    mock_ref_file_cm_fb_2.__enter__.return_value = returned_ref_handle_fb_2
    mock_ref_file_cm_fb_2.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_fb_2.close = MagicMock()

    mock_fallback_output_handle = MagicMock(name="DummyFallbackOutputHandle")
    mock_fallback_output_file_cm = MagicMock(
        name="FallbackOutputFileContextManager")
    mock_fallback_output_file_cm.__enter__.return_value = mock_fallback_output_handle
    mock_fallback_output_file_cm.__exit__ = MagicMock(return_value=None)
    mock_open.side_effect = [mock_ref_file_cm_fb_1,
        mock_ref_file_cm_fb_2, mock_fallback_output_file_cm]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2],
        openai_style=openai_style_for_attempt
    )

    mock_makedirs.assert_any_call(os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_any_call(ref_image_path_1)
    mock_os_path_exists.assert_any_call(ref_image_path_2)
    assert mock_os_path_exists.call_count == 2

    num_references = 2
    other_refs_desc = f" Additionally, consider {num_references - 1} other guiding reference concepts implied by the context of this request."
    instruction_prefix = (
        f"IMPORTANT: Use the primary provided image as a strict visual reference for a key character. "
        f"This character in the output image MUST visually match this primary reference (face, hair, build).{other_refs_desc} "
        f"This visual guidance takes precedence. Integrate this character into the following scene. Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm_fb_1,
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE,
        style=openai_style_for_attempt,
        response_format="b64_json"
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        n=1,
        size=ai_services.IMAGE_SIZE,
        quality="standard",
        style=openai_style_for_attempt,
        response_format="b64_json"
    )
    mock_ref_file_cm_fb_1.close.assert_called_once()
    mock_ref_file_cm_fb_2.close.assert_called_once()

    mock_fallback_output_file_cm.__enter__.assert_called_once()
    mock_fallback_output_handle.write.assert_called_once_with(
        b"fake_fallback_image_bytes")
    mock_fallback_output_file_cm.__exit__.assert_called_once()

    assert mock_open.call_count == 3
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(ref_image_path_2, "rb")
    mock_open.assert_any_call(image_path, 'wb')


@patch('backend.ai_services.os.path.exists')
@patch('backend.ai_services.os.makedirs')
@patch('builtins.open', new_callable=MagicMock)
@patch('backend.ai_services.base64.b64decode')
def test_generate_image_falls_back_if_one_of_multiple_ref_files_missing(
    mock_b64decode, mock_open, mock_makedirs, mock_os_path_exists, mock_openai_client
):
    page_desc = "Character Z near a castle with one good ref."
    image_path = "/fake/path/to/save/fallback_partial_ref_file.png"
    ref_image_path_1 = "/fake/path/to/existent_ref.png"
    ref_image_path_2 = "/fake/path/to/non_existent_ref.png"
    openai_style = "vivid"

    mock_os_path_exists.side_effect = lambda path: path == ref_image_path_1
    mock_b64decode.return_value = b"fake_edited_one_ref_bytes"

    mock_ref_file_handle_1 = MagicMock(name="ref_handle_exist")
    mock_ref_file_cm_1 = MagicMock(name="RefFileContextManagerPartial1")
    mock_ref_file_cm_1.__enter__.return_value = mock_ref_file_handle_1
    mock_ref_file_cm_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_1.close = MagicMock()

    mock_output_file_handle_partial = MagicMock(
        name="DummyOutputHandlePartial")
    mock_output_file_cm_partial = MagicMock(
        name="OutputFileContextManagerPartial")
    mock_output_file_cm_partial.__enter__.return_value = mock_output_file_handle_partial
    mock_output_file_cm_partial.__exit__ = MagicMock(return_value=None)
    mock_open.side_effect = [mock_ref_file_cm_1, mock_output_file_cm_partial]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2],
        openai_style=openai_style
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_os_path_exists.assert_any_call(ref_image_path_1)
    mock_os_path_exists.assert_any_call(ref_image_path_2)
    assert mock_os_path_exists.call_count == 2

    instruction_prefix = (
        "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
        "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
        "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene's style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 2
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm_1,
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE,
        style=openai_style,
        response_format="b64_json"
    )
    mock_ref_file_cm_1.close.assert_called_once()

    mock_output_file_cm_partial.__enter__.assert_called_once()
    mock_output_file_handle_partial.write.assert_called_once_with(
        b"fake_edited_one_ref_bytes")
    mock_output_file_cm_partial.__exit__.assert_called_once()
    mock_openai_client.images.generate.assert_not_called()


@patch(\'backend.ai_services.os.makedirs\')
@patch(\'backend.ai_services.uuid.uuid4\')
@patch(\'backend.ai_services.generate_image\')
def test_generate_character_reference_image_success(
    mock_internal_generate_image, mock_uuid, mock_makedirs, # Renamed mock_generate_image
    sample_character_detail, sample_image_style # mock_openai_client removed as it's not directly used when internal generate_image is mocked
):
    user_id = 1
    story_id = 100
    mock_uuid.return_value.hex = "abcdef123456"
    # Test with "vivid" style from config
    image_styles_config_vivid = {"openai_style": "vivid"}
    expected_openai_style_from_config = "vivid"
    expected_quality_for_char_ref = "hd" # As per generate_character_reference_image implementation

    expected_char_filename_safe_name = "Test_Character" # Based on sample_character_detail.name
    expected_disk_save_dir = os.path.join(
        "data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_abcdef.png" # Using mock_uuid
    expected_image_save_path_on_disk = os.path.join(
        expected_disk_save_dir, expected_image_filename)
    
    # Construct the expected prompt that generate_character_reference_image will build
    char_style_prompt = sample_image_style.value['prompt'] if sample_image_style.value and 'prompt' in sample_image_style.value else ImageStyle.DEFAULT.value['prompt']
    expected_prompt_for_internal_call = (
        f"Full body reference image for character: {sample_character_detail.name}. "
        f"Description: {sample_character_detail.description} "
        f"Age: {sample_character_detail.age}, Gender: {sample_character_detail.gender}. "
        f"Appearance: {sample_character_detail.physical_appearance}. "
        f"Clothing: {sample_character_detail.clothing_style}. "
        f"Key Traits: {sample_character_detail.key_traits}. "
        f"Background: {sample_character_detail.background}. "
        f"Style: {char_style_prompt}."
    )

    # Set up the mock for the internal call to ai_services.generate_image
    mock_internal_generate_image.return_value = {
        "image_path": expected_image_save_path_on_disk, # This is what the outer function expects
        "revised_prompt": "A mock revised prompt from the internal call", 
        "gen_id": "mockgenid123"
    }

    result_dict = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style,
        image_styles_config=image_styles_config_vivid # Passing the config
    )

    mock_makedirs.assert_called_once_with(expected_disk_save_dir, exist_ok=True)
    
    # Assert that the internal generate_image was called with correct parameters
    mock_internal_generate_image.assert_called_once_with(
        page_image_description=expected_prompt_for_internal_call,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None, 
        image_style_prompt_prefix="", 
        page_number=0, 
        total_pages=0, 
        additional_prompt_text="", 
        openai_style=expected_openai_style_from_config, # Asserting style from image_styles_config
        quality=expected_quality_for_char_ref # Asserting "hd" quality
    )

    expected_db_path_prefix = os.path.join(
        "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_path_for_db = os.path.join(
        expected_db_path_prefix, expected_image_filename)

    assert result_dict is not None
    assert isinstance(result_dict, dict)
    assert result_dict.get("reference_image_path") == expected_image_path_for_db
    assert result_dict.get("name") == sample_character_detail.name
    assert result_dict.get("reference_image_revised_prompt") == "Test Revised Prompt"
    assert result_dict.get("reference_image_gen_id") == "testgenid123"


@patch(\'backend.ai_services.os.makedirs\')
@patch(\'backend.ai_services.uuid.uuid4\')
@patch(\'backend.ai_services.generate_image\')
def test_generate_character_reference_image_with_natural_style(
    mock_generate_image, mock_uuid, mock_makedirs,
    sample_character_detail, sample_image_style, mock_openai_client
):
    user_id = 1
    story_id = 101 
    mock_uuid.return_value.hex = "naturalstylehex"
    image_styles_config_natural = {"openai_style": "natural"}

    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join(
        "data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_naturalstylehex.png"
    expected_image_save_path_on_disk = os.path.join(
        expected_disk_save_dir, expected_image_filename)

    mock_generate_image.return_value = {
        "image_path": expected_image_save_path_on_disk,
        "revised_prompt": "Natural Style Revised Prompt",
        "gen_id": "testgenidnatural"
    }

    result_dict = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style,
        image_styles_config=image_styles_config_natural
    )
    
    prompt_parts = [
        f"Generate a character sheet for {sample_character_detail.name} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view. It is crucial that all views depict the exact same character consistently.",
        f"Physical Appearance: {sample_character_detail.physical_appearance}.",
        f"Clothing Style: {sample_character_detail.clothing_style}.",
        f"Key Traits: {sample_character_detail.key_traits}.",
    ]
    if sample_character_detail.age:
        prompt_parts.append(f"Age: {sample_character_detail.age}.")
    if sample_character_detail.gender:
        prompt_parts.append(f"Gender: {sample_character_detail.gender}.")

    style_value = sample_image_style.value if hasattr(
        sample_image_style, 'value') else str(sample_image_style)
    if style_value != "Default":
        prompt_parts.append(f"Style: {style_value}.")
    else:
        prompt_parts.append("Style: Clear, vibrant, detailed illustration.")

    prompt_parts.append(
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    )
    expected_image_prompt = " ".join(filter(None, prompt_parts))

    mock_generate_image.assert_called_once_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None,
        character_name_for_reference=None,
        openai_style="natural"
    )
    expected_db_path_prefix = os.path.join(
        "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_path_for_db = os.path.join(
        expected_db_path_prefix, expected_image_filename)
    assert result_dict.get("reference_image_path") == expected_image_path_for_db
    assert result_dict.get("reference_image_revised_prompt") == "Natural Style Revised Prompt"


@patch(\'backend.ai_services.os.makedirs\')
@patch(\'backend.ai_services.uuid.uuid4\')
@patch(\'backend.ai_services.generate_image\')
def test_generate_character_reference_image_with_no_config_defaults_to_vivid(
    mock_generate_image, mock_uuid, mock_makedirs,
    sample_character_detail, sample_image_style, mock_openai_client
):
    user_id = 1
    story_id = 102 
    mock_uuid.return_value.hex = "noconfighex"

    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join("data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename_none = f"char_{expected_char_filename_safe_name}_ref_noconfighex.png"
    expected_image_save_path_on_disk_none = os.path.join(expected_disk_save_dir, expected_image_filename_none)

    mock_generate_image.return_value = {"image_path": expected_image_save_path_on_disk_none, "revised_prompt": "No Config Prompt", "gen_id": "testgenidnoconfig"}

    result_dict_none = ai_services.generate_character_reference_image(
        character=sample_character_detail, user_id=user_id, story_id=story_id,
        image_style_enum=sample_image_style, image_styles_config=None
    )
    
    prompt_parts = [
        f"Generate a character sheet for {sample_character_detail.name} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view. It is crucial that all views depict the exact same character consistently.",
        f"Physical Appearance: {sample_character_detail.physical_appearance}.",
        f"Clothing Style: {sample_character_detail.clothing_style}.",
        f"Key Traits: {sample_character_detail.key_traits}.",
    ]
    if sample_character_detail.age:
        prompt_parts.append(f"Age: {sample_character_detail.age}.")
    if sample_character_detail.gender:
        prompt_parts.append(f"Gender: {sample_character_detail.gender}.")
    style_value = sample_image_style.value if hasattr(sample_image_style, 'value') else str(sample_image_style)
    if style_value != "Default": prompt_parts.append(f"Style: {style_value}.")
    else: prompt_parts.append("Style: Clear, vibrant, detailed illustration.")
    prompt_parts.append("The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet.")
    expected_image_prompt = " ".join(filter(None, prompt_parts))

    mock_generate_image.assert_called_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk_none, 
        character_reference_image_paths=None,
        character_name_for_reference=None,
        openai_style="vivid"
    )
    assert result_dict_none.get("reference_image_revised_prompt") == "No Config Prompt"

    mock_generate_image.reset_mock()
    mock_uuid.return_value.hex = "emptyconfighex" 
    expected_image_filename_empty = f"char_{expected_char_filename_safe_name}_ref_emptyconfighex.png"
    expected_image_save_path_on_disk_empty = os.path.join(expected_disk_save_dir, expected_image_filename_empty)
    mock_generate_image.return_value = {"image_path": expected_image_save_path_on_disk_empty, "revised_prompt": "Empty Config Prompt", "gen_id": "testgenidemptyconfig"}

    result_dict_empty = ai_services.generate_character_reference_image(
        character=sample_character_detail, user_id=user_id, story_id=story_id, 
        image_style_enum=sample_image_style, image_styles_config={}
    )
    mock_generate_image.assert_called_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk_empty,
        character_reference_image_paths=None,
        character_name_for_reference=None,
        openai_style="vivid"
    )
    assert result_dict_empty.get("reference_image_revised_prompt") == "Empty Config Prompt"


@patch(\'backend.ai_services.error_logger\')
@patch(\'backend.ai_services.uuid.uuid4\')
@patch(\'backend.ai_services.generate_image\')
@patch(\'backend.ai_services.os.makedirs\')
def test_generate_character_reference_image_handles_generate_image_failure(
    mock_os_makedirs, mock_generate_image, mock_uuid, mock_error_logger,
    sample_character_detail, sample_image_style
):
    user_id = 1
    story_id = 100 
    mock_uuid.return_value.hex = "failurecasehex"
    image_styles_config_vivid = {"openai_style": "vivid"} 

    mock_generate_image.side_effect = Exception(
        "Internal image generation failed")

    expected_result = sample_character_detail.model_dump(exclude_none=True)

    result = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style,
        image_styles_config=image_styles_config_vivid
    )

    assert result == expected_result
    mock_error_logger.error.assert_called_once()
    
    prompt_parts = [
        f"Generate a character sheet for {sample_character_detail.name} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view. It is crucial that all views depict the exact same character consistently.",
        f"Physical Appearance: {sample_character_detail.physical_appearance}.",
        f"Clothing Style: {sample_character_detail.clothing_style}.",
        f"Key Traits: {sample_character_detail.key_traits}.",
    ]
    if sample_character_detail.age:
        prompt_parts.append(f"Age: {sample_character_detail.age}.")
    if sample_character_detail.gender:
        prompt_parts.append(f"Gender: {sample_character_detail.gender}.")

    style_value = sample_image_style.value if hasattr(
        sample_image_style, 'value') else str(sample_image_style)
    if style_value != "Default":
        prompt_parts.append(f"Style: {style_value}.")
    else:
        prompt_parts.append("Style: Clear, vibrant, detailed illustration.")

    prompt_parts.append(
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    )
    expected_image_prompt = " ".join(filter(None, prompt_parts))
    
    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join("data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_failurecasehex.png" 
    expected_image_save_path_on_disk = os.path.join(expected_disk_save_dir, expected_image_filename)

    mock_generate_image.assert_called_once_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk, 
        character_reference_image_paths=None,
        character_name_for_reference=None,
        openai_style="vivid" 
    )
