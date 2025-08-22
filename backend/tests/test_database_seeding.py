from backend.main import app
from backend.database_seeding import seed_database, is_database_empty
from backend.database import Base, DynamicList, DynamicListItem
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)

# Fixture to create a new database for each test function


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_is_database_empty(db_session: Session):
    """Test the helper function that checks if the DB is empty."""
    # Initially, the database should be empty
    assert is_database_empty(db_session) == True

    # Add a dummy list and check again
    db_session.add(DynamicList(list_name="test_list", list_label="Test List"))
    db_session.commit()
    assert is_database_empty(db_session) == False


def test_seed_database_on_empty_db(db_session: Session):
    """Test that seed_database populates an empty database."""
    # Ensure the database is empty before seeding
    assert db_session.query(DynamicList).count() == 0

    # Run the seeder function, passing the test session
    seed_database(db=db_session)

    # Now, check if the data was seeded correctly
    genres_count = db_session.query(
        DynamicListItem).filter_by(list_name='genres').count()
    image_styles_count = db_session.query(
        DynamicListItem).filter_by(list_name='image_styles').count()

    assert genres_count > 5
    assert image_styles_count > 5
    assert db_session.query(DynamicList).count() >= 2


def test_seed_database_on_non_empty_db(db_session: Session):
    """Test that seed_database does not run if the database is not empty."""
    # Pre-populate the database
    db_session.add(DynamicList(list_name="existing_list",
                   list_label="Existing List"))
    db_session.commit()

    initial_count = db_session.query(DynamicList).count()
    assert initial_count == 1

    # Run the seeder, which should do nothing
    seed_database(db=db_session)

    # Verify no new data was added
    assert db_session.query(DynamicList).count() == initial_count
