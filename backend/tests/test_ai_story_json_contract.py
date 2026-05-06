"""Tests for the must-not-break AI story JSON contract.

These tests are intentionally pure (no OpenAI calls). They validate the structure
we expect from `backend.ai_services.generate_story_from_chatgpt()` regardless of
whether the backend uses Chat Completions or the Responses API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest


def assert_ai_story_json_contract(story: Dict[str, Any]) -> None:
    """Assert the "must-not-break" story JSON contract.

    Parameters
    ----------
    story:
        Parsed JSON object representing the AI story.

    Raises
    ------
    AssertionError
        If the object violates the contract.

    Notes
    -----
    Contract requirements (high-level):
    - Top-level keys: `Title` (str), `Pages` (list)
    - Title page is first: `Pages[0].Page_number == "Title"`
    - Title page `Text` equals top-level `Title`
    - Each page object includes keys:
      `Page_number`, `Text`, `Image_description`, `Characters_in_scene`
    - `Characters_in_scene` is a list of strings (may be empty)
    - `Image_description` is either a non-empty string or null depending on
      the word-to-picture ratio rules (Title page must have a non-empty string).
    """

    assert isinstance(story, dict), "Story must be a JSON object (dict)."

    assert "Title" in story, "Story must include top-level 'Title'."
    assert "Pages" in story, "Story must include top-level 'Pages'."

    title = story["Title"]
    pages = story["Pages"]

    assert isinstance(title, str), "Top-level 'Title' must be a string."
    assert title.strip(), "Top-level 'Title' must be non-empty."

    assert isinstance(pages, list), "Top-level 'Pages' must be a list."
    assert len(pages) >= 1, "'Pages' must contain at least the Title page."

    # Validate Title page invariants.
    title_page = pages[0]
    _assert_page_shape(title_page)

    assert (
        title_page["Page_number"] == "Title"
    ), "First page must have Page_number == 'Title'."

    assert isinstance(
        title_page["Text"], str
    ), "Title page 'Text' must be a string."
    assert (
        title_page["Text"] == title
    ), "Title page 'Text' must exactly match top-level 'Title'."

    assert isinstance(
        title_page["Image_description"], str
    ), "Title page must include a non-empty string 'Image_description'."
    assert title_page["Image_description"].strip(), (
        "Title page 'Image_description' must be non-empty (cover prompt)."
    )

    # Validate remaining pages.
    for idx, page in enumerate(pages[1:], start=1):
        _assert_page_shape(page, page_index=idx)

        page_number = page["Page_number"]
        assert _is_valid_content_page_number(page_number), (
            "Content page 'Page_number' must be an integer or an integer-like "
            "string (e.g., 1, 2, 3)."
        )

        assert isinstance(page["Text"], str), "Page 'Text' must be a string."
        assert page["Text"].strip(), "Page 'Text' must be non-empty."

        image_description = page["Image_description"]
        assert (image_description is None) or isinstance(image_description, str), (
            "Page 'Image_description' must be a string or null."
        )
        if isinstance(image_description, str):
            assert image_description.strip(), (
                "If provided, 'Image_description' must be non-empty."
            )

        characters_in_scene = page["Characters_in_scene"]
        assert isinstance(
            characters_in_scene, list
        ), "'Characters_in_scene' must be a list."
        assert all(isinstance(n, str) for n in characters_in_scene), (
            "All items in 'Characters_in_scene' must be strings."
        )


def _assert_page_shape(page: Any, page_index: Optional[int] = None) -> None:
    """Assert required keys exist and basic types are plausible."""

    assert isinstance(page, dict), _prefix(
        page_index) + "Page must be an object."

    required_keys = {
        "Page_number",
        "Text",
        "Image_description",
        "Characters_in_scene",
    }

    missing = required_keys.difference(page.keys())
    assert not missing, _prefix(page_index) + \
        f"Missing keys: {sorted(missing)}"


def _is_valid_content_page_number(value: Any) -> bool:
    """Return True if value is an int >= 1 or a numeric string representing that."""

    if isinstance(value, int):
        return value >= 1

    if isinstance(value, str):
        stripped = value.strip()
        return stripped.isdigit() and int(stripped) >= 1

    return False


def _prefix(page_index: Optional[int]) -> str:
    """Create a stable assertion prefix for page errors."""

    if page_index is None:
        return ""
    return f"Pages[{page_index}]: "


def test_ai_story_json_contract_accepts_known_good_example() -> None:
    """Contract test: a representative story object passes validation."""

    story = {
        "Title": "The Lantern in the Snow",
        "Pages": [
            {
                "Page_number": "Title",
                "Text": "The Lantern in the Snow",
                "Image_description": (
                    "A captivating cover illustration: a warm lantern glowing in "
                    "falling snow near a cozy cabin, inviting mood, fantasy art style"
                ),
                "Characters_in_scene": ["Mira"],
            },
            {
                "Page_number": 1,
                "Text": "Mira stepped into the quiet forest, listening for the wind.",
                "Image_description": (
                    "Mira walking through a snowy forest trail, lantern light "
                    "reflecting off pine branches, fantasy art style"
                ),
                "Characters_in_scene": ["Mira"],
            },
        ],
    }

    assert_ai_story_json_contract(story)


@pytest.mark.parametrize(
    "bad_story, expected_error",
    [
        ({}, "Title"),
        ({"Title": "X", "Pages": []}, "Title page"),
        (
            {
                "Title": "X",
                "Pages": [
                    {
                        "Page_number": "Title",
                        "Text": "Y",
                        "Image_description": "cover",
                        "Characters_in_scene": [],
                    }
                ],
            },
            "match",
        ),
    ],
)
def test_ai_story_json_contract_rejects_invalid_examples(
    bad_story: Dict[str, Any], expected_error: str
) -> None:
    """Contract test: clearly invalid objects fail with helpful messages."""

    with pytest.raises(AssertionError) as excinfo:
        assert_ai_story_json_contract(bad_story)

    assert expected_error.lower() in str(excinfo.value).lower()
