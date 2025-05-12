from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# This will be ideally read from .env
DATABASE_URL = "sqlite:///./story_generator.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
    owner_id = Column(Integer, ForeignKey("users.id"))
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
