from backend.main import app
from backend.database_seeding import seed_database, is_database_empty
import backend.database_seeding as database_seeding
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
    text_positions_count = db_session.query(
        DynamicListItem).filter_by(list_name='text_positions').count()
    font_families_count = db_session.query(
        DynamicListItem).filter_by(list_name='font_families').count()

    assert genres_count > 5
    assert image_styles_count > 5
    assert text_positions_count == 9
    assert font_families_count >= 6
    assert db_session.query(DynamicList).count() >= 4


def test_seed_database_on_non_empty_db(db_session: Session):
    """Test that seed_database preserves existing rows and backfills defaults."""
    # Pre-populate the database
    db_session.add(DynamicList(list_name="existing_list",
                   list_label="Existing List"))
    db_session.commit()

    initial_count = db_session.query(DynamicList).count()
    assert initial_count == 1

    # Run the seeder, which should preserve existing rows and add defaults.
    seed_database(db=db_session)

    # Verify the pre-existing list remains and default lists are backfilled.
    assert db_session.query(DynamicList).count() > initial_count
    assert db_session.query(DynamicList).filter_by(
        list_name="existing_list"
    ).count() == 1
    assert db_session.query(DynamicList).filter_by(list_name="genres").count() == 1
    assert db_session.query(DynamicListItem).filter_by(list_name="genres").count() > 0


def test_seed_database_backfills_partial_existing_data(db_session: Session):
    """Test that reseeding backfills missing defaults without overwriting existing items."""
    existing_genre = DynamicList(
        list_name="genres",
        list_label="Custom Genres",
    )
    existing_position = DynamicList(
        list_name="text_positions",
        list_label="Custom Text Positions",
    )
    db_session.add_all([existing_genre, existing_position])
    db_session.flush()
    db_session.add_all(
        [
            DynamicListItem(
                list_name="genres",
                item_value="Fantasy",
                item_label="Existing Fantasy Label",
                is_active=False,
                sort_order=99,
                additional_config={"source": "preexisting"},
            ),
            DynamicListItem(
                list_name="text_positions",
                item_value="top-left",
                item_label="Already Present",
                is_active=False,
                sort_order=77,
                additional_config={"source": "preexisting"},
            ),
        ]
    )
    db_session.commit()

    seed_database(db=db_session)

    fantasy_item = db_session.query(DynamicListItem).filter_by(
        list_name="genres",
        item_value="Fantasy",
    ).one()
    top_left_item = db_session.query(DynamicListItem).filter_by(
        list_name="text_positions",
        item_value="top-left",
    ).one()

    assert db_session.query(DynamicList).filter_by(list_name="genres").count() == 1
    assert db_session.query(DynamicListItem).filter_by(list_name="genres").count() == 10
    assert db_session.query(DynamicListItem).filter_by(
        list_name="text_positions"
    ).count() == 9
    assert fantasy_item.item_label == "Existing Fantasy Label"
    assert fantasy_item.is_active is False
    assert fantasy_item.sort_order == 99
    assert fantasy_item.additional_config == {"source": "preexisting"}
    assert top_left_item.item_label == "Already Present"
    assert top_left_item.is_active is False
    assert top_left_item.sort_order == 77


def test_seed_database_is_idempotent_on_reseed(db_session: Session):
    """Test that running the seeder multiple times does not duplicate defaults."""
    seed_database(db=db_session)

    first_list_count = db_session.query(DynamicList).count()
    first_item_count = db_session.query(DynamicListItem).count()
    first_genres_count = db_session.query(DynamicListItem).filter_by(
        list_name="genres"
    ).count()
    first_positions_count = db_session.query(DynamicListItem).filter_by(
        list_name="text_positions"
    ).count()

    seed_database(db=db_session)

    assert db_session.query(DynamicList).count() == first_list_count
    assert db_session.query(DynamicListItem).count() == first_item_count
    assert db_session.query(DynamicListItem).filter_by(
        list_name="genres"
    ).count() == first_genres_count
    assert db_session.query(DynamicListItem).filter_by(
        list_name="text_positions"
    ).count() == first_positions_count
    assert db_session.query(DynamicListItem).filter_by(
        list_name="genres",
        item_value="Fantasy",
    ).count() == 1
    assert db_session.query(DynamicListItem).filter_by(
        list_name="text_positions",
        item_value="top-left",
    ).count() == 1


def test_seed_database_rolls_back_when_reseeding_fails_mid_run(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that a mid-run failure rolls back pending default inserts."""
    db_session.add(DynamicList(list_name="existing_list", list_label="Existing List"))
    db_session.commit()

    original_add = db_session.add

    def failing_add(instance):
        if (
            isinstance(instance, DynamicListItem)
            and instance.list_name == "genres"
            and instance.item_value == "Drama"
        ):
            raise RuntimeError("simulated seeding failure")
        return original_add(instance)

    monkeypatch.setattr(db_session, "add", failing_add)

    seed_database(db=db_session)

    assert db_session.query(DynamicList).count() == 1
    assert db_session.query(DynamicList).filter_by(
        list_name="existing_list"
    ).count() == 1
    assert db_session.query(DynamicList).filter_by(list_name="genres").count() == 0
    assert db_session.query(DynamicListItem).count() == 0


def test_seed_database_on_empty_db_without_sql_script(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test that fresh-install seeding falls back to ORM defaults when the SQL script is missing."""
    monkeypatch.setattr(database_seeding.os.path, "exists", lambda _: False)

    seed_database(db=db_session)

    assert db_session.query(DynamicList).filter_by(list_name="genres").count() == 1
    assert db_session.query(DynamicListItem).filter_by(list_name="genres").count() > 0
    assert db_session.query(DynamicList).filter_by(
        list_name="text_positions"
    ).count() == 1
    assert db_session.query(DynamicListItem).filter_by(
        list_name="text_positions"
    ).count() == 9
