from sqlalchemy.orm import Session
from . import schemas
from backend.logging_config import error_logger
# Added DynamicList, DynamicListItem
from .database import User, Story, Page, DynamicList, DynamicListItem, StoryGenerationTask, Character, CharacterImage
from passlib.context import CryptContext
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder  # Added for JSON conversion
# Ensure datetime and timezone are imported
from datetime import datetime, timezone
import uuid  # Import uuid for generating task IDs

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


_STORY_DYNAMIC_LIST_NAMES: Dict[str, str] = {
    "genre": "genres",
    "image_style": "image_styles",
    "word_to_picture_ratio": "word_to_picture_ratio",
    "text_density": "text_density",
}

_STORY_FIELD_DEFAULTS: Dict[str, str] = {
    "image_style": schemas.ImageStyle.DEFAULT.value,
    "word_to_picture_ratio": schemas.WordToPictureRatio.PER_PAGE.value,
    "text_density": schemas.TextDensity.CONCISE.value,
}


def _coerce_story_field_value(value: Any, default: Optional[str] = None) -> Optional[str]:
    """Normalize incoming story field values to persisted strings."""

    if value in (None, ""):
        return default
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def validate_story_dynamic_list_values(
    db: Session,
    story_data: schemas.StoryBase,
) -> Dict[str, str]:
    """Validate story metadata fields against active dynamic-list items.

    If a list has not been seeded yet, validation for that specific field is
    skipped so existing direct CRUD callers keep working in sparse test setups.
    """

    resolved_values = {
        "genre": _coerce_story_field_value(story_data.genre),
        "image_style": _coerce_story_field_value(
            story_data.image_style,
            _STORY_FIELD_DEFAULTS["image_style"],
        ),
        "word_to_picture_ratio": _coerce_story_field_value(
            story_data.word_to_picture_ratio,
            _STORY_FIELD_DEFAULTS["word_to_picture_ratio"],
        ),
        "text_density": _coerce_story_field_value(
            story_data.text_density,
            _STORY_FIELD_DEFAULTS["text_density"],
        ),
    }

    for field_name, list_name in _STORY_DYNAMIC_LIST_NAMES.items():
        field_value = resolved_values[field_name]
        active_items = get_active_dynamic_list_items(db, list_name=list_name)
        if not active_items:
            continue

        active_values = {item.item_value for item in active_items}
        if field_value not in active_values:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=[
                    {
                        "loc": ["body", field_name],
                        "msg": (
                            f"Value '{field_value}' is not an active item in "
                            f"dynamic list '{list_name}'."
                        ),
                        "type": "value_error.dynamic_list.inactive_or_unknown",
                    }
                ],
            )

    return resolved_values

def get_story_editor_settings(story: Story) -> Dict[str, Any]:
    """Return normalized document editor settings for a story."""

    settings = dict(schemas.EDITOR_DEFAULTS)
    if isinstance(getattr(story, "editor_settings", None), dict):
        settings.update(story.editor_settings)
    return settings


def get_page_editor_state(page: Page) -> Dict[str, Any]:
    """Return normalized editor state for a page, including restore points."""

    state: Dict[str, Any] = {}
    if isinstance(getattr(page, "editor_state", None), dict):
        state.update(page.editor_state)

    if not state.get("original_text"):
        state["original_text"] = page.text
    if not state.get("original_image_path"):
        state["original_image_path"] = page.image_path
    return state


def get_effective_page_editor_settings(story: Story, page: Page) -> Dict[str, Any]:
    """Return the effective editor settings for a specific page."""

    settings = get_story_editor_settings(story)
    page_state = get_page_editor_state(page)
    for key in ("text_position", "font_size", "font_color"):
        value = page_state.get(key)
        if value not in (None, ""):
            settings[key] = value
    return settings


def _coerce_datetime_to_utc(value: datetime) -> datetime:
    """Coerce a datetime into an aware UTC datetime.

    SQLite frequently returns timezone-naive datetimes even when SQLAlchemy
    columns are declared with `timezone=True`. To avoid runtime errors when
    computing durations, we treat naive datetimes as UTC.

    Parameters
    ----------
    value:
        Datetime value from the database or application code.

    Returns
    -------
    datetime
        A timezone-aware UTC datetime.
    """

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

# User CRUD


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(
        User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role="user",
        # Ensure is_active is set, default to True
        is_active=user.is_active if user.is_active is not None else True
    )  # Added user.email
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Admin CRUD for Users


def admin_get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """List users excluding soft-deleted ones by default."""
    return db.query(User).filter(User.is_deleted == False).offset(skip).limit(limit).all()


def admin_update_user(db: Session, user_id: int, user_update: schemas.AdminUserUpdate) -> Optional[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)
    return db_user

# Story CRUD
# Modified to handle StoryCreate which doesn't have a title initially
# The title will be populated after AI generation


# Added is_draft, title is Optional
def create_story_db_entry(db: Session, story_data: schemas.StoryBase, user_id: int, title: Optional[str] = None, is_draft: bool = False):
    """
    Creates the story entry in the database.
    If it's a draft, the title might be None.
    The main story content (pages) will be added separately after AI generation for non-drafts.
    """
    resolved_values = validate_story_dynamic_list_values(db, story_data)
    word_to_picture_ratio_value = resolved_values["word_to_picture_ratio"]
    text_density_value = resolved_values["text_density"]
    image_style_value = resolved_values["image_style"]
    editor_settings_value = dict(schemas.EDITOR_DEFAULTS)
    if getattr(story_data, "editor_settings", None):
        editor_settings_value.update(
            story_data.editor_settings.model_dump(exclude_none=True)
        )

    # Use the title from story_data if it exists, otherwise use the title argument
    final_title = getattr(story_data, 'title', None) or title

    db_story = Story(
        title=final_title,  # Title can be None for drafts
        genre=resolved_values["genre"],
        # Changed from outline to story_outline
        story_outline=story_data.story_outline,
        # Encode list of Pydantic models to JSON
        main_characters=jsonable_encoder(story_data.main_characters),
        num_pages=story_data.num_pages,
        tone=story_data.tone,
        setting=story_data.setting,
        # Added image_style
        image_style=image_style_value,
        # FR13: Added word_to_picture_ratio
        word_to_picture_ratio=word_to_picture_ratio_value,
        # New Req: Added text_density
        text_density=text_density_value,
        owner_id=user_id,
        is_draft=is_draft,  # FR24
        generated_at=None if is_draft else datetime.now(timezone.utc),  # FR24
        editor_settings=editor_settings_value,
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story


def create_story_draft(db: Session, story_data: schemas.StoryCreate, user_id: int) -> Story:
    """
    Creates a story draft. Title can be None initially.
    """
    resolved_values = validate_story_dynamic_list_values(db, story_data)
    word_to_picture_ratio_value = resolved_values["word_to_picture_ratio"]
    text_density_value = resolved_values["text_density"]
    image_style_value = resolved_values["image_style"]
    editor_settings_value = dict(schemas.EDITOR_DEFAULTS)
    if getattr(story_data, "editor_settings", None):
        editor_settings_value.update(
            story_data.editor_settings.model_dump(exclude_none=True)
        )

    db_story_draft = Story(
        title=story_data.title,  # Can be None or a preliminary title
        genre=resolved_values["genre"],
        story_outline=story_data.story_outline,
        main_characters=jsonable_encoder(story_data.main_characters),
        num_pages=story_data.num_pages,
        tone=story_data.tone,
        setting=story_data.setting,
        image_style=image_style_value,
        word_to_picture_ratio=word_to_picture_ratio_value,
        text_density=text_density_value,
        owner_id=user_id,
        is_draft=True,
        generated_at=None,  # Drafts are not "generated" in the final sense
        editor_settings=editor_settings_value,
    )
    db.add(db_story_draft)
    db.commit()
    db.refresh(db_story_draft)
    return db_story_draft


def update_story_draft(db: Session, story_id: int, story_update_data: schemas.StoryCreate, user_id: int) -> Optional[Story]:
    """
    Updates an existing story draft.
    """
    db_story_draft = db.query(Story).filter(
        Story.id == story_id, Story.owner_id == user_id, Story.is_draft == True).first()
    if not db_story_draft:
        return None

    resolved_values = validate_story_dynamic_list_values(db, story_update_data)
    update_data = story_update_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "main_characters":
            setattr(db_story_draft, key, jsonable_encoder(value))
        elif key in resolved_values:
            setattr(db_story_draft, key, resolved_values[key])
        else:
            setattr(db_story_draft, key, value)

    db.commit()
    db.refresh(db_story_draft)
    return db_story_draft


def finalize_story_draft(db: Session, story_id: int, user_id: int, title: str) -> Optional[Story]:
    """
    Finalizes a draft, setting is_draft to False and updating generated_at.
    This would typically be called before AI generation of pages.
    The title from the generation process is also updated here.
    """
    db_story = db.query(Story).filter(
        Story.id == story_id, Story.owner_id == user_id, Story.is_draft == True).first()
    if not db_story:
        return None

    db_story.is_draft = False
    db_story.generated_at = datetime.now(timezone.utc)
    db_story.title = title  # Update title upon finalization
    db.commit()
    db.refresh(db_story)
    return db_story


def update_story_with_pages(db: Session, story_id: int, pages_data: List[schemas.PageCreate], image_paths: List[Optional[str]]):
    """
    Adds pages to an existing story.
    """
    for i, page_data in enumerate(pages_data):
        image_path = image_paths[i] if i < len(image_paths) else None
        db_page = Page(
            **page_data.model_dump(),  # Changed from .dict()
            story_id=story_id,
            image_path=image_path
        )
        db.add(db_page)
    db.commit()


# Increased limit, added include_drafts
def get_stories_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100, include_drafts: bool = True):
    query = db.query(Story).filter(Story.owner_id == user_id)
    if not include_drafts:
        query = query.filter(Story.is_draft == False)
    # Order by creation
    return query.order_by(Story.created_at.desc()).offset(skip).limit(limit).all()


def get_story_draft(db: Session, story_id: int, user_id: int) -> Optional[Story]:
    """
    Retrieves a specific story draft by its ID for a given user.
    """
    return db.query(Story).filter(Story.id == story_id, Story.owner_id == user_id, Story.is_draft == True).first()


def get_story(db: Session, story_id: int, user_id: int) -> Optional[Story]:
    """
    Retrieves a single story by its ID and owner.
    """
    return db.query(Story).filter(Story.id == story_id, Story.owner_id == user_id).first()


def get_story_by_title_and_owner(db: Session, title: str, user_id: int) -> Optional[Story]:
    """
    Retrieves a story by its title and owner ID.
    """
    return db.query(Story).filter(Story.title == title, Story.owner_id == user_id).first()


def update_story_title(db: Session, story_id: int, new_title: str) -> Optional[Story]:
    """
    Updates the title of an existing story.
    """
    db_story = db.query(Story).filter(Story.id == story_id).first()
    if db_story:
        db_story.title = new_title
        title_page = db.query(Page).filter(
            Page.story_id == story_id,
            Page.page_number == 0,
        ).first()
        if title_page:
            title_page.text = new_title
            title_page.editor_state = get_page_editor_state(title_page)
        db.commit()
        db.refresh(db_story)
        return db_story
    return None


def save_story_editor(
    db: Session,
    story_id: int,
    user_id: int,
    editor_update: schemas.StoryEditorUpdate,
) -> Optional[Story]:
    """Persist story editor title/defaults/page text and override changes."""

    db_story = get_story(db, story_id=story_id, user_id=user_id)
    if not db_story:
        return None

    if editor_update.title is not None:
        db_story.title = editor_update.title.strip() or db_story.title
        title_page = db.query(Page).filter(
            Page.story_id == story_id,
            Page.page_number == 0,
        ).first()
        if title_page:
            title_page.text = db_story.title
            title_page.editor_state = get_page_editor_state(title_page)

    if editor_update.editor_settings is not None:
        current_settings = get_story_editor_settings(db_story)
        current_settings.update(
            editor_update.editor_settings.model_dump(exclude_none=True)
        )
        db_story.editor_settings = current_settings

    pages_by_id = {
        page.id: page
        for page in db.query(Page).filter(Page.story_id == story_id).all()
    }
    for page_update in editor_update.pages:
        db_page = pages_by_id.get(page_update.id)
        if not db_page:
            continue

        if page_update.text is not None:
            db_page.text = page_update.text
            if db_page.page_number == 0:
                db_story.title = page_update.text.strip() or db_story.title

        state = get_page_editor_state(db_page)
        if page_update.editor_state is not None:
            state.update(
                page_update.editor_state.model_dump(exclude_none=True))
        db_page.editor_state = state

    db.commit()
    db.refresh(db_story)
    return db_story


def restore_page_text(
    db: Session,
    story_id: int,
    page_id: int,
    user_id: int,
) -> Optional[Page]:
    """Restore a page's text to its original generated content."""

    db_story = get_story(db, story_id=story_id, user_id=user_id)
    if not db_story:
        return None
    db_page = db.query(Page).filter(Page.id == page_id,
                                    Page.story_id == story_id).first()
    if not db_page:
        return None

    state = get_page_editor_state(db_page)
    original_text = state.get("original_text")
    if original_text is not None:
        db_page.text = original_text
        if db_page.page_number == 0:
            db_story.title = original_text
        db_page.editor_state = state
        db.commit()
        db.refresh(db_page)
    return db_page


def restore_page_image(
    db: Session,
    story_id: int,
    page_id: int,
    user_id: int,
) -> Optional[Page]:
    """Restore a page's image to its original generated asset."""

    db_story = get_story(db, story_id=story_id, user_id=user_id)
    if not db_story:
        return None
    db_page = db.query(Page).filter(Page.id == page_id,
                                    Page.story_id == story_id).first()
    if not db_page:
        return None

    state = get_page_editor_state(db_page)
    original_image_path = state.get("original_image_path")
    db_page.image_path = original_image_path
    db_page.editor_state = state
    db.commit()
    db.refresh(db_page)
    return db_page

# Page CRUD (will be used internally when story is generated)


def create_story_page(db: Session, page: schemas.PageCreate, story_id: int, image_path: Optional[str] = None):
    db_page = Page(**page.model_dump(), story_id=story_id,
                   image_path=image_path)  # Changed from .dict()
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page


def delete_story_db_entry(db: Session, story_id: int) -> bool:
    """
    Deletes a story and all its associated pages from the database.
    Returns True if deletion was successful, False otherwise.
    """
    db_story = db.query(Story).filter(Story.id == story_id).first()
    if db_story:
        # Delete associated pages first to maintain foreign key integrity
        db.query(Page).filter(Page.story_id == story_id).delete(
            synchronize_session=False)
        db.delete(db_story)
        db.commit()
        return True
    return False


def update_page_image_path(db: Session, page_id: int, image_path: str) -> Optional[Page]:
    """
    Updates the image_path of an existing page.
    """
    db_page = db.query(Page).filter(Page.id == page_id).first()
    if db_page:
        db_page.image_path = image_path
        db.commit()
        db.refresh(db_page)
        return db_page
    return None

# --- Admin User Management CRUD ---


def get_users_admin(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Retrieves a list of users for admin purposes.
    """
    return db.query(User).offset(skip).limit(limit).all()


def get_user_admin(db: Session, user_id: int) -> Optional[User]:
    """Retrieve a single user by ID (excluding soft-deleted)."""
    return db.query(User).filter(User.id == user_id, User.is_deleted == False).first()


def update_user_status_admin(db: Session, user_id: int, is_active: bool) -> Optional[User]:
    """
    Updates the is_active status of a user by admin.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        db_user.is_active = is_active
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


def update_user_role_admin(db: Session, user_id: int, role: str) -> Optional[User]:
    """
    Updates the role of a user by admin.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        # Add validation for role if necessary (e.g., ensure it's 'user' or 'admin')
        db_user.role = role
        db.commit()
        db.refresh(db_user)
        return db_user
    return None


def soft_delete_user_admin(db: Session, user_id: int) -> bool:
    """Soft delete a user by setting is_deleted=True and deactivating the account.

    Returns True if updated, False if user does not exist or already deleted.
    """
    db_user = db.query(User).filter(User.id == user_id,
                                    User.is_deleted == False).first()
    if not db_user:
        return False
    db_user.is_deleted = True
    db_user.is_active = False
    db.commit()
    return True


# --- Story Moderation CRUD ---

def list_stories_admin(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    include_hidden: bool = False,
    include_deleted: bool = False,
):
    """List stories with filters for admin moderation."""
    query = db.query(Story)
    if not include_deleted:
        query = query.filter(Story.is_deleted == False)
    if not include_hidden:
        query = query.filter(Story.is_hidden == False)
    if user_id is not None:
        query = query.filter(Story.owner_id == user_id)
    if status is not None:
        if status == "generated":
            query = query.filter(Story.is_draft == False)
        elif status == "draft":
            query = query.filter(Story.is_draft == True)
    if created_from is not None:
        query = query.filter(Story.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Story.created_at <= created_to)
    total = query.count()
    items = query.order_by(Story.created_at.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    return total, items


def set_story_hidden_admin(db: Session, story_id: int, is_hidden: bool) -> Optional[Story]:
    story = db.query(Story).filter(Story.id == story_id,
                                   Story.is_deleted == False).first()
    if not story:
        return None
    story.is_hidden = bool(is_hidden)
    db.commit()
    db.refresh(story)
    return story


def soft_delete_story_admin(db: Session, story_id: int) -> bool:
    story = db.query(Story).filter(Story.id == story_id,
                                   Story.is_deleted == False).first()
    if not story:
        return False
    story.is_deleted = True
    db.commit()
    return True

# --- Dynamic List CRUD (FR-ADM-05) ---


def create_dynamic_list(db: Session, dynamic_list: schemas.DynamicListCreate) -> DynamicList:
    db_dynamic_list = DynamicList(**dynamic_list.model_dump())
    db.add(db_dynamic_list)
    db.commit()
    db.refresh(db_dynamic_list)
    return db_dynamic_list


def get_dynamic_list(db: Session, list_name: str) -> Optional[DynamicList]:
    return db.query(DynamicList).filter(DynamicList.list_name == list_name).first()


def get_dynamic_lists(db: Session, skip: int = 0, limit: int = 100) -> List[DynamicList]:
    # Added order_by
    return db.query(DynamicList).order_by(DynamicList.list_name).offset(skip).limit(limit).all()


def update_dynamic_list(db: Session, list_name: str, dynamic_list_update: schemas.DynamicListUpdate) -> Optional[DynamicList]:
    db_list = get_dynamic_list(db, list_name)
    if db_list:
        update_data = dynamic_list_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_list, key, value)
        db_list.updated_at = datetime.now(
            timezone.utc)  # Ensure timezone aware
        db.commit()
        db.refresh(db_list)
    return db_list


def delete_dynamic_list(db: Session, list_name: str) -> bool:
    db_list = get_dynamic_list(db, list_name)
    if db_list:
        # Cascading delete for items is handled by the relationship setting in database.py
        db.delete(db_list)
        db.commit()
        return True
    return False

# --- Dynamic List Item CRUD (FR-ADM-05) ---


def create_dynamic_list_item(db: Session, item: schemas.DynamicListItemCreate) -> DynamicListItem:
    parent_list = get_dynamic_list(db, item.list_name)
    if not parent_list:
        # For API layer to catch
        raise ValueError(f"Parent list '{item.list_name}' does not exist.")

    # Check for uniqueness of item_value within the list
    existing_item = db.query(DynamicListItem).filter(
        DynamicListItem.list_name == item.list_name,
        DynamicListItem.item_value == item.item_value
    ).first()
    if existing_item:
        raise ValueError(
            f"Item with value '{item.item_value}' already exists in list '{item.list_name}'.")

    db_item = DynamicListItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_dynamic_list_item(db: Session, item_id: int) -> Optional[DynamicListItem]:
    return db.query(DynamicListItem).filter(DynamicListItem.id == item_id).first()


def get_dynamic_list_items(
    db: Session,
    list_name: str,
    skip: int = 0,
    limit: int = 100,
    only_active: Optional[bool] = None
) -> List[DynamicListItem]:
    query = db.query(DynamicListItem).filter(
        DynamicListItem.list_name == list_name)
    if only_active is not None:
        query = query.filter(DynamicListItem.is_active == only_active)
    return query.order_by(DynamicListItem.sort_order, DynamicListItem.item_label).offset(skip).limit(limit).all()


def get_public_list_items(db: Session, list_name: str) -> List[schemas.DynamicListItemPublic]:
    """
    Gets all active, public-facing items for a list, sorted by sort_order.
    Returns only the item_value and item_label.
    """
    return db.query(DynamicListItem).filter(DynamicListItem.list_name == list_name, DynamicListItem.is_active == True).order_by(DynamicListItem.sort_order, DynamicListItem.item_label).all()


def get_active_dynamic_list_items(db: Session, list_name: str, skip: int = 0, limit: int = 1000) -> List[DynamicListItem]:
    """Gets all active items for a list, sorted."""
    return db.query(DynamicListItem)\
        .filter(DynamicListItem.list_name == list_name, DynamicListItem.is_active == True)\
        .order_by(DynamicListItem.sort_order, DynamicListItem.item_label)\
        .offset(skip)\
        .limit(limit)\
        .all()


def get_active_dynamic_list_item_by_value(
    db: Session,
    list_name: str,
    item_value: str,
) -> Optional[DynamicListItem]:
    """Get a single active DynamicListItem by its value.

    This is useful for lightweight lookups (e.g., mapping business enums to
    provider-specific parameters).
    """
    return (
        db.query(DynamicListItem)
        .filter(
            DynamicListItem.list_name == list_name,
            DynamicListItem.item_value == item_value,
            DynamicListItem.is_active == True,
        )
        .first()
    )


def update_dynamic_list_item(db: Session, item_id: int, item_update: schemas.DynamicListItemUpdate) -> Optional[DynamicListItem]:
    db_item = get_dynamic_list_item(db, item_id)
    if db_item:
        update_data = item_update.model_dump(exclude_unset=True)

        # If item_value is being changed, check for uniqueness within the list
        if 'item_value' in update_data and update_data['item_value'] != db_item.item_value:
            existing_item_with_new_value = db.query(DynamicListItem).filter(
                DynamicListItem.list_name == db_item.list_name,
                DynamicListItem.item_value == update_data['item_value'],
                DynamicListItem.id != item_id  # Exclude the current item itself
            ).first()
            if existing_item_with_new_value:
                raise ValueError(
                    f"Another item with value '{update_data['item_value']}' already exists in list '{db_item.list_name}'.")

        for key, value in update_data.items():
            setattr(db_item, key, value)
        db_item.updated_at = datetime.now(
            timezone.utc)  # Ensure timezone aware
        db.commit()
        db.refresh(db_item)
    return db_item


def delete_dynamic_list_item(db: Session, item_id: int) -> bool:
    # Before deleting, ensure it's not in use (this check might be better at API layer for user feedback)
    # if is_dynamic_list_item_in_use(db, item_id):
    #     raise ValueError("Cannot delete item: it is currently in use.") # Or return a specific status/message

    db_item = get_dynamic_list_item(db, item_id)
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False


def is_dynamic_list_item_in_use(db: Session, item_id: int) -> dict:
    """
    Checks if a DynamicListItem is referenced in any existing Stories.
    Returns a dictionary: {"is_in_use": bool, "details": List[str]}
    """
    item = get_dynamic_list_item(db, item_id)
    if not item:
        return {"is_in_use": False, "details": ["Item not found."]}

    usage_details = []

    # Only check specific story fields if the list name matches known special lists
    if item.list_name == "genres":
        stories_using_genre = db.query(Story.id, Story.title).filter(
            Story.genre == item.item_value).all()
        if stories_using_genre:
            usage_details.append(
                f"Genre in Stories: {', '.join([s.title or f'ID {s.id}' for s in stories_using_genre])}")

    elif item.list_name == "image_styles":
        stories_using_style = db.query(Story.id, Story.title).filter(
            Story.image_style == item.item_value).all()
        if stories_using_style:
            usage_details.append(
                f"Image Style in Stories: {', '.join([s.title or f'ID {s.id}' for s in stories_using_style])}")

    # Add more checks here for other specific dynamic lists and how they are used.
    # For generic lists not tied to specific Story fields, they are considered not in use by default
    # unless a more generic check (e.g., in a hypothetical UserPreferences.favorite_color_item_id) is added.

    if usage_details:
        return {"is_in_use": True, "details": usage_details}

    # If no specific usage is found for known list types, or if it's a generic list,
    # assume not in use by default for this specific check.
    # The frontend might show a generic "Not in direct use" or similar.
    return {"is_in_use": False, "details": []}


def update_story_with_generated_content(db: Session, story_id: int, story_content: dict) -> Optional[Story]:
    """
    Updates a story with the content generated by the AI service.
    This includes updating the title and creating all the pages.
    """
    db_story = db.query(Story).filter(Story.id == story_id).first()
    if not db_story:
        error_logger.error(
            f"Story with id {story_id} not found for updating with generated content.")
        return None

    # Update story title
    if 'Title' in story_content:
        db_story.title = story_content['Title']
    db_story.editor_settings = get_story_editor_settings(db_story)

    # Delete existing pages to prevent duplicates
    db.query(Page).filter(Page.story_id == story_id).delete(
        synchronize_session=False)

    # Create new pages
    if 'Pages' in story_content and isinstance(story_content['Pages'], list):
        for page_data in story_content['Pages']:
            # Coerce page number: use 0 for title page, else integer
            raw_page_num = page_data.get('Page_number')
            page_number: int
            if isinstance(raw_page_num, str):
                if raw_page_num.lower() == 'title':
                    page_number = 0
                else:
                    try:
                        page_number = int(raw_page_num)
                    except (TypeError, ValueError):
                        page_number = 0
            else:
                try:
                    page_number = int(
                        raw_page_num) if raw_page_num is not None else 0
                except (TypeError, ValueError):
                    page_number = 0

            new_page = Page(
                story_id=story_id,
                page_number=page_number,
                text=page_data.get('Text'),
                image_description=page_data.get('Image_description'),
                image_path=page_data.get('image_url'),
                editor_state={
                    "original_text": page_data.get('Text'),
                    "original_image_path": page_data.get('image_url'),
                },
            )
            db.add(new_page)

    db_story.generated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_story)
    return db_story


def create_story_generation_task(db: Session, story_id: int, user_id: int) -> Optional[schemas.StoryGenerationTask]:
    new_task = StoryGenerationTask(
        id=str(uuid.uuid4()),
        story_id=story_id,
        user_id=user_id,
        status=schemas.GenerationTaskStatus.PENDING.value,
        progress=0,
        current_step=schemas.GenerationTaskStep.INITIALIZING.value,
        attempts=0,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def get_story_generation_task(db: Session, task_id: str) -> Optional[StoryGenerationTask]:
    return db.query(StoryGenerationTask).filter(StoryGenerationTask.id == task_id).first()


def update_story_generation_task_progress(
    db: Session,
    task_id: str,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
) -> Optional[StoryGenerationTask]:
    """Convenience helper to update just progress and/or current_step."""
    return update_story_generation_task(
        db,
        task_id,
        progress=progress,
        current_step=current_step,
    )


def update_story_generation_task(
    db: Session,
    task_id: str,
    status: Optional[schemas.GenerationTaskStatus] = None,
    progress: Optional[int] = None,
    current_step: Optional[object] = None,
    error_message: Optional[str] = None,
    retry_counts_by_page: Optional[Dict[str, int]] = None,
    total_retries: Optional[int] = None,
    failed_pages_count: Optional[int] = None,
) -> Optional[StoryGenerationTask]:
    task = get_story_generation_task(db, task_id)
    if not task:
        return None
    # Capture state transitions and timing metrics
    now = datetime.now(timezone.utc)
    previous_status = task.status

    if status is not None:
        new_status = status.value if hasattr(status, "value") else str(status)
        # Set started_at when first moving from pending to in_progress
        if new_status == schemas.GenerationTaskStatus.IN_PROGRESS.value and task.started_at is None:
            task.started_at = now
        # On terminal states, record completed_at and duration
        if new_status in [schemas.GenerationTaskStatus.COMPLETED.value, schemas.GenerationTaskStatus.FAILED.value]:
            if task.completed_at is None:
                task.completed_at = now
            if task.started_at and task.completed_at and task.duration_ms is None:
                started_at_utc = _coerce_datetime_to_utc(task.started_at)
                completed_at_utc = _coerce_datetime_to_utc(task.completed_at)
                duration_ms = int(
                    (completed_at_utc - started_at_utc).total_seconds() * 1000
                )
                # Guard against negative values due to clock skew or bad data.
                task.duration_ms = max(0, duration_ms)
        task.status = new_status
    if progress is not None:
        task.progress = progress
    if current_step is not None:
        # Allow passing either enum or string
        if hasattr(current_step, "value"):
            task.current_step = current_step.value
        else:
            task.current_step = str(current_step)
    if error_message is not None:
        task.error_message = error_message
        # Update last_error for persistent tracking (do not clear automatically)
        task.last_error = error_message
    if retry_counts_by_page is not None:
        task.retry_counts_by_page = retry_counts_by_page
    if total_retries is not None:
        task.total_retries = total_retries
    if failed_pages_count is not None:
        task.failed_pages_count = failed_pages_count

    # Increment attempts if we re-enter in_progress after a failure or while already in progress (retry scenario)
    if status is not None:
        # Heuristic: if transitioning to in_progress from failed or staying in in_progress with an error update
        if task.status == schemas.GenerationTaskStatus.IN_PROGRESS.value and previous_status in [schemas.GenerationTaskStatus.FAILED.value]:
            task.attempts = (task.attempts or 0) + 1
        # If marking failed, don't increment attempts yet; attempts represent retry cycles after failure

    db.commit()
    db.refresh(task)
    return task


def update_story_generated_at(db: Session, story_id: int) -> Optional[Story]:
    story = db.query(Story).filter(Story.id == story_id).first()
    if story:
        story.generated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(story)
        return story
    return None


# --- Characters Domain (Phase 2) ---


def create_character(db: Session, user_id: int, payload: schemas.CharacterCreate) -> Character:
    ch = Character(
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        age=payload.age,
        gender=payload.gender,
        clothing_style=payload.clothing_style,
        key_traits=payload.key_traits,
        image_style=payload.image_style,
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


def get_character_by_name_ci(db: Session, user_id: int, name: str) -> Optional[Character]:
    """Find a character by case-insensitive name for a given user."""
    if not name:
        return None
    return db.query(Character).filter(
        Character.user_id == user_id,
        Character.name.ilike(name)
    ).first()


def get_character(db: Session, user_id: int, char_id: int) -> Optional[Character]:
    return db.query(Character).filter(Character.id == char_id, Character.user_id == user_id).first()


def list_characters(db: Session, user_id: int, q: Optional[str] = None, page: int = 1, page_size: int = 20):
    query = db.query(Character).filter(Character.user_id == user_id)
    if q:
        like = f"%{q}%"
        query = query.filter(Character.name.ilike(like))
    total = query.count()
    items = query.order_by(Character.updated_at.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    return total, items


def update_character(db: Session, user_id: int, char_id: int, payload: schemas.CharacterUpdate) -> Optional[Character]:
    ch = get_character(db, user_id, char_id)
    if not ch:
        return None
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(ch, k, v)
    ch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ch)
    return ch


def delete_character(db: Session, user_id: int, char_id: int) -> bool:
    ch = get_character(db, user_id, char_id)
    if not ch:
        return False
    db.delete(ch)
    db.commit()
    return True


def add_character_image(db: Session, user_id: int, char_id: int, file_path: str, prompt_used: Optional[str], image_style: Optional[str]) -> Optional[CharacterImage]:
    ch = get_character(db, user_id, char_id)
    if not ch:
        return None
    img = CharacterImage(character_id=char_id, file_path=file_path,
                         prompt_used=prompt_used, image_style=image_style)
    db.add(img)
    db.commit()
    db.refresh(img)
    # set current image
    ch.current_image_id = img.id
    ch.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ch)
    return img


def upsert_character_from_detail(db: Session, user_id: int, char_detail: dict) -> Character:
    """
    Create or update a Character for the given user based on a character detail dict
    coming from story input or generation. If a reference image path is present,
    attach it as the current CharacterImage.

    Expected keys in char_detail: name (required), description, age, gender,
    clothing_style, key_traits, image_style (optional), reference_image_path (optional).
    """
    name = (char_detail.get('name') or '').strip()
    if not name:
        raise ValueError("Character detail missing required 'name'.")

    # Try to find existing character by name (case-insensitive) and user
    existing = db.query(Character).filter(
        Character.user_id == user_id,
        Character.name.ilike(name)
    ).first()

    if existing:
        # Update fields if provided
        for key in ['description', 'age', 'gender', 'clothing_style', 'key_traits', 'image_style']:
            if key in char_detail and char_detail[key] is not None:
                setattr(existing, key, char_detail[key])
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        ch = existing
    else:
        ch = Character(
            user_id=user_id,
            name=name,
            description=char_detail.get('description'),
            age=char_detail.get('age'),
            gender=char_detail.get('gender'),
            clothing_style=char_detail.get('clothing_style'),
            key_traits=char_detail.get('key_traits'),
            image_style=char_detail.get('image_style'),
        )
        db.add(ch)
        db.commit()
        db.refresh(ch)

    # Attach reference image if provided
    ref_path = char_detail.get('reference_image_path')
    if ref_path:
        # Avoid duplicating if current image already points to this path
        already_has = False
        if ch.current_image:
            try:
                already_has = (ch.current_image.file_path == ref_path)
            except Exception:
                already_has = False
        if not already_has:
            add_character_image(db, user_id, ch.id, ref_path, prompt_used=None,
                                image_style=char_detail.get('image_style'))

    return ch


def upsert_characters_from_user_stories(db: Session, user_id: int, include_drafts: bool = True) -> int:
    """
    Scan all stories for the given user and upsert characters from their main_characters
    into the Characters library. Returns the number of upsert attempts performed.
    """
    query = db.query(Story).filter(Story.owner_id == user_id)
    if not include_drafts:
        query = query.filter(Story.is_draft == False)
    stories = query.all()
    count = 0
    for s in stories:
        try:
            chars = s.main_characters or []
            if isinstance(chars, list):
                for ch in chars:
                    try:
                        # ch is expected to be a dict already (json stored)
                        upsert_character_from_detail(db, user_id, ch)
                        count += 1
                    except Exception:
                        # continue on individual character failures
                        pass
        except Exception:
            # continue on story failures
            pass
    return count
