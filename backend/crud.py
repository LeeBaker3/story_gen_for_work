from sqlalchemy.orm import Session
from . import schemas
from backend.logging_config import error_logger
# Added DynamicList, DynamicListItem
from .database import User, Story, Page, DynamicList, DynamicListItem, StoryGenerationTask
from passlib.context import CryptContext
from typing import List, Optional
from fastapi.encoders import jsonable_encoder  # Added for JSON conversion
# Ensure datetime and timezone are imported
from datetime import datetime, timezone
import uuid  # Import uuid for generating task IDs

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
        # Ensure role is set, default to 'user'
        role=user.role if user.role else 'user',
        # Ensure is_active is set, default to True
        is_active=user.is_active if user.is_active is not None else True
    )  # Added user.email
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Admin CRUD for Users


def admin_get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def admin_update_user(db: Session, user_id: int, user_update: schemas.AdminUserUpdate) -> Optional[User]:
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        # Basic validation for role, can be enhanced with Enums or more specific checks
        if key == "role" and value not in ["user", "admin"]:
            # Skip invalid role update or raise an error
            continue
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
    # Determine the string value for word_to_picture_ratio
    word_to_picture_ratio_value = story_data.word_to_picture_ratio.value \
        if story_data.word_to_picture_ratio else schemas.WordToPictureRatio.PER_PAGE.value

    # Determine the string value for text_density (New Req)
    text_density_value = story_data.text_density.value \
        if story_data.text_density else schemas.TextDensity.CONCISE.value

    image_style_value = story_data.image_style.value \
        if story_data.image_style else schemas.ImageStyle.DEFAULT.value

    # Use the title from story_data if it exists, otherwise use the title argument
    final_title = getattr(story_data, 'title', None) or title

    db_story = Story(
        title=final_title,  # Title can be None for drafts
        genre=story_data.genre.value,
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
        generated_at=None if is_draft else datetime.now(timezone.utc)  # FR24
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    return db_story


def create_story_draft(db: Session, story_data: schemas.StoryCreate, user_id: int) -> Story:
    """
    Creates a story draft. Title can be None initially.
    """
    # Extract enums or use defaults
    word_to_picture_ratio_value = story_data.word_to_picture_ratio.value if story_data.word_to_picture_ratio else schemas.WordToPictureRatio.PER_PAGE.value
    text_density_value = story_data.text_density.value if story_data.text_density else schemas.TextDensity.CONCISE.value
    image_style_value = story_data.image_style.value if story_data.image_style else schemas.ImageStyle.DEFAULT.value

    db_story_draft = Story(
        title=story_data.title,  # Can be None or a preliminary title
        genre=story_data.genre.value,
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
        generated_at=None  # Drafts are not "generated" in the final sense
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

    update_data = story_update_data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "main_characters":
            setattr(db_story_draft, key, jsonable_encoder(value))
        elif hasattr(schemas, key.replace("_", " ").title().replace(" ", "")):  # Handle Enum types
            # Attempt to get the Enum class dynamically
            enum_class_name = key.replace("_", " ").title().replace(" ", "")
            if enum_class_name == "ImageStyle":
                enum_cls = schemas.ImageStyle
            elif enum_class_name == "WordToPictureRatio":
                enum_cls = schemas.WordToPictureRatio
            elif enum_class_name == "TextDensity":
                enum_cls = schemas.TextDensity
            else:
                enum_cls = None

            if enum_cls and isinstance(value, str):
                # Store the .value for enums
                setattr(db_story_draft, key, enum_cls(value).value)
            elif enum_cls and isinstance(value, enum_cls):
                setattr(db_story_draft, key, value.value)
            else:
                # Fallback for other types or if enum not found
                setattr(db_story_draft, key, value)
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
        db.commit()
        db.refresh(db_story)
        return db_story
    return None

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
    """
    Retrieves a single user by ID for admin purposes.
    """
    return db.query(User).filter(User.id == user_id).first()


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


def delete_user_admin(db: Session, user_id: int) -> bool:
    """
    Deletes a user by ID by admin.
    Returns True if deletion was successful, False otherwise.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user:
        # Consider implications: what happens to stories owned by this user?
        # For now, direct delete. Add cascading or re-assignment logic if needed.
        db.delete(db_user)
        db.commit()
        return True
    return False

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

    # Delete existing pages to prevent duplicates
    db.query(Page).filter(Page.story_id == story_id).delete(
        synchronize_session=False)

    # Create new pages
    if 'Pages' in story_content and isinstance(story_content['Pages'], list):
        for page_data in story_content['Pages']:
            page_number_str = str(page_data.get('Page_number'))

            new_page = Page(
                story_id=story_id,
                page_number=page_number_str,
                text=page_data.get('Text'),
                image_description=page_data.get('Image_description'),
                characters_in_scene=jsonable_encoder(
                    page_data.get('Characters_in_scene', [])),
                image_path=page_data.get('image_url')
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
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


def get_story_generation_task(db: Session, task_id: str) -> Optional[StoryGenerationTask]:
    return db.query(StoryGenerationTask).filter(StoryGenerationTask.id == task_id).first()


def update_story_generation_task(
    db: Session,
    task_id: str,
    status: Optional[schemas.GenerationTaskStatus] = None,
    progress: Optional[int] = None,
    current_step: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[StoryGenerationTask]:
    task = get_story_generation_task(db, task_id)
    if not task:
        return None

    if status is not None:
        task.status = status.value
    if progress is not None:
        task.progress = progress
    if current_step is not None:
        task.current_step = current_step
    if error_message is not None:
        task.error_message = error_message

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
