import os
import re
import uuid
from typing import Tuple
from .settings import get_settings


_PRIVATE_STORY_ASSET_RE = re.compile(r"^images/user_\d+/story_\d+(?:/|$)")


def _data_dir() -> str:
    return get_settings().data_dir


def _private_dir() -> str:
    return get_settings().private_data_dir


def normalize_data_relative_path(path: str) -> str:
    """Return a safe normalized path relative to the data directory."""

    normalized = os.path.normpath(
        str(path or "").replace("\\", "/").lstrip("/"))
    if normalized in ("", "."):
        raise ValueError("Data-relative path is required")
    if normalized.startswith(".."):
        raise ValueError("Data-relative path escapes the data directory")
    return normalized


def resolve_data_path(path: str) -> str:
    """Resolve a data-relative path to an absolute path within DATA_DIR."""

    normalized = normalize_data_relative_path(path)
    data_dir = os.path.realpath(_data_dir())
    resolved = os.path.realpath(os.path.join(data_dir, normalized))
    if resolved != data_dir and not resolved.startswith(data_dir + os.sep):
        raise ValueError("Resolved path escapes the data directory")
    return resolved


def is_private_story_asset_path(path: str) -> bool:
    """Return whether a data-relative path points into a story asset folder."""

    normalized = normalize_data_relative_path(path)
    unix_style = normalized.replace(os.sep, "/")
    return bool(_PRIVATE_STORY_ASSET_RE.match(unix_style))


def images_base_rel(user_id: int) -> str:
    return os.path.join("images", f"user_{user_id}")


def story_images_rel(user_id: int, story_id: int) -> str:
    return os.path.join(images_base_rel(user_id), f"story_{story_id}")


def story_images_abs(user_id: int, story_id: int) -> str:
    return os.path.join(_data_dir(), story_images_rel(user_id, story_id))


def sanitize_name(name: str) -> str:
    if not name:
        return f"item_{uuid.uuid4().hex[:8]}"
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip())


def character_ref_paths(user_id: int, story_id: int, character_name: str) -> Tuple[str, str]:
    """
    Returns (abs_path_on_disk, db_relative_path) for a character reference image.
    """
    base_rel = story_images_rel(user_id, story_id)
    ref_rel_dir = os.path.join(base_rel, "references")
    os.makedirs(os.path.join(_data_dir(), ref_rel_dir), exist_ok=True)
    safe_name = sanitize_name(character_name) or f"char_{uuid.uuid4().hex[:8]}"
    filename = f"{safe_name}_ref_story_{story_id}.png"
    rel_path = os.path.join(ref_rel_dir, filename)
    abs_path = os.path.join(_data_dir(), rel_path)
    return abs_path, rel_path


def page_image_paths(user_id: int, story_id: int, page_num_int: int) -> Tuple[str, str]:
    """
    Returns (abs_path_on_disk, db_relative_path) for a page image.
    Uses 'cover' for page 0 else 'page_{n}' and appends a short uuid.
    """
    base_rel = story_images_rel(user_id, story_id)
    os.makedirs(os.path.join(_data_dir(), base_rel), exist_ok=True)
    prefix = "cover" if page_num_int == 0 else f"page_{page_num_int}"
    suffix = uuid.uuid4().hex[:8]
    filename = f"{prefix}_{suffix}_story_{story_id}_p{page_num_int}.png"
    rel_path = os.path.join(base_rel, filename)
    abs_path = os.path.join(_data_dir(), rel_path)
    return abs_path, rel_path


def character_uploads_abs(user_id: int, char_id: int) -> str:
    """Return absolute directory for a character's private uploads."""
    rel_dir = os.path.join(
        "uploads", f"user_{user_id}", "characters", str(char_id))
    abs_dir = os.path.join(_private_dir(), rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def character_uploaded_photo_candidates_abs(user_id: int, char_id: int) -> Tuple[str, ...]:
    """Return absolute file path candidates for a character's uploaded photo."""
    base = os.path.join(character_uploads_abs(user_id, char_id), "photo")
    return (
        base + ".jpg",
        base + ".jpeg",
        base + ".png",
        base + ".webp",
    )
