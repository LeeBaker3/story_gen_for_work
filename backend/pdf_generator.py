import io
import os
from typing import Any, Dict, List, Tuple

from reportlab.lib.pagesizes import A4, landscape, letter, portrait
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .database import Story as StoryModel
from .logging_config import app_logger, error_logger
from .schemas import EDITOR_DEFAULTS

PAGE_MARGIN = 36
SQUARE_STORYBOOK = (612.0, 612.0)
PAGE_SIZE_MAP = {
    "letter": letter,
    "us-letter": letter,
    "us_letter": letter,
    "a4": A4,
    "portrait": portrait(letter),
    "landscape": landscape(letter),
    "square-storybook": SQUARE_STORYBOOK,
    "square_storybook": SQUARE_STORYBOOK,
    "square storybook": SQUARE_STORYBOOK,
}
_OLD_POSITION_MAP = {
    "top": "top-center",
    "bottom": "bottom-center",
    "left": "middle-left",
    "right": "middle-right",
    "center": "middle-center",
}
VALID_TEXT_POSITIONS = {
    "top-left", "top-center", "top-right",
    "middle-left", "middle-center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
    "top", "bottom", "left", "right", "center",
}
FONT_FAMILY_MAP = {
    "storybook": "Helvetica-Bold",
    "classic": "Times-Roman",
    "modern": "Helvetica",
    "handwritten": "Courier",
    "dyslexia-friendly": "Helvetica",
    "large print": "Helvetica-Bold",
}


def _resolve_story_editor_settings(story_data: StoryModel) -> Dict[str, Any]:
    """Return normalized document defaults for PDF rendering."""

    settings = dict(EDITOR_DEFAULTS)
    raw = getattr(story_data, "editor_settings", None)
    if isinstance(raw, dict):
        settings.update(raw)
    return settings


def _resolve_page_editor_state(page: Any) -> Dict[str, Any]:
    """Return normalized page-level editor state."""

    state: Dict[str, Any] = {}
    raw = getattr(page, "editor_state", None)
    if isinstance(raw, dict):
        state.update(raw)
    if not state.get("original_text"):
        state["original_text"] = getattr(page, "text", None)
    if not state.get("original_image_path"):
        state["original_image_path"] = getattr(page, "image_path", None)
    return state


def _effective_page_settings(story_data: StoryModel, page: Any) -> Dict[str, Any]:
    """Merge story defaults with per-page overrides."""

    settings = _resolve_story_editor_settings(story_data)
    state = _resolve_page_editor_state(page)
    for key in ("text_position", "font_family", "font_size", "font_color"):
        value = state.get(key)
        if value not in (None, ""):
            settings[key] = value
    return settings


def _resolve_page_size(story_data: StoryModel) -> Tuple[float, float]:
    """Return the configured PDF page size for the story."""

    settings = _resolve_story_editor_settings(story_data)
    page_format = str(settings.get("page_format") or "letter").strip().lower()
    return PAGE_SIZE_MAP.get(page_format, letter)


def _safe_hex_color(value: Any) -> HexColor:
    """Return a valid ReportLab color from a hex input."""

    try:
        return HexColor(str(value or "#ffffff"))
    except Exception:
        return HexColor("#ffffff")


def _resolve_font_name(font_family: Any) -> str:
    """Map a friendly font family token to a built-in PDF font."""

    key = str(font_family or "storybook").strip().lower()
    return FONT_FAMILY_MAP.get(key, "Helvetica-Bold")


def _resolve_image_path(image_path: str) -> str:
    """Resolve and canonicalize an image path, ensuring it stays within data/."""

    project_root = os.path.realpath(os.path.join(
        os.path.dirname(__file__), os.pardir))
    data_root = os.path.join(project_root, "data")
    full_path = os.path.realpath(os.path.join(data_root, image_path))
    if not full_path.startswith(data_root + os.sep) and full_path != data_root:
        raise ValueError(f"Image path escapes data directory: {image_path!r}")
    return full_path


def _text_box_geometry(
    text_position: str,
    page_size: Tuple[float, float],
) -> Tuple[float, float, float, float]:
    """Return x, y, width, height for the page overlay text box.

    Accepts 9-position grid values (v-h format) or legacy 5-value format.
    Legacy values are mapped: top→top-center, bottom→bottom-center,
    left→middle-left, right→middle-right, center→middle-center.
    """

    page_width, page_height = page_size

    position = str(text_position or "bottom-center").strip().lower()
    position = _OLD_POSITION_MAP.get(position, position)

    parts = position.split("-", 1)
    vertical = parts[0] if len(parts) >= 1 else "bottom"
    horizontal = parts[1] if len(parts) == 2 else "center"

    if vertical not in {"top", "middle", "bottom"}:
        vertical = "bottom"
    if horizontal not in {"left", "center", "right"}:
        horizontal = "center"

    if vertical == "top":
        box_height = page_height * 0.22
        box_y = page_height - PAGE_MARGIN - box_height
    elif vertical == "middle":
        box_height = page_height * 0.34
        box_y = (page_height - box_height) / 2.0
    else:
        box_height = page_height * 0.22
        box_y = PAGE_MARGIN

    if horizontal == "left":
        box_width = page_width * 0.48
        box_x = PAGE_MARGIN
    elif horizontal == "right":
        box_width = page_width * 0.48
        box_x = page_width - PAGE_MARGIN - box_width
    else:
        if vertical == "middle":
            box_width = page_width * 0.65
        else:
            box_width = page_width - (2 * PAGE_MARGIN)
        box_x = (page_width - box_width) / 2.0

    return box_x, box_y, box_width, box_height


def _draw_full_page_image(
    pdf: canvas.Canvas,
    full_image_path: str,
    page_size: Tuple[float, float],
) -> None:
    """Draw an image full-bleed, cropped to fill the entire page."""

    page_width, page_height = page_size

    image = ImageReader(full_image_path)
    image_width, image_height = image.getSize()
    if not image_width or not image_height:
        raise ValueError("Image has invalid dimensions")

    scale = max(page_width / image_width, page_height / image_height)
    draw_width = image_width * scale
    draw_height = image_height * scale
    draw_x = (page_width - draw_width) / 2.0
    draw_y = (page_height - draw_height) / 2.0
    pdf.drawImage(
        image,
        draw_x,
        draw_y,
        width=draw_width,
        height=draw_height,
        preserveAspectRatio=True,
        mask="auto",
    )


def _draw_placeholder_background(
    pdf: canvas.Canvas,
    page_size: Tuple[float, float],
) -> None:
    """Draw a fallback page background when an image is unavailable."""

    page_width, page_height = page_size

    pdf.saveState()
    pdf.setFillColor(HexColor("#202634"))
    pdf.rect(0, 0, page_width, page_height, stroke=0, fill=1)
    pdf.restoreState()


def _draw_text_overlay(
    pdf: canvas.Canvas,
    text: str,
    settings: Dict[str, Any],
    page_size: Tuple[float, float],
    is_title_page: bool = False,
) -> None:
    """Draw a readable overlay text box using the current editor settings."""

    box_x, box_y, box_width, box_height = _text_box_geometry(
        settings.get("text_position", "bottom"),
        page_size,
    )
    opacity = settings.get("text_box_opacity", 0.6)
    try:
        opacity = max(0.0, min(1.0, float(opacity)))
    except Exception:
        opacity = 0.6

    font_name = _resolve_font_name(settings.get("font_family"))
    try:
        font_size = int(settings.get("font_size")
                        or EDITOR_DEFAULTS["font_size"])
    except Exception:
        font_size = EDITOR_DEFAULTS["font_size"]
    if is_title_page:
        font_size = max(font_size + 8, 34)

    max_text_width = box_width - 24
    max_text_height = box_height - 24
    line_height = font_size * 1.25
    wrapped_lines = simpleSplit(
        text or "", font_name, font_size, max_text_width)

    while wrapped_lines and (len(wrapped_lines) * line_height) > max_text_height and font_size > 14:
        font_size -= 2
        line_height = font_size * 1.25
        wrapped_lines = simpleSplit(
            text or "", font_name, font_size, max_text_width)

    pdf.saveState()
    pdf.setFillColor(Color(0, 0, 0, alpha=opacity))
    pdf.roundRect(box_x, box_y, box_width, box_height, 10, stroke=0, fill=1)
    pdf.restoreState()

    pdf.saveState()
    pdf.setFillColor(_safe_hex_color(settings.get("font_color")))
    pdf.setFont(font_name, font_size)
    content_height = len(wrapped_lines) * line_height
    text_y = box_y + box_height - 16 - \
        ((box_height - 24 - content_height) / 2.0)
    for line in wrapped_lines:
        if is_title_page:
            line_width = stringWidth(line, font_name, font_size)
            text_x = box_x + (box_width - line_width) / 2.0
        else:
            text_x = box_x + 12
        pdf.drawString(text_x, text_y, line)
        text_y -= line_height
    pdf.restoreState()


def create_story_pdf(story_data: StoryModel) -> bytes:
    """Render the edited story into a PDF using persisted editor settings."""

    app_logger.info(
        "Starting editor-aware PDF generation for story: %s (ID: %s)",
        story_data.title,
        story_data.id,
    )
    buffer = io.BytesIO()
    page_size = _resolve_page_size(story_data)
    pdf = canvas.Canvas(buffer, pagesize=page_size)

    sorted_pages: List[Any] = sorted(
        story_data.pages or [], key=lambda page: int(getattr(page, "page_number", 0))
    )
    if not sorted_pages:
        _draw_placeholder_background(pdf, page_size)
        _draw_text_overlay(
            pdf,
            getattr(story_data, "title", "Untitled Story"),
            _resolve_story_editor_settings(story_data),
            page_size,
            is_title_page=True,
        )
        pdf.showPage()
    else:
        for page in sorted_pages:
            page_number = int(getattr(page, "page_number", 0))
            full_image_path = None
            image_path = getattr(page, "image_path", None)
            if image_path:
                try:
                    full_image_path = _resolve_image_path(image_path)
                except ValueError:
                    full_image_path = None

            try:
                if full_image_path and os.path.exists(full_image_path):
                    _draw_full_page_image(pdf, full_image_path, page_size)
                else:
                    _draw_placeholder_background(pdf, page_size)
            except Exception as exc:
                error_logger.error(
                    "Failed to draw image for story %s page %s: %s",
                    story_data.id,
                    page_number,
                    exc,
                    exc_info=True,
                )
                _draw_placeholder_background(pdf, page_size)

            text_value = getattr(page, "text", None) or getattr(
                story_data, "title", "")
            page_settings = _effective_page_settings(story_data, page)
            _draw_text_overlay(
                pdf,
                text_value,
                page_settings,
                page_size,
                is_title_page=(page_number == 0),
            )
            pdf.showPage()

    pdf.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# Example usage (for testing this file directly - requires a mock StoryModel object)
if __name__ == '__main__':
    # This is a mock setup for direct testing.
    # In the actual app, StoryModel will come from SQLAlchemy.
    class MockPage:
        def __init__(self, page_number, text, image_path):
            self.page_number = page_number
            self.text = text
            self.image_path = image_path

    class MockStory:
        def __init__(self, id, title, pages):
            self.id = id
            self.title = title
            self.pages = pages

    # Create a dummy image for testing if it doesn't exist
    # This test assumes it's run from the 'backend' directory.
    # For the actual app, image paths are relative to the workspace root.

    # Adjust path for test image creation
    test_image_dir = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), "data", "images", "test")
    os.makedirs(test_image_dir, exist_ok=True)
    test_image_path = os.path.join(test_image_dir, "sample_test_image.png")

    if not os.path.exists(test_image_path):
        try:
            from PIL import Image as PILImage
            img = PILImage.new('RGB', (100, 100), color='red')
            img.save(test_image_path)
            print(f"Created dummy image at {test_image_path}")
        except ImportError:
            print(
                "Pillow not installed, cannot create dummy image for testing pdf_generator.py directly.")
            # Create an empty file as a placeholder if Pillow is not available
            open(test_image_path, 'a').close()
            print(f"Created empty placeholder file at {test_image_path}")
        except Exception as e:
            print(f"Error creating dummy image: {e}")

    mock_story_data = MockStory(
        id=1,
        title="The Adventures of Sir Reginald and Sparky",
        pages=[
            MockPage(
                1, "Once upon a time, Sir Reginald, a brave knight, met Sparky, a friendly dragon.", test_image_path),
            # Test missing image
            MockPage(
                2, "They decided to go on an adventure to find the legendary Golden Acorn.", None),
            MockPage(
                3, "After many trials, they found it and shared its magic with the kingdom!", test_image_path)
        ]
    )

    print(
        f"Attempting to generate PDF for mock story ID: {mock_story_data.id}...")
    try:
        pdf_output_path = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), "data", "test_story.pdf")
        pdf_bytes = create_story_pdf(mock_story_data)
        with open(pdf_output_path, 'wb') as f:
            f.write(pdf_bytes)
        print(
            f"Mock PDF generated successfully: {os.path.abspath(pdf_output_path)}")
    except Exception as e:
        print(f"Error during PDF generation test: {e}")
