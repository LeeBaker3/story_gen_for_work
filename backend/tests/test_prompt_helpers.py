"""Regression tests for shared prompt helper wiring."""

from backend import public_router, story_generation_service


def test_story_generation_service_text_position_guidance_handles_top_and_bottom():
    """The shared helper should return non-empty guidance for key positions."""

    for text_position in ("top", "bottom"):
        guidance = story_generation_service._text_position_guidance(
            text_position
        )
        assert callable(story_generation_service._text_position_guidance)
        assert isinstance(guidance, str)
        assert guidance.strip()


def test_story_generation_service_text_position_guidance_varies_by_layout_mode():
    """Full-page overlay guidance should be softer than split-layout guidance."""

    overlay_guidance = story_generation_service._text_position_guidance(
        "top",
        "full-page-overlay",
    )
    split_guidance = story_generation_service._text_position_guidance(
        "top",
        "horizontal-split",
    )

    assert "top area" in overlay_guidance.lower()
    assert "less visually busy" in overlay_guidance.lower()
    assert "tonally supportive" in overlay_guidance.lower()
    assert "readable visual space" not in overlay_guidance.lower()

    assert "top area" in split_guidance.lower()
    assert "readable visual space" in split_guidance.lower()


def test_public_router_does_not_define_text_position_guidance_locally():
    """The public router should rely on the shared helper implementation."""

    assert "_text_position_guidance" not in public_router.__dict__
