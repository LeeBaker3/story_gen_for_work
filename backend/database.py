from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, DateTime, Boolean, UniqueConstraint  # Added Boolean
# Import declarative_base from sqlalchemy.orm
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

# This will be ideally read from .env
DATABASE_URL = "sqlite:///./story_generator.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # Use the imported declarative_base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    # Made email unique and nullable
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)  # New field
    role = Column(String, default="user")  # New field (e.g., "user", "admin")

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
    list_name = Column(String, ForeignKey(
        "dynamic_lists.list_name"), nullable=False)
    # The actual value, e.g., "sci_fi", "watercolor"
    item_value = Column(String, nullable=False)
    # User-friendly label, e.g., "Science Fiction", "Watercolor Art"
    item_label = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    # Optional: for specific mappings like OpenAI style 'vivid'/'natural'
    additional_config = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    parent_list = relationship("DynamicList", back_populates="items")

    # Add a unique constraint for item_value within a list_name
    __table_args__ = (UniqueConstraint(
        'list_name', 'item_value', name='_list_name_item_value_uc'),)


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
