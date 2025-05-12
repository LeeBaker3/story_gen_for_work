from sqlalchemy.orm import Session
from . import schemas
from .database import User, Story, Page
from passlib.context import CryptContext
from typing import List, Optional
from fastapi.encoders import jsonable_encoder  # Added for JSON conversion

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User CRUD


def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Story CRUD
# Modified to handle StoryCreate which doesn't have a title initially
# The title will be populated after AI generation


def create_story_db_entry(db: Session, story_data: schemas.StoryBase, user_id: int, title: str):
    """
    Creates the story entry in the database.
    The main story content (pages) will be added separately after AI generation.
    """
    db_story = Story(
        title=title,  # Title is now passed explicitly
        genre=story_data.genre,
        # Changed from outline to story_outline
        story_outline=story_data.story_outline,
        # Encode list of Pydantic models to JSON
        main_characters=jsonable_encoder(story_data.main_characters),
        num_pages=story_data.num_pages,
        tone=story_data.tone,
        setting=story_data.setting,
        owner_id=user_id
    )
    db.add(db_story)
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
            **page_data.dict(),
            story_id=story_id,
            image_path=image_path
        )
        db.add(db_page)
    db.commit()


def get_stories_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 10):
    return db.query(Story).filter(Story.owner_id == user_id).offset(skip).limit(limit).all()


def get_story(db: Session, story_id: int):
    return db.query(Story).filter(Story.id == story_id).first()

# Page CRUD (will be used internally when story is generated)


def create_story_page(db: Session, page: schemas.PageCreate, story_id: int, image_path: Optional[str] = None):
    db_page = Page(**page.dict(), story_id=story_id, image_path=image_path)
    db.add(db_page)
    db.commit()
    db.refresh(db_page)
    return db_page
