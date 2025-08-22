import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, DateTime, Boolean, UniqueConstraint, Enum  # Added Boolean
# Import declarative_base from sqlalchemy.orm
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load .env for local development (harmless in prod/CI)
load_dotenv()

# DATABASE_URL can be provided via environment; default to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./story_generator.db")

# For SQLite, we must pass check_same_thread=False for SQLAlchemy in multi-threaded apps
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith(
    "sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # Use the imported declarative_base


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    # Made email unique and nullable
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)  # New field
    role = Column(String, default="user")  # New field (e.g., "user", "admin")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    stories = relationship("Story", back_populates="owner")


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    story_outline = Column(Text, nullable=True)  # Changed from outline
    genre = Column(String, nullable=False)
    main_characters = Column(JSON, nullable=True)
    num_pages = Column(Integer, nullable=False, default=0)
    tone = Column(String, nullable=True)
    setting = Column(String, nullable=True)
    # FR14: Added image_style column
    image_style = Column(String, nullable=True, default="Default")
    # FR13: Added word_to_picture_ratio column
    word_to_picture_ratio = Column(
        String, nullable=True, default="One image per page")
    # New Req: Added text_density column
    text_density = Column(String, nullable=True,
                          default="Concise")  # Default to Concise
    owner_id = Column(Integer, ForeignKey("users.id"))
    # Represents draft creation or story generation time
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    # Time of actual story generation, null for drafts
    generated_at = Column(DateTime(timezone=True), nullable=True)
    # True if story is a draft, False if generated
    is_draft = Column(Boolean, default=True, nullable=False)

    owner = relationship("User", back_populates="stories")
    pages = relationship("Page", back_populates="story",
                         cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"))
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    image_description = Column(Text, nullable=True)  # Prompt for DALL-E
    image_path = Column(String, nullable=True)  # Path to locally stored image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    story = relationship("Story", back_populates="pages")

# New Models for Dynamic Lists (FR-ADM-05)


class DynamicList(Base):
    __tablename__ = "dynamic_lists"

    # e.g., "genres", "image_styles"
    list_name = Column(String, primary_key=True, index=True)
    list_label = Column(String, nullable=True)  # User-friendly label
    # Optional description of the list's purpose
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    items = relationship(
        "DynamicListItem", back_populates="parent_list", cascade="all, delete-orphan")


class DynamicListItem(Base):
    __tablename__ = "dynamic_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_name = Column(String, ForeignKey("dynamic_lists.list_name"))
    item_value = Column(String, nullable=False)  # The actual value of the item
    item_label = Column(String, nullable=True)  # Optional user-friendly label
    is_active = Column(Boolean, default=True)
    # For ordering items within a list
    sort_order = Column(Integer, default=100)
    additional_config = Column(JSON, nullable=True)  # For extra configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    parent_list = relationship("DynamicList", back_populates="items")

    __table_args__ = (UniqueConstraint(
        'list_name', 'item_value', name='_list_value_uc'),)


class StoryGenerationTask(Base):
    __tablename__ = 'story_generation_tasks'

    id = Column(String, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(String, nullable=False, default='PENDING')
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())

    story = relationship("Story")
    user = relationship("User")


# --- Characters Domain (Phase 2) ---


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    clothing_style = Column(String, nullable=True)
    key_traits = Column(Text, nullable=True)
    image_style = Column(String, nullable=True)
    # use_alter=True marks this FK as part of a known cycle so metadata.drop/create won't warn
    current_image_id = Column(
        Integer,
        ForeignKey("character_images.id", use_alter=True,
                   name="fk_characters_current_image_id"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    owner = relationship("User")
    images = relationship(
        "CharacterImage",
        back_populates="character",
        cascade="all, delete-orphan",
        # Disambiguate: CharacterImage.character_id points to Character.id
        foreign_keys="CharacterImage.character_id",
        primaryjoin=lambda: Character.id == CharacterImage.character_id,
    )
    current_image = relationship(
        "CharacterImage",
        foreign_keys=[current_image_id],
        post_update=True,
        uselist=False,
    )


class CharacterImage(Base):
    __tablename__ = "character_images"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", use_alter=True,
                   name="fk_character_images_character_id"),
        nullable=False,
        index=True,
    )
    # Relative to data/ (e.g., images/user_1/characters/5/uuid.png)
    file_path = Column(String, nullable=False)
    prompt_used = Column(Text, nullable=True)
    image_style = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Disambiguate relationship path back to Character
    character = relationship(
        "Character",
        back_populates="images",
        foreign_keys=[character_id],
        primaryjoin=lambda: CharacterImage.character_id == Character.id,
    )


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
