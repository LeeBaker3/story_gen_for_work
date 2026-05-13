from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


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

IMAGE_STYLES_LIST_NAME = "image_styles"
_STYLE_CACHE_KEY = "_image_style_mapping_cache"


@dataclass(frozen=True)
class ResolvedImageStyle:
    """Resolved business style and prompt phrase for image generation."""

    business_style: str | None
    prompt_style: str | None


def map_style(business_style: str | None, mapping: Dict[str, str] | None = None) -> str | None:
    """Return a prompt modifier for the given business style, if known.

    If the style is unknown or None, returns None to preserve the original input.
    """
    if not business_style:
        return None
    m = mapping or DEFAULT_IMAGE_STYLE_MAP
    return m.get(str(business_style).strip(), None)


def _normalize_style_value(business_style: str | None) -> str | None:
    """Normalize a business style string, treating blanks as missing."""

    if business_style is None:
        return None
    normalized = str(business_style).strip()
    return normalized or None


def _get_session_style_cache(db: Any) -> Dict[str, Any]:
    """Return a per-session cache for dynamic image style lookups."""

    info = getattr(db, "info", None)
    if isinstance(info, dict):
        return info.setdefault(_STYLE_CACHE_KEY, {})
    return {}


def _get_active_image_style_items(db: Any) -> list[Any]:
    """Load active image styles once for the current DB session."""

    cache = _get_session_style_cache(db)
    items = cache.get("active_items")
    if items is None:
        from . import crud

        items = crud.get_active_dynamic_list_items(db, IMAGE_STYLES_LIST_NAME)
        cache["active_items"] = items
    return items


def _get_active_image_style_lookup(db: Any) -> Dict[str, Any]:
    """Build a value lookup for active image style items."""

    cache = _get_session_style_cache(db)
    lookup = cache.get("active_lookup")
    if lookup is None:
        lookup = {}
        for item in _get_active_image_style_items(db):
            item_value = _normalize_style_value(
                getattr(item, "item_value", None))
            if item_value:
                lookup[item_value] = item
        cache["active_lookup"] = lookup
    return lookup


def _get_default_image_style_item(db: Any) -> Any | None:
    """Return the default active image style item for the current session."""

    cache = _get_session_style_cache(db)
    if "default_item" not in cache:
        active_items = _get_active_image_style_items(db)
        default_item = next(
            (
                item
                for item in active_items
                if isinstance(getattr(item, "additional_config", None), dict)
                and item.additional_config.get("is_default") is True
            ),
            None,
        )
        cache["default_item"] = default_item or (
            active_items[0] if active_items else None)
    return cache["default_item"]


def resolve_image_style(
    *,
    db: Any,
    business_style: str | None,
    mapping_enabled: bool = False,
) -> ResolvedImageStyle:
    """Resolve the effective business style and prompt phrase.

    For blank or "Default" styles, this prefers the active `image_styles`
    item marked with `additional_config.is_default`, then falls back to the
    lowest `sort_order` active item. When mapping is enabled, an item's
    `additional_config.prompt_modifier` takes precedence over the in-code style
    map, and both fall back to the effective business style string.
    """

    normalized_style = _normalize_style_value(business_style)
    selected_item = None
    effective_business_style = normalized_style

    if normalized_style is None or normalized_style == "Default":
        selected_item = _get_default_image_style_item(db)
        selected_value = _normalize_style_value(
            getattr(selected_item, "item_value", None)
        )
        if selected_value:
            effective_business_style = selected_value
    elif db is not None:
        selected_item = _get_active_image_style_lookup(
            db).get(normalized_style)

    prompt_style = effective_business_style
    if mapping_enabled:
        additional_config = getattr(selected_item, "additional_config", None)
        if isinstance(additional_config, dict):
            prompt_modifier = _normalize_style_value(
                additional_config.get("prompt_modifier")
            )
            if prompt_modifier:
                prompt_style = prompt_modifier
        if not prompt_style:
            prompt_style = map_style(effective_business_style)
        elif prompt_style == effective_business_style:
            mapped_style = map_style(effective_business_style)
            if mapped_style:
                prompt_style = mapped_style

    return ResolvedImageStyle(
        business_style=effective_business_style,
        prompt_style=prompt_style,
    )


OPENAI_IMAGE_STYLE_LIST_NAME = "image_style_mappings"
_ALLOWED_OPENAI_STYLES = {"vivid", "natural"}


def _normalize_openai_style_value(value: Any) -> str | None:
    """Normalize a configured OpenAI style value when it is allowed."""

    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in _ALLOWED_OPENAI_STYLES:
        return normalized
    return None


def normalize_openai_style_default(default: str = "vivid") -> str:
    """Return a safe default OpenAI image style."""

    normalized = _normalize_openai_style_value(default)
    return normalized or "vivid"


def get_admin_image_style_mapping_state(
    *,
    db: Any,
    mapping_enabled: bool,
    default: str = "vivid",
) -> Dict[str, Any]:
    """Return the effective image style mapping state for admin views.

    The returned rules are ordered by active image style sort order. Any
    mapping entries whose business styles are no longer active in the
    `image_styles` list are included after active styles so admins can still
    inspect and clean up stale rules.
    """

    from . import crud

    fallback = normalize_openai_style_default(default)
    image_style_items = crud.get_dynamic_list_items(
        db,
        list_name=IMAGE_STYLES_LIST_NAME,
        limit=1000,
    )
    mapping_items = crud.get_dynamic_list_items(
        db,
        list_name=OPENAI_IMAGE_STYLE_LIST_NAME,
        limit=1000,
    )

    mapping_by_value: Dict[str, Any] = {}
    for item in mapping_items:
        item_value = _normalize_style_value(getattr(item, "item_value", None))
        if item_value:
            mapping_by_value[item_value] = item

    rules: list[Dict[str, Any]] = []
    seen_styles: set[str] = set()

    for style_item in sorted(
        image_style_items,
        key=lambda item: (getattr(item, "sort_order", 0),
                          getattr(item, "id", 0)),
    ):
        business_style = _normalize_style_value(
            getattr(style_item, "item_value", None)
        )
        if not business_style:
            continue

        seen_styles.add(business_style)
        mapping_item = mapping_by_value.get(business_style)
        configured_openai_style = None
        if mapping_item and isinstance(
            getattr(mapping_item, "additional_config", None), dict
        ):
            configured_openai_style = _normalize_openai_style_value(
                mapping_item.additional_config.get("openai_style")
            )

        effective_openai_style = get_openai_image_style(
            db=db,
            business_style=business_style,
            default=fallback,
        )
        source = (
            "dynamic_list"
            if mapping_item
            and getattr(mapping_item, "is_active", False)
            and configured_openai_style
            else "default"
        )
        rules.append(
            {
                "business_style": business_style,
                "image_style_item_id": getattr(style_item, "id", None),
                "image_style_item_label": getattr(style_item, "item_label", None),
                "image_style_item_active": bool(
                    getattr(style_item, "is_active", False)
                ),
                "mapping_item_id": getattr(mapping_item, "id", None)
                if mapping_item else None,
                "mapping_item_label": getattr(mapping_item, "item_label", None)
                if mapping_item else None,
                "mapping_item_active": bool(
                    getattr(mapping_item, "is_active", False)
                ) if mapping_item else False,
                "configured_openai_style": configured_openai_style,
                "effective_openai_style": effective_openai_style,
                "source": source,
                "sort_order": getattr(style_item, "sort_order", 0) or 0,
            }
        )

    orphaned_mapping_rules = []
    for mapping_item in sorted(
        mapping_items,
        key=lambda item: (getattr(item, "sort_order", 0),
                          getattr(item, "id", 0)),
    ):
        business_style = _normalize_style_value(
            getattr(mapping_item, "item_value", None)
        )
        if not business_style or business_style in seen_styles:
            continue

        configured_openai_style = None
        if isinstance(getattr(mapping_item, "additional_config", None), dict):
            configured_openai_style = _normalize_openai_style_value(
                mapping_item.additional_config.get("openai_style")
            )

        orphaned_mapping_rules.append(
            {
                "business_style": business_style,
                "image_style_item_id": None,
                "image_style_item_label": None,
                "image_style_item_active": False,
                "mapping_item_id": getattr(mapping_item, "id", None),
                "mapping_item_label": getattr(mapping_item, "item_label", None),
                "mapping_item_active": bool(
                    getattr(mapping_item, "is_active", False)
                ),
                "configured_openai_style": configured_openai_style,
                "effective_openai_style": get_openai_image_style(
                    db=db,
                    business_style=business_style,
                    default=fallback,
                ),
                "source": "dynamic_list"
                if getattr(mapping_item, "is_active", False)
                and configured_openai_style else "default",
                "sort_order": getattr(mapping_item, "sort_order", 0) or 0,
            }
        )

    rules.extend(orphaned_mapping_rules)

    return {
        "mapping_feature_enabled": bool(mapping_enabled),
        "default_openai_style": fallback,
        "rules": rules,
    }


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

    fallback = normalize_openai_style_default(default)

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
