import pytest
from unittest.mock import patch, MagicMock, ANY  # Add ANY
import os
import base64  # Import base64
from backend import ai_services
# Import CharacterDetail and ImageStyle
from backend.schemas import CharacterDetail, ImageStyle

# Assuming OpenAI client is imported like this in ai_services
# from openai import OpenAI # This line is not needed in the test file itself if already imported in ai_services

# Ensure the test environment has necessary configurations if any (e.g., OPENAI_API_KEY)
# For these tests, we\'ll be mocking the API calls, so live keys aren\'t strictly needed for the mocks to work.


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
        model="gpt-image-1",  # Updated model
        prompt=page_desc,
        size="1024x1024",
        n=1
        # response_format="b64_json"  # Removed response_format
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

    # This is what __enter__ would return if used with 'with'
    returned_ref_handle = MagicMock(name="ReturnedRefHandle")
    mock_ref_file_cm = MagicMock(name="RefFileContextManager")
    # For completeness if it were used in a 'with'
    mock_ref_file_cm.__enter__.return_value = returned_ref_handle
    mock_ref_file_cm.__exit__ = MagicMock(return_value=None)
    # For the direct .close() call in ai_services.py
    mock_ref_file_cm.close = MagicMock()

    mock_output_file_handle = MagicMock(name="DummyOutputHandle")
    mock_output_file_cm = MagicMock(name="OutputFileContextManager")
    mock_output_file_cm.__enter__.return_value = mock_output_file_handle
    mock_output_file_cm.__exit__ = MagicMock(return_value=None)

    # open(ref_path, "rb") returns mock_ref_file_cm directly (which is then used as image and closed)
    # open(image_path, "wb") returns mock_output_file_cm (which is used in a 'with' statement)
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
        # Literal for scene\'s
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene\\\'s style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 2
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm,  # Expecting the context manager mock itself
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE
        # response_format="b64_json" # Removed response_format
    )

    # Assert close on the context manager mock
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

    # Mocks for first reference file
    returned_ref_handle_1 = MagicMock(name="ReturnedRefHandle1")
    mock_ref_file_cm_1 = MagicMock(name="RefFileContextManager1")
    mock_ref_file_cm_1.__enter__.return_value = returned_ref_handle_1
    mock_ref_file_cm_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_1.close = MagicMock()

    # Mocks for second reference file
    returned_ref_handle_2 = MagicMock(name="ReturnedRefHandle2")
    mock_ref_file_cm_2 = MagicMock(name="RefFileContextManager2")
    mock_ref_file_cm_2.__enter__.return_value = returned_ref_handle_2
    mock_ref_file_cm_2.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_2.close = MagicMock()

    # Mock for output file
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
        image=mock_ref_file_cm_1,  # Expecting the first context manager mock
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE
        # response_format="b64_json" # Removed response_format
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
    # This b64decode is for the fallback generate call
    mock_b64decode.return_value = b"fake_fallback_image_bytes"

    # Mocks for first reference file (attempted for edit)
    returned_ref_handle_fb_1 = MagicMock(name="ReturnedRefHandleFb1")
    mock_ref_file_cm_fb_1 = MagicMock(name="RefFileContextManagerFb1")
    mock_ref_file_cm_fb_1.__enter__.return_value = returned_ref_handle_fb_1
    mock_ref_file_cm_fb_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_fb_1.close = MagicMock()

    # Mocks for second reference file (attempted for edit)
    returned_ref_handle_fb_2 = MagicMock(name="ReturnedRefHandleFb2")
    mock_ref_file_cm_fb_2 = MagicMock(name="RefFileContextManagerFb2")
    mock_ref_file_cm_fb_2.__enter__.return_value = returned_ref_handle_fb_2
    mock_ref_file_cm_fb_2.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_fb_2.close = MagicMock()

    # Mock for output file (for the fallback generate call)
    mock_fallback_output_handle = MagicMock(name="DummyFallbackOutputHandle")
    mock_fallback_output_file_cm = MagicMock(
        name="FallbackOutputFileContextManager")
    mock_fallback_output_file_cm.__enter__.return_value = mock_fallback_output_handle
    mock_fallback_output_file_cm.__exit__ = MagicMock(return_value=None)

    # open() calls: ref1, ref2 (for edit attempt), then output file (for generate)
    mock_open.side_effect = [mock_ref_file_cm_fb_1,
                             mock_ref_file_cm_fb_2, mock_fallback_output_file_cm]

    ai_services.generate_image(
        page_image_description=page_desc,
        image_path=image_path,
        character_reference_image_paths=[ref_image_path_1, ref_image_path_2]
    )

    mock_makedirs.assert_any_call(os.path.dirname(
        image_path), exist_ok=True)  # Called for edit and generate
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
        image=mock_ref_file_cm_fb_1,  # Expecting the first context manager mock
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE
        # response_format="b64_json" # Removed response_format
    )

    mock_openai_client.images.generate.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        prompt=page_desc,  # Fallback uses original page_desc
        n=1,
        size=ai_services.IMAGE_SIZE
        # response_format="b64_json" # Removed response_format
    )

    mock_ref_file_cm_fb_1.close.assert_called_once()
    mock_ref_file_cm_fb_2.close.assert_called_once()

    mock_fallback_output_file_cm.__enter__.assert_called_once()
    mock_fallback_output_handle.write.assert_called_once_with(
        b"fake_fallback_image_bytes")
    mock_fallback_output_file_cm.__exit__.assert_called_once()

    assert mock_open.call_count == 3  # ref1, ref2, output_for_generate
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(ref_image_path_2, "rb")
    # This is for the generate call
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
    ref_image_path_1 = "/fake/path/to/existent_ref.png"  # Exists
    ref_image_path_2 = "/fake/path/to/non_existent_ref.png"  # Does not exist

    # os.path.exists will be called for ref_image_path_1 then ref_image_path_2
    mock_os_path_exists.side_effect = lambda path: path == ref_image_path_1
    # For the successful edit with one ref
    mock_b64decode.return_value = b"fake_edited_one_ref_bytes"

    # Mock for the existing reference file
    mock_ref_file_handle_1 = MagicMock(name="ref_handle_exist")
    mock_ref_file_cm_1 = MagicMock(name="RefFileContextManagerPartial1")
    mock_ref_file_cm_1.__enter__.return_value = mock_ref_file_handle_1
    mock_ref_file_cm_1.__exit__ = MagicMock(return_value=None)
    mock_ref_file_cm_1.close = MagicMock()

    # Mock for the output file
    mock_output_file_handle_partial = MagicMock(
        name="DummyOutputHandlePartial")
    mock_output_file_cm_partial = MagicMock(
        name="OutputFileContextManagerPartial")
    mock_output_file_cm_partial.__enter__.return_value = mock_output_file_handle_partial
    mock_output_file_cm_partial.__exit__ = MagicMock(return_value=None)

    # open() calls: existent_ref (for edit), then output file (for edit)
    # non_existent_ref is not opened because os.path.exists is false for it.
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
    assert mock_os_path_exists.call_count == 2  # Called for both paths

    # Since only one reference is valid, it uses the single-reference prefix
    instruction_prefix = (
        "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
        "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
        "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
        # Literal for scene\'s
        "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene\\\'s style and actions. "
        "Scene details: "
    )
    expected_edit_prompt = instruction_prefix + page_desc

    assert mock_open.call_count == 2  # existent_ref, output_file
    mock_open.assert_any_call(ref_image_path_1, "rb")
    mock_open.assert_any_call(image_path, 'wb')

    mock_openai_client.images.edit.assert_called_once_with(
        model=ai_services.IMAGE_MODEL,
        image=mock_ref_file_cm_1,  # Expecting the context manager mock for the valid ref
        prompt=expected_edit_prompt,
        n=1,
        size=ai_services.IMAGE_SIZE
        # response_format="b64_json" # Removed response_format
    )

    # Close called on the valid ref file mock
    mock_ref_file_cm_1.close.assert_called_once()

    mock_output_file_cm_partial.__enter__.assert_called_once()
    mock_output_file_handle_partial.write.assert_called_once_with(
        b"fake_edited_one_ref_bytes")
    mock_output_file_cm_partial.__exit__.assert_called_once()

    # Should not fall back to generate
    mock_openai_client.images.generate.assert_not_called()


@patch('backend.ai_services.os.makedirs')
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')
def test_generate_character_reference_image_success(
    mock_generate_image, mock_uuid, mock_makedirs,
    sample_character_detail, sample_image_style,
    mock_openai_client  # This mock is implicitly available due to the class-level patch
):
    user_id = 1
    story_id = 100
    mock_uuid.return_value.hex = "abcdef123456"

    expected_char_filename_safe_name = "Test_Character"
    expected_disk_save_dir = os.path.join(
        "data", "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_filename = f"char_{expected_char_filename_safe_name}_ref_abcdef.png"
    expected_image_save_path_on_disk = os.path.join(
        expected_disk_save_dir, expected_image_filename)

    mock_generate_image.return_value = {
        "image_path": expected_image_save_path_on_disk,
        "revised_prompt": "Test Revised Prompt",
        "gen_id": "testgenid123"
    }

    result_dict = ai_services.generate_character_reference_image(
        character=sample_character_detail,
        user_id=user_id,
        story_id=story_id,
        image_style_enum=sample_image_style
    )

    expected_db_path_prefix = os.path.join(
        "images", f"user_{user_id}", f"story_{story_id}", "references")
    expected_image_path_for_db = os.path.join(
        expected_db_path_prefix, expected_image_filename)

    mock_makedirs.assert_called_once_with(
        expected_disk_save_dir, exist_ok=True)
    mock_uuid.assert_called_once()

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
    # Removed call to ai_services._truncate_prompt

    mock_generate_image.assert_called_once_with(
        page_image_description=expected_image_prompt,
        image_path=expected_image_save_path_on_disk,
        character_reference_image_paths=None,
        character_name_for_reference=None
    )

    assert result_dict is not None
    assert isinstance(result_dict, dict)
    assert result_dict.get(
        "reference_image_path") == expected_image_path_for_db
    assert result_dict.get("name") == sample_character_detail.name
    assert result_dict.get(
        "reference_image_revised_prompt") == "Test Revised Prompt"
    assert result_dict.get("reference_image_gen_id") == "testgenid123"


@patch('backend.ai_services.error_logger')  # Patched specific error_logger
@patch('backend.ai_services.uuid.uuid4')
@patch('backend.ai_services.generate_image')
@patch('backend.ai_services.os.makedirs')
def test_generate_character_reference_image_handles_generate_image_failure(
    # Use mock_error_logger
    mock_os_makedirs, mock_generate_image, mock_uuid, mock_error_logger,
    sample_character_detail, sample_image_style
):
    user_id = 1
    story_id = 100
    mock_uuid.return_value.hex = "abcdef123456"

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
    # Assert on the directly patched logger
    mock_error_logger.error.assert_called_once()
