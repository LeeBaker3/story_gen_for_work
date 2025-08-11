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
