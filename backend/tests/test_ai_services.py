import pytest
from unittest.mock import patch, MagicMock, ANY
import os
import base64
from backend import ai_services
from backend.schemas import CharacterDetail, ImageStyle

# Assuming OpenAI client is imported like this in ai_services
# from openai import OpenAI # This line is not needed in the test file itself if already imported in ai_services

# Ensure the test environment has necessary configurations if any (e.g., OPENAI_API_KEY)
# For these tests, we'll be mocking the API calls, so live keys aren't strictly needed for the mocks to work.


@pytest.fixture
def mock_openai_client():
    """Fixture to mock the OpenAI client and its methods."""
    with patch('backend.ai_services.client') as mock_client_instance:
        mock_image_api_response = MagicMock()
        mock_image_data = MagicMock()
        mock_image_data.b64_json = "fake_base64_encoded_image_data"
        # Add revised_prompt and gen_id for generate_image return value
        mock_image_data.revised_prompt = "A mock revised prompt."
        mock_image_api_response.created = 1234567890
        mock_image_api_response.data = [mock_image_data]

        mock_client_instance.images.generate.return_value = mock_image_api_response
        mock_client_instance.images.edit.return_value = mock_image_api_response
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

    mock_b64decode.return_value = b"fake_image_bytes"
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle

    ai_services.generate_image(
        page_image_description=page_desc, image_path=image_path
    )

    mock_makedirs.assert_called_once_with(
        os.path.dirname(image_path), exist_ok=True)
    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        size=ai_services.IMAGE_SIZE,
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
    Tests with a single reference image.
    """
    page_desc = "Character X in a forest."
    image_path = "/fake/path/to/save/edited_image.png"
    ref_image_path_1 = "/fake/path/to/ref_image1.png"

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
            ref_image_path_1]
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
        size=ai_services.IMAGE_SIZE
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
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2]
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
        size=ai_services.IMAGE_SIZE
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
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2]
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
        size=ai_services.IMAGE_SIZE
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,
        n=1,
        size=ai_services.IMAGE_SIZE
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
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2]
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
        size=ai_services.IMAGE_SIZE
    )
    mock_ref_file_cm_1.close.assert_called_once()

    mock_output_file_cm_partial.__enter__.assert_called_once()
    mock_output_file_handle_partial.write.assert_called_once_with(
        b"fake_edited_one_ref_bytes")
    mock_output_file_cm_partial.__exit__.assert_called_once()
    mock_openai_client.images.generate.assert_not_called()


@patch('backend.ai_services.os.makedirs')
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')
def test_generate_character_reference_image_success(
    mock_internal_generate_image, mock_uuid, mock_makedirs,
    sample_character_detail, sample_image_style
):
    user_id = 1
    story_id = 100
    unique_id = "abcdef"
    mock_uuid.return_value.hex = unique_id

    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join(
        "data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_{unique_id[:6]}.png"
    expected_image_save_path_on_disk = os.path.join(
        expected_disk_save_dir, expected_image_filename)

    char_name_for_prompt = sample_character_detail.name
    prompt_parts = [
        f"Generate a character sheet for {char_name_for_prompt} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view.",
        "It is crucial that all views depict the exact same character consistently."
    ]
    if sample_character_detail.physical_appearance:
        prompt_parts.append(
            f"Physical Appearance: {sample_character_detail.physical_appearance}.")
    if sample_character_detail.clothing_style:
        prompt_parts.append(
            f"Clothing Style: {sample_character_detail.clothing_style}.")
    if sample_character_detail.key_traits:
        prompt_parts.append(
            f"Key Traits: {sample_character_detail.key_traits}.")
    if sample_character_detail.age:
        prompt_parts.append(f"Age: {sample_character_detail.age}.")
    if sample_character_detail.gender:
        prompt_parts.append(f"Gender: {sample_character_detail.gender}.")

    style_value = sample_image_style.value
    if style_value != "Default":
        prompt_parts.append(f"Style: {style_value}.")
    else:
        prompt_parts.append("Style: Clear, vibrant, detailed illustration.")

    prompt_parts.append(
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    )
    expected_prompt_for_internal_call = " ".join(filter(None, prompt_parts))

    mock_internal_generate_image.return_value = {
        "image_path": expected_image_save_path_on_disk,
        "revised_prompt": "A mock revised prompt from the internal call",
        "gen_id": "mockgenid123"
    }

    result_dict = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style
    )

    mock_makedirs.assert_called_once_with(
        expected_disk_save_dir, exist_ok=True)

    mock_internal_generate_image.assert_called_once_with(
        page_image_description=expected_prompt_for_internal_call,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None,
        character_name_for_reference=None
    )

    expected_db_path_prefix = os.path.join(
        "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_path_for_db = os.path.join(
        expected_db_path_prefix, expected_image_filename)

    assert result_dict is not None
    assert isinstance(result_dict, dict)
    assert result_dict.get(
        "reference_image_path") == expected_image_path_for_db
    assert result_dict.get("name") == sample_character_detail.name
    assert result_dict.get(
        "reference_image_revised_prompt") == "A mock revised prompt from the internal call"
    assert result_dict.get("reference_image_gen_id") == "mockgenid123"


@patch('backend.ai_services.error_logger')
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')
@patch('backend.ai_services.os.makedirs')
def test_generate_character_reference_image_handles_generate_image_failure(
    mock_os_makedirs, mock_generate_image, mock_uuid, mock_error_logger,
    sample_character_detail, sample_image_style
):
    user_id = 1
    story_id = 100
    unique_id = "failurecasehex"
    mock_uuid.return_value.hex = unique_id

    mock_generate_image.side_effect = Exception(
        "Internal image generation failed")

    expected_result = sample_character_detail.model_dump(exclude_none=True)

    result = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style
    )

    assert result == expected_result
    mock_error_logger.error.assert_called_once()

    char_name_for_prompt = sample_character_detail.name
    prompt_parts = [
        f"Generate a character sheet for {char_name_for_prompt} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view.",
        "It is crucial that all views depict the exact same character consistently."
    ]
    if sample_character_detail.physical_appearance:
        prompt_parts.append(
            f"Physical Appearance: {sample_character_detail.physical_appearance}.")
    if sample_character_detail.clothing_style:
        prompt_parts.append(
            f"Clothing Style: {sample_character_detail.clothing_style}.")
    if sample_character_detail.key_traits:
        prompt_parts.append(
            f"Key Traits: {sample_character_detail.key_traits}.")
    if sample_character_detail.age:
        prompt_parts.append(f"Age: {sample_character_detail.age}.")
    if sample_character_detail.gender:
        prompt_parts.append(f"Gender: {sample_character_detail.gender}.")

    style_value = sample_image_style.value
    if style_value != "Default":
        prompt_parts.append(f"Style: {style_value}.")
    else:
        prompt_parts.append("Style: Clear, vibrant, detailed illustration.")

    prompt_parts.append(
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    )
    expected_image_prompt = " ".join(filter(None, prompt_parts))

    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join(
        "data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_{unique_id[:6]}.png"
    expected_image_save_path_on_disk = os.path.join(
        expected_disk_save_dir, expected_image_filename)

    mock_generate_image.assert_called_once_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None,
        character_name_for_reference=None
    )
