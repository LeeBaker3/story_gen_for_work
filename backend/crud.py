from sqlalchemy.orm import Session
from . import schemas
from .database import User, Story, Page
from passlib.context import CryptContext
from typing import List, Optional
from fastapi.encoders import jsonable_encoder  # Added for JSON conversion
# Ensure datetime and timezone are imported
from datetime import datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User CRUD


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, email=user.email,
                   hashed_password=hashed_password)  # Added user.email
    db.add(db_user)
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
    # The schema has a default, so story_data.word_to_picture_ratio should exist.
    word_to_picture_ratio_value = story_data.word_to_picture_ratio.value \
        if story_data.word_to_picture_ratio else schemas.WordToPictureRatio.PER_PAGE.value

    # Determine the string value for text_density (New Req)
    # The schema has a default, so story_data.text_density should exist.
    text_density_value = story_data.text_density.value \
        if story_data.text_density else schemas.TextDensity.CONCISE.value

    db_story = Story(
        title=title,  # Title can be None for drafts
        genre=story_data.genre,
        # Changed from outline to story_outline
        story_outline=story_data.story_outline,
        # Encode list of Pydantic models to JSON
        main_characters=jsonable_encoder(story_data.main_characters),
        num_pages=story_data.num_pages,
        tone=story_data.tone,
        setting=story_data.setting,
        # Added image_style
        image_style=story_data.image_style.value if story_data.image_style else "Default",
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
        genre=story_data.genre,
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


def get_story(db: Session, story_id: int):
    return db.query(Story).filter(Story.id == story_id).first()


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
