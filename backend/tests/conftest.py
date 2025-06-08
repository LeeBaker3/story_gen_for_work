from datetime import timedelta  # Add this import
# Changed from backend.models to backend.database
# Changed from backend.database to backend.schemas
from backend.schemas import UserRole
from backend.auth import create_access_token, get_password_hash  # Add get_password_hash
from fastapi.testclient import TestClient  # Add this import
from typing import Generator
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, text  # Added text
import pytest
# Ensure all models are imported so Base.metadata is fully populated
# User here is the model
from backend.database import Base, User, Story, Page, DynamicList, DynamicListItem
from backend.database import get_db as database_get_db # Alias for database.get_db
from backend.main import app, get_db as main_get_db # Import app's get_db and alias
import sys  # Add sys import
from pathlib import Path  # Add pathlib import

# Add project root to sys.path to allow for absolute imports of backend module
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))


# Use an in-memory SQLite database for testing, shared across connections
SQLALCHEMY_DATABASE_URL = "sqlite:///file:testdb?mode=memory&cache=shared&uri=true"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Fixture to provide a database session for tests.
    Creates all tables, yields a session, and then drops all tables after the test.
    """
    # Ensure all models are imported so Base.metadata is fully populated
    # These imports are at top-level of conftest.py now.

    print(
        f"DEBUG: Tables in Base.metadata before create_all: {list(Base.metadata.tables.keys())}")
    if 'users' not in Base.metadata.tables:
        print("DEBUG: 'users' table is NOT in Base.metadata before create_all!")
    else:
        print("DEBUG: 'users' table IS in Base.metadata before create_all.")

    Base.metadata.create_all(bind=engine)
    print("DEBUG: Base.metadata.create_all(bind=engine) called.")

    # === BEGIN SQLITE_MASTER CHECK ===
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';"))
            # Sort for consistent order
            tables_in_db = sorted([row[0] for row in result])
            print(
                f"DEBUG: Tables found in sqlite_master after create_all: {tables_in_db}")
            # No explicit commit needed for SELECT with engine.connect() context manager
    except Exception as e:
        print(f"DEBUG: EXCEPTION during sqlite_master check: {e}")
    # === END SQLITE_MASTER CHECK ===

    db = TestingSessionLocal()
    try:
        # Create test users that correspond to admin_token and regular_user_token
        admin_user = User(
            username="admin@example.com",  # Corresponds to 'sub' in admin_token
            email="admin@example.com",
            # Dummy password, not used for auth in this flow
            hashed_password=get_password_hash("adminpassword"),
            role=UserRole.ADMIN.value,
            is_active=True
        )
        regular_user = User(
            username="user@example.com",  # Corresponds to 'sub' in regular_user_token
            email="user@example.com",
            hashed_password=get_password_hash(
                "userpassword"),  # Dummy password
            role=UserRole.USER.value,
            is_active=True
        )
        db.add(admin_user)
        db.add(regular_user)
        db.commit()
        db.refresh(admin_user)  # Get IDs
        db.refresh(regular_user)  # Get IDs
        print(
            f"DEBUG: Created admin user 'admin@example.com' (ID: {admin_user.id}) in fixture.")
        print(
            f"DEBUG: Created regular user 'user@example.com' (ID: {regular_user.id}) in fixture.")

        # === BEGIN DIAGNOSTIC CODE FOR DynamicList ===
        print("DEBUG: Attempting to create and retrieve a test DynamicList directly in db_session fixture...")
        try:
            # DynamicList is imported from backend.database
            fixture_dl = DynamicList(
                list_name="fixture_dl_test",
                description="A test dynamic list created in fixture"
            )
            db.add(fixture_dl)
            db.commit()
            db.refresh(fixture_dl)
            print(
                f"DEBUG: DynamicList 'fixture_dl_test' (Description: {fixture_dl.description}) committed to DB in fixture.")

            retrieved_fixture_dl = db.query(DynamicList).filter(
                DynamicList.list_name == "fixture_dl_test").first()
            if retrieved_fixture_dl:
                print(
                    f"DEBUG: DynamicList 'fixture_dl_test' (Description: {retrieved_fixture_dl.description}) successfully retrieved from DB in fixture.")
            else:
                print(
                    "DEBUG: FAILED to retrieve 'fixture_dl_test' (DynamicList) from DB in fixture.")
        except Exception as e:
            print(f"DEBUG: EXCEPTION during fixture DynamicList test: {e}")
            import traceback
            traceback.print_exc()  # Print full traceback for this specific exception
        # === END DIAGNOSTIC CODE FOR DynamicList ===

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)  # Clean up tables
        print("DEBUG: Base.metadata.drop_all(bind=engine) called.")

# Override the get_db dependency for the FastAPI app


# Modified to accept the session from the fixture
def override_get_db(db: Session) -> Generator[Session, None, None]:
    try:
        yield db
    finally:
        # The db_session fixture is responsible for closing the session
        pass


# app.dependency_overrides[get_db] = override_get_db # Remove global override


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Fixture to provide a TestClient for the FastAPI app.
    Uses the db_session fixture to ensure a clean database for each test.
    Overrides both main.get_db and database.get_db dependencies.
    """
    # Store original overrides to restore them later
    original_main_get_db_override = app.dependency_overrides.get(main_get_db)
    original_database_get_db_override = app.dependency_overrides.get(database_get_db)

    # Override main.get_db (used by routes in main.py like the public one)
    app.dependency_overrides[main_get_db] = lambda: db_session
    # Override database.get_db (used by auth.py and potentially other modules)
    app.dependency_overrides[database_get_db] = lambda: db_session

    with TestClient(app) as c:
        yield c

    # Restore original overrides or clear them
    if original_main_get_db_override is not None:
        app.dependency_overrides[main_get_db] = original_main_get_db_override
    else:
        app.dependency_overrides.pop(main_get_db, None)

    if original_database_get_db_override is not None:
        app.dependency_overrides[database_get_db] = original_database_get_db_override
    else:
        app.dependency_overrides.pop(database_get_db, None)


@pytest.fixture(scope="session")
def admin_token() -> str:
    return create_access_token(
        data={"sub": "admin@example.com", "role": UserRole.ADMIN.value},
        expires_delta=timedelta(minutes=30)
    )


@pytest.fixture(scope="session")
def regular_user_token() -> str:
    return create_access_token(
        data={"sub": "user@example.com", "role": UserRole.USER.value},
        expires_delta=timedelta(minutes=30)
    )
