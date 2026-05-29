import pytest
from dataclasses import dataclass, field
import re
from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from backend.pdf_generator import (
    PAGE_SIZE_MAP,
    _effective_page_settings,
    _resolve_page_size,
    create_story_pdf,
)
from backend.schemas import EDITOR_DEFAULTS
from datetime import datetime, UTC
from unittest.mock import patch


@dataclass
class MockPdfPage:
    """Minimal page object for direct PDF renderer tests."""

    page_number: int
    text: str
    image_path: str | None = None
    editor_state: dict | None = None


@dataclass
class MockPdfStory:
    """Minimal story object matching create_story_pdf attribute access."""

    id: int
    title: str
    cover_subtitle: str | None = None
    cover_author: str | None = None
    pages: list[MockPdfPage] = field(default_factory=list)
    editor_settings: dict | None = None


def _assert_valid_pdf_bytes(pdf_bytes: bytes, tmp_path, filename: str) -> None:
    """Assert the renderer returned a non-empty PDF byte stream."""

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    output_path = tmp_path / filename
    output_path.write_bytes(pdf_bytes)
    assert output_path.stat().st_size == len(pdf_bytes)


def _extract_media_box(pdf_bytes: bytes) -> tuple[float, float]:
    """Return the first page width and height from the rendered PDF bytes."""

    match = re.search(
        rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]",
        pdf_bytes,
    )
    assert match is not None
    return float(match.group(1)), float(match.group(2))


def test_export_pdf_success(client: TestClient, db_session, regular_user_auth_headers):
    # Arrange: create a story owned by the regular user
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="A Test Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch("backend.pdf_generator.create_story_pdf", return_value=b"%PDF-1.4\n..."):
        resp = client.get(f"/api/v1/stories/{story.id}/pdf",
                          headers=regular_user_auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"
        cd = resp.headers.get("content-disposition", "")
        assert f"filename={story.title}.pdf" in cd


def test_export_pdf_unauthorized_for_other_user(client: TestClient, db_session, regular_user_auth_headers, admin_auth_headers):
    # Arrange: create a story owned by admin
    admin_user = db_session.query(database.User).filter_by(
        username="admin@example.com").first()
    story = database.Story(
        title="Admin Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=admin_user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    # Regular user should not access admin's story
    resp = client.get(f"/api/v1/stories/{story.id}/pdf",
                      headers=regular_user_auth_headers)
    assert resp.status_code == 404


def test_export_pdf_filename_sanitization(client: TestClient, db_session, regular_user_auth_headers):
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="A/Weird*Title?",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch("backend.pdf_generator.create_story_pdf", return_value=b"%PDF-1.4\n..."):
        resp = client.get(f"/api/v1/stories/{story.id}/pdf",
                          headers=regular_user_auth_headers)
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        # Sanitized filename should not include illegal characters; fallback keeps alnum, space, -,_
        assert "AWeirdTitle.pdf" in cd or "story_" in cd


def test_export_pdf_preview_uses_inline_disposition(
    client: TestClient,
    db_session,
    regular_user_auth_headers,
):
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="Preview Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch("backend.pdf_generator.create_story_pdf", return_value=b"%PDF-1.4\n..."):
        resp = client.get(
            f"/api/v1/stories/{story.id}/pdf?disposition=inline",
            headers=regular_user_auth_headers,
        )

    assert resp.status_code == 200
    assert resp.headers.get("content-type") == "application/pdf"
    assert resp.headers.get("content-disposition", "").startswith(
        "inline; filename=Preview Story.pdf"
    )


def test_export_pdf_hides_internal_exception_message(
    client: TestClient,
    db_session,
    regular_user_auth_headers,
):
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="Leaky PDF Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch(
        "backend.pdf_generator.create_story_pdf",
        side_effect=RuntimeError(
            "internal renderer failure: /srv/private/template.ttf"),
    ):
        resp = client.get(
            f"/api/v1/stories/{story.id}/pdf",
            headers=regular_user_auth_headers,
        )

    assert resp.status_code == 500
    assert resp.json()["detail"] == "Failed to generate PDF"
    assert "internal renderer failure" not in resp.text
    assert "/srv/private/template.ttf" not in resp.text


def test_create_story_pdf_basic_generation_returns_pdf_bytes(tmp_path) -> None:
    story = MockPdfStory(
        id=101,
        title="Minimal Story",
        pages=[MockPdfPage(page_number=1, text="A short first page.")],
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "basic-story.pdf")


def test_create_story_pdf_multi_page_story_returns_pdf_bytes(tmp_path) -> None:
    story = MockPdfStory(
        id=102,
        title="Three Pages",
        pages=[
            MockPdfPage(page_number=1, text="Page one."),
            MockPdfPage(page_number=2, text="Page two."),
            MockPdfPage(page_number=3, text="Page three."),
        ],
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "multi-page-story.pdf")


def test_create_story_pdf_sorts_pages_by_page_number_before_rendering() -> None:
    story = MockPdfStory(
        id=120,
        title="Sorted Render",
        pages=[
            MockPdfPage(page_number=2, text="Second."),
            MockPdfPage(page_number=0, text="Cover."),
            MockPdfPage(page_number=1, text="First."),
        ],
    )
    rendered_text = []

    with patch("backend.pdf_generator._draw_placeholder_background"), patch(
        "backend.pdf_generator._draw_image_cover"
    ), patch(
        "backend.pdf_generator._draw_title_page_overlay",
        side_effect=lambda *_args, **_kwargs: rendered_text.append("Cover."),
    ), patch(
        "backend.pdf_generator._draw_text_overlay",
        side_effect=lambda _pdf, text, *
            _args, **_kwargs: rendered_text.append(text),
    ):
        create_story_pdf(story)

    assert rendered_text == ["Cover.", "First.", "Second."]


def test_create_story_pdf_missing_image_falls_back_to_placeholder(tmp_path) -> None:
    story = MockPdfStory(
        id=103,
        title="Missing Image Story",
        pages=[
            MockPdfPage(
                page_number=1,
                text="This page has a missing image.",
                image_path="images/does-not-exist.png",
            )
        ],
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "missing-image-story.pdf")


def test_create_story_pdf_escaped_image_path_falls_back_to_placeholder(tmp_path) -> None:
    story = MockPdfStory(
        id=106,
        title="Escaped Image Story",
        pages=[
            MockPdfPage(
                page_number=1,
                text="This page has an invalid escaped image path.",
                image_path="../outside.png",
            )
        ],
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "escaped-image-story.pdf")


def test_create_story_pdf_honors_text_position_overrides(tmp_path) -> None:
    story = MockPdfStory(
        id=104,
        title="Override Positions",
        pages=[
            MockPdfPage(
                page_number=1,
                text="Top text.",
                editor_state={"text_position": "top"},
            ),
            MockPdfPage(
                page_number=2,
                text="Bottom text.",
                editor_state={"text_position": "bottom"},
            ),
        ],
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "text-position-story.pdf")


def test_create_story_pdf_honors_font_family_override(tmp_path) -> None:
    story = MockPdfStory(
        id=105,
        title="Classic Font Story",
        pages=[MockPdfPage(page_number=1, text="Font override test.")],
        editor_settings={
            **EDITOR_DEFAULTS,
            "font_family": "classic",
        },
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "font-family-story.pdf")


def test_create_story_pdf_uses_explicit_text_alignment(tmp_path) -> None:
    story = MockPdfStory(
        id=111,
        title="Right Align Story",
        pages=[MockPdfPage(page_number=1, text="Right aligned body text.")],
        editor_settings={
            **EDITOR_DEFAULTS,
            "text_alignment": "right",
        },
    )

    with patch(
        "reportlab.pdfgen.canvas.Canvas.drawRightString",
        autospec=True,
    ) as draw_right_string:
        pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "text-alignment-story.pdf")
    drawn_text = [call.args[3] for call in draw_right_string.call_args_list]
    assert "Right aligned body text." in drawn_text


def test_create_story_pdf_soft_shadow_treatment_draws_shadow_pass(tmp_path) -> None:
    story = MockPdfStory(
        id=112,
        title="Shadow Story",
        pages=[MockPdfPage(page_number=1, text="Shadowed body text.")],
        editor_settings={
            **EDITOR_DEFAULTS,
            "text_alignment": "left",
            "readability_treatment": "Soft shadow",
        },
    )

    with patch("reportlab.pdfgen.canvas.Canvas.drawString", autospec=True) as draw_string:
        pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "soft-shadow-story.pdf")
    drawn_text = [call.args[3] for call in draw_string.call_args_list]
    assert drawn_text.count("Shadowed body text.") == 2


def test_create_story_pdf_supports_split_layout_modes(tmp_path) -> None:
    story = MockPdfStory(
        id=109,
        title="Split Layout Story",
        pages=[MockPdfPage(page_number=1, text="Split layout text.")],
        editor_settings={
            **EDITOR_DEFAULTS,
            "layout_mode": "horizontal-split",
        },
    )

    horizontal_pdf = create_story_pdf(story)
    _assert_valid_pdf_bytes(horizontal_pdf, tmp_path,
                            "horizontal-split-story.pdf")

    story.editor_settings = {
        **EDITOR_DEFAULTS,
        "layout_mode": "vertical-split",
    }
    vertical_pdf = create_story_pdf(story)

    _assert_valid_pdf_bytes(vertical_pdf, tmp_path, "vertical-split-story.pdf")


def test_create_story_pdf_uses_configured_a4_page_size(tmp_path) -> None:
    story = MockPdfStory(
        id=106,
        title="A4 Story",
        pages=[MockPdfPage(page_number=1, text="A4 page size test.")],
        editor_settings={
            **EDITOR_DEFAULTS,
            "page_format": "a4",
        },
    )

    pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "a4-story.pdf")
    width, height = _extract_media_box(pdf_bytes)
    expected_width, expected_height = PAGE_SIZE_MAP["a4"]
    assert width == pytest.approx(expected_width, abs=0.2)
    assert height == pytest.approx(expected_height, abs=0.2)


def test_create_story_pdf_renders_cover_subtitle_and_author(tmp_path) -> None:
    story = MockPdfStory(
        id=110,
        title="Cover Metadata Story",
        cover_subtitle="A quiet adventure under moonlight",
        cover_author="Lee Baker",
        pages=[MockPdfPage(page_number=0, text="Cover Metadata Story")],
    )

    with patch(
        "reportlab.pdfgen.canvas.Canvas.drawCentredString",
        autospec=True,
    ) as draw_string:
        pdf_bytes = create_story_pdf(story)

    _assert_valid_pdf_bytes(pdf_bytes, tmp_path, "cover-metadata-story.pdf")
    drawn_text = [call.args[3] for call in draw_string.call_args_list]
    assert "A quiet adventure under moonlight" in drawn_text
    assert "By Lee Baker" in drawn_text


def test_resolve_page_size_defaults_to_letter_and_supports_square_storybook() -> None:
    default_story = MockPdfStory(id=107, title="Default Format")
    square_story = MockPdfStory(
        id=108,
        title="Square Format",
        editor_settings={
            **EDITOR_DEFAULTS,
            "page_format": "square-storybook",
        },
    )

    assert _resolve_page_size(default_story) == PAGE_SIZE_MAP["letter"]
    assert _resolve_page_size(
        square_story) == PAGE_SIZE_MAP["square-storybook"]


def test_effective_page_settings_prefers_page_font_family_override() -> None:
    story = MockPdfStory(
        id=106,
        title="Per Page Font Story",
        editor_settings={
            **EDITOR_DEFAULTS,
            "font_family": "classic",
        },
    )
    page = MockPdfPage(
        page_number=1,
        text="Per-page font override.",
        editor_state={"font_family": "handwritten"},
    )

    settings = _effective_page_settings(story, page)

    assert settings["font_family"] == "handwritten"
    assert settings["layout_mode"] == "full-page-overlay"


def test_effective_page_settings_prefers_page_alignment_and_opacity_override() -> None:
    story = MockPdfStory(
        id=113,
        title="Per Page Alignment Story",
        editor_settings={
            **EDITOR_DEFAULTS,
            "text_alignment": "right",
            "text_box_opacity": 0.65,
        },
    )
    page = MockPdfPage(
        page_number=1,
        text="Per-page alignment override.",
        editor_state={"text_alignment": "left", "text_box_opacity": 0.3},
    )

    settings = _effective_page_settings(story, page)

    assert settings["text_alignment"] == "left"
    assert settings["text_box_opacity"] == 0.3
