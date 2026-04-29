from unittest.mock import MagicMock, call, patch
import pytest

from backend import ai_services
from backend.ai_services import generate_character_reference_image, generate_image_for_page
from backend.database import DynamicList, DynamicListItem
from backend.image_style_mapping import DEFAULT_IMAGE_STYLE_MAP


@pytest.mark.asyncio
@patch("backend.ai_services.asyncio.to_thread")
@patch("backend.ai_services.os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
async def test_generate_image_for_page_uses_dynamic_default_style_and_prompt_modifier(
    mock_open,
    _mock_makedirs,
    mock_to_thread,
    db_session,
):
    ai_services._settings.enable_image_style_mapping = True
    mock_to_thread.return_value = b"img"

    db_session.add(DynamicList(list_name="image_styles", list_label="Image Styles"))
    db_session.add_all(
        [
            DynamicListItem(
                list_name="image_styles",
                item_value="Watercolor",
                item_label="Watercolor",
                is_active=True,
                sort_order=1,
                additional_config={"prompt_modifier": "soft watercolor painting"},
            ),
            DynamicListItem(
                list_name="image_styles",
                item_value="Comic",
                item_label="Comic",
                is_active=True,
                sort_order=10,
                additional_config={
                    "is_default": True,
                    "prompt_modifier": "bold line comic book, cel shading",
                },
            ),
        ]
    )
    db_session.commit()

    mock_image_handle = MagicMock()
    mock_prompt_handle = MagicMock()

    def open_side_effect(path, *args, **kwargs):
        if path == "/tmp/page.png":
            return mock_image_handle
        return mock_prompt_handle

    mock_open.side_effect = open_side_effect

    result = await generate_image_for_page(
        page_content="A cat on a sofa",
        style_reference="Default",
        db=db_session,
        user_id=1,
        story_id=2,
        page_number=1,
        image_save_path_on_disk="/tmp/page.png",
        image_path_for_db="images/u1/s1/p1.png",
    )

    assert result == "images/u1/s1/p1.png"
    args, _kwargs = mock_to_thread.call_args
    assert args[1].startswith(
        "A bold line comic book, cel shading style image of A cat on a sofa"
    )


@pytest.mark.asyncio
@patch("backend.ai_services.asyncio.to_thread")
@patch("backend.ai_services.os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
async def test_generate_character_reference_image_uses_prompt_modifier_when_enabled(
    mock_open,
    _mock_makedirs,
    mock_to_thread,
    db_session,
):
    ai_services._settings.enable_image_style_mapping = True
    mock_to_thread.return_value = b"fake_image_data"

    db_session.add(DynamicList(list_name="image_styles", list_label="Image Styles"))
    db_session.add(
        DynamicListItem(
            list_name="image_styles",
            item_value="Fantasy",
            item_label="Fantasy",
            is_active=True,
            sort_order=1,
            additional_config={
                "prompt_modifier": "lush fantasy storybook illustration"
            },
        )
    )
    db_session.commit()

    mock_character = MagicMock()
    mock_character.name = "Anya"
    mock_character.description = "A mysterious sorceress."
    mock_character.physical_appearance = "tall with silver hair"
    mock_character.clothing_style = "dark robes"
    mock_character.key_traits = "carries a glowing orb"
    mock_character.model_dump.return_value = {
        "name": "Anya",
        "description": "A mysterious sorceress.",
    }

    mock_story_input = MagicMock()
    mock_story_input.image_style = "Fantasy"

    mock_image_handle = MagicMock()
    mock_prompt_handle = MagicMock()

    def open_side_effect(path, *args, **kwargs):
        if path == "/tmp/Anya_ref_story_1.png":
            return mock_image_handle
        return mock_prompt_handle

    mock_open.side_effect = open_side_effect

    await generate_character_reference_image(
        character=mock_character,
        story_input=mock_story_input,
        db=db_session,
        user_id=1,
        story_id=1,
        image_save_path_on_disk="/tmp/Anya_ref_story_1.png",
        image_path_for_db="images/user_1/story_1/char_1.png",
    )

    args, _kwargs = mock_to_thread.call_args
    generated_prompt = args[1]
    assert generated_prompt.startswith(
        "A lush fantasy storybook illustration style full-body character sheet for Anya"
    )


@pytest.mark.asyncio
@patch("backend.ai_services.asyncio.to_thread")
@patch("backend.ai_services.os.makedirs")
@patch("builtins.open", new_callable=MagicMock)
async def test_generate_image_for_page_falls_back_to_default_map_when_dynamic_list_absent(
    mock_open,
    _mock_makedirs,
    mock_to_thread,
    db_session,
):
    ai_services._settings.enable_image_style_mapping = True
    mock_to_thread.return_value = b"img"

    mock_image_handle = MagicMock()
    mock_prompt_handle = MagicMock()

    def open_side_effect(path, *args, **kwargs):
        if path == "/tmp/fallback.png":
            return mock_image_handle
        return mock_prompt_handle

    mock_open.side_effect = open_side_effect

    business_style = "Photorealistic"
    result = await generate_image_for_page(
        page_content="A cat on a sofa",
        style_reference=business_style,
        db=db_session,
        user_id=1,
        story_id=2,
        page_number=1,
        image_save_path_on_disk="/tmp/fallback.png",
        image_path_for_db="images/u1/s1/p1.png",
    )

    assert result == "images/u1/s1/p1.png"
    args, _kwargs = mock_to_thread.call_args
    assert DEFAULT_IMAGE_STYLE_MAP[business_style] in args[1]
