from __future__ import annotations

from typing import Dict


# Default mapping from business ImageStyle values to OpenAI-friendly prompt modifiers.
# Keys should match Story.image_style values provided in requests or dynamic list items.
DEFAULT_IMAGE_STYLE_MAP: Dict[str, str] = {
    # Common examples
    "Default": "illustrated children’s book",
    "Photorealistic": "highly detailed photorealistic",
    "Watercolor": "soft watercolor painting",
    "Pencil Sketch": "clean pencil sketch with linework",
    "Comic": "bold line comic book, cel shading",
    "Fantasy": "epic fantasy concept art",
    "Sci-Fi": "cinematic sci‑fi concept art, volumetric lighting",
}


def map_style(business_style: str | None, mapping: Dict[str, str] | None = None) -> str | None:
    """Return a prompt modifier for the given business style, if known.

    If the style is unknown or None, returns None to preserve the original input.
    """
    if not business_style:
        return None
    m = mapping or DEFAULT_IMAGE_STYLE_MAP
    return m.get(str(business_style).strip(), None)


OPENAI_IMAGE_STYLE_LIST_NAME = "image_style_mappings"
_ALLOWED_OPENAI_STYLES = {"vivid", "natural"}


def get_openai_image_style(
    *,
    db,
    business_style: str | None,
    default: str = "vivid",
) -> str:
    """Resolve the OpenAI `style` parameter from a DynamicList.

    The DynamicListItem is expected to have:
    - list_name: "image_style_mappings"
    - item_value: the application's ImageStyle value (string)
    - additional_config: {"openai_style": "vivid"|"natural"}

    If no mapping exists (or it's invalid), returns the provided default.

    Parameters:
        db: SQLAlchemy Session.
        business_style: The app's ImageStyle value.
        default: Fallback OpenAI style.

    Returns:
        str: "vivid" or "natural" (or the provided default).
    """

    fallback = str(default).strip().lower() or "vivid"
    if fallback not in _ALLOWED_OPENAI_STYLES:
        fallback = "vivid"

    if not business_style:
        return fallback

    # Local import to avoid circular imports during app startup.
    from . import crud

    item = crud.get_active_dynamic_list_item_by_value(
        db,
        OPENAI_IMAGE_STYLE_LIST_NAME,
        str(business_style).strip(),
    )
    if not item or not getattr(item, "additional_config", None):
        return fallback

    openai_style = item.additional_config.get("openai_style")
    if not openai_style:
        return fallback

    openai_style_norm = str(openai_style).strip().lower()
    if openai_style_norm in _ALLOWED_OPENAI_STYLES:
        return openai_style_norm

    return fallback
