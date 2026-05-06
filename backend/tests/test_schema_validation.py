"""Regression tests for API-layer schema validation."""

from unittest.mock import patch


def _story_payload(title: str, story_outline: str) -> dict:
    """Build a minimal valid story creation payload for API tests."""

    return {
        "title": title,
        "genre": "Fantasy",
        "story_outline": story_outline,
        "main_characters": [{"name": "Valid Hero"}],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)",
    }


def test_create_story_rejects_title_longer_than_200_characters(
    client,
    regular_user_auth_headers,
):
    """The story endpoint should reject titles that exceed the schema limit."""

    response = client.post(
        "/api/v1/stories/",
        json=_story_payload("T" * 201, "A valid outline."),
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 422


def test_create_story_rejects_story_outline_longer_than_5000_characters(
    client,
    regular_user_auth_headers,
):
    """The story endpoint should reject outlines that exceed the schema limit."""

    response = client.post(
        "/api/v1/stories/",
        json=_story_payload("Valid Title", "O" * 5001),
        headers=regular_user_auth_headers,
    )

    assert response.status_code == 422


def test_create_story_accepts_title_at_exact_200_character_limit(
    client,
    regular_user_auth_headers,
):
    """The story endpoint should accept a title at the exact schema limit."""

    with patch(
        "backend.public_router.story_generation_service"
        ".generate_story_as_background_task",
        lambda *args, **kwargs: None,
    ):
        response = client.post(
            "/api/v1/stories/",
            json=_story_payload("T" * 200, "A valid outline."),
            headers=regular_user_auth_headers,
        )

    assert response.status_code in {200, 202}, response.text
