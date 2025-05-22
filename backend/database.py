from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON, DateTime, Boolean  # Added Boolean
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
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True,
                   nullable=True)  # Added email column
    hashed_password = Column(String, nullable=False)
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
    story = relationship("Story", back_populates="pages")


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
