from unittest.mock import patch

import pytest

from backend.database import DynamicList, DynamicListItem, Story, User


def _story_payload(**overrides):
    """Build a minimal valid story payload for endpoint tests."""

    payload = {
        "title": "Dynamic List Story",
        "genre": "Fantasy",
        "story_outline": "A short outline for validation testing.",
        "main_characters": [{"name": "Hero"}],
        "num_pages": 2,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)",
    }
    payload.update(overrides)
    return payload


def _ensure_dynamic_list_item(
    db_session,
    list_name: str,
    item_value: str,
    *,
    is_active: bool,
    sort_order: int = 999,
) -> None:
    """Ensure a dynamic-list item exists with the requested active state."""

    parent = db_session.query(DynamicList).filter_by(
        list_name=list_name).first()
    if parent is None:
        db_session.add(
            DynamicList(list_name=list_name,
                        list_label=list_name.replace("_", " "))
        )
        db_session.commit()

    item = (
        db_session.query(DynamicListItem)
        .filter_by(list_name=list_name, item_value=item_value)
        .first()
    )
    if item is None:
        item = DynamicListItem(
            list_name=list_name,
            item_value=item_value,
            item_label=item_value,
            is_active=is_active,
            sort_order=sort_order,
        )
        db_session.add(item)
    else:
        item.is_active = is_active
        item.item_label = item_value
        item.sort_order = sort_order

    db_session.commit()


def _seed_story_validation_defaults(db_session) -> None:
    """Seed the baseline active items needed for story metadata validation."""

    _ensure_dynamic_list_item(
        db_session,
        "genres",
        "Fantasy",
        is_active=True,
        sort_order=1,
    )
    _ensure_dynamic_list_item(
        db_session,
        "image_styles",
        "Default",
        is_active=True,
        sort_order=1,
    )
    _ensure_dynamic_list_item(
        db_session,
        "word_to_picture_ratio",
        "One image per page",
        is_active=True,
        sort_order=1,
    )
    _ensure_dynamic_list_item(
        db_session,
        "text_density",
        "Concise (~30-50 words)",
        is_active=True,
        sort_order=1,
    )


def test_create_story_accepts_admin_added_active_dynamic_list_values(
    client,
    db_session,
    regular_user_auth_headers,
):
    """Story creation should accept active admin-added values for all four fields."""

    _seed_story_validation_defaults(db_session)
    custom_values = {
        "genre": "Solarpunk",
        "image_style": "Paper Cut Collage",
        "word_to_picture_ratio": "One image per spread",
        "text_density": "Extended (~150-200 words)",
    }
    _ensure_dynamic_list_item(
        db_session,
        "genres",
        custom_values["genre"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "image_styles",
        custom_values["image_style"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "word_to_picture_ratio",
        custom_values["word_to_picture_ratio"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "text_density",
        custom_values["text_density"],
        is_active=True,
    )

    with patch(
        "backend.public_router.story_generation_service.generate_story_as_background_task"
    ):
        response = client.post(
            "/api/v1/stories/",
            json=_story_payload(**custom_values),
            headers=regular_user_auth_headers,
        )

    assert response.status_code == 202
    story_id = response.json()["story_id"]
    created_story = db_session.query(Story).filter(Story.id == story_id).one()
    assert created_story.genre == custom_values["genre"]
    assert created_story.image_style == custom_values["image_style"]
    assert (
        created_story.word_to_picture_ratio
        == custom_values["word_to_picture_ratio"]
    )
    assert created_story.text_density == custom_values["text_density"]


def test_create_story_draft_accepts_admin_added_active_dynamic_list_values(
    client,
    db_session,
    regular_user_auth_headers,
):
    """Draft creation should accept active admin-added values for all four fields."""

    _seed_story_validation_defaults(db_session)
    custom_values = {
        "genre": "Hopepunk",
        "image_style": "Ink Wash",
        "word_to_picture_ratio": "One image per chapter",
        "text_density": "Light (~20-30 words)",
    }
    _ensure_dynamic_list_item(
        db_session,
        "genres",
        custom_values["genre"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "image_styles",
        custom_values["image_style"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "word_to_picture_ratio",
        custom_values["word_to_picture_ratio"],
        is_active=True,
    )
    _ensure_dynamic_list_item(
        db_session,
        "text_density",
        custom_values["text_density"],
        is_active=True,
    )

    response = client.post(
        "/stories/drafts/",
        json=_story_payload(title="Dynamic Draft", **custom_values),
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["genre"] == custom_values["genre"]
    assert data["image_style"] == custom_values["image_style"]
    assert data["word_to_picture_ratio"] == custom_values["word_to_picture_ratio"]
    assert data["text_density"] == custom_values["text_density"]


@pytest.mark.parametrize(
    ("path", "field_name", "field_value", "is_active"),
    [
        ("/api/v1/stories/", "image_style", "Not A Real Style", None),
        ("/stories/drafts/", "genre", "Retired Genre", False),
    ],
)
def test_story_inputs_reject_invalid_or_inactive_dynamic_list_values(
    client,
    db_session,
    regular_user_auth_headers,
    path,
    field_name,
    field_value,
    is_active,
):
    """Create and draft endpoints should reject unknown or inactive values."""

    _seed_story_validation_defaults(db_session)
    field_to_list_name = {
        "genre": "genres",
        "image_style": "image_styles",
        "word_to_picture_ratio": "word_to_picture_ratio",
        "text_density": "text_density",
    }
    if is_active is not None:
        _ensure_dynamic_list_item(
            db_session,
            field_to_list_name[field_name],
            field_value,
            is_active=is_active,
        )

    response = client.post(
        path,
        json=_story_payload(
            title=f"Rejected {field_name}", **{field_name: field_value}),
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list)
    assert detail[0]["loc"] == ["body", field_name]
    assert field_value in detail[0]["msg"]
