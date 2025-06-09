import pytest
from sqlalchemy.orm import Session
from backend import crud, schemas
from backend.database import User  # For type hinting and checking instance

# Test User Creation


def test_create_user(db_session: Session):
    user_in = schemas.UserCreate(
        username="testuser", password="testpassword", email="testuser@example.com")
    db_user = crud.create_user(db=db_session, user=user_in)
    assert db_user is not None
    assert db_user.username == "testuser"
    assert db_user.email == "testuser@example.com"
    assert hasattr(db_user, "hashed_password")
    assert crud.pwd_context.verify("testpassword", db_user.hashed_password)
    assert isinstance(db_user, User)

# Test Get User by ID


def test_get_user(db_session: Session):
    user_in = schemas.UserCreate(
        username="testuser_getid", password="password123", email="getid@example.com")
    created_user = crud.create_user(db=db_session, user=user_in)
    retrieved_user = crud.get_user(db=db_session, user_id=created_user.id)
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == "testuser_getid"


def test_get_user_non_existent(db_session: Session):
    retrieved_user = crud.get_user(db=db_session, user_id=99999)
    assert retrieved_user is None

# Test Get User by Username


def test_get_user_by_username(db_session: Session):
    user_in = schemas.UserCreate(
        username="testuser_getusername", password="password456", email="getusername@example.com")
    created_user = crud.create_user(db=db_session, user=user_in)
    retrieved_user = crud.get_user_by_username(
        db=db_session, username="testuser_getusername")
    assert retrieved_user is not None
    assert retrieved_user.username == created_user.username
    assert retrieved_user.id == created_user.id


def test_get_user_by_username_non_existent(db_session: Session):
    retrieved_user = crud.get_user_by_username(
        db=db_session, username="nonexistentuser")
    assert retrieved_user is None

# Test Duplicate Username Creation


def test_create_user_duplicate_username(db_session: Session):
    user_in1 = schemas.UserCreate(
        username="duplicateuser", password="pass1", email="dup1@example.com")
    crud.create_user(db=db_session, user=user_in1)

    user_in2 = schemas.UserCreate(
        username="duplicateuser", password="pass2", email="dup2@example.com")

    with pytest.raises(Exception):  # Ideally, catch sqlalchemy.exc.IntegrityError
        crud.create_user(db=db_session, user=user_in2)
        # The commit is inside crud.create_user, so the error happens there.
        # No need for an explicit db_session.commit() here in the test if crud.create_user handles it.

    db_session.rollback()  # Add rollback here to clear the session state

    # Verify only one user with that username exists
    users_count = db_session.query(User).filter(
        User.username == "duplicateuser").count()
    assert users_count == 1

# Test User Creation with Role and Active Status


def test_create_user_with_defaults(db_session: Session):
    user_in = schemas.UserCreate(username="defaultuser", password="password")
    db_user = crud.create_user(db=db_session, user=user_in)
    assert db_user.username == "defaultuser"
    assert db_user.role == "user"  # Default role
    assert db_user.is_active is True  # Default active status
    assert db_user.email is None  # Ensure email is None if not provided


def test_create_user_with_specific_role_and_status(db_session: Session):
    user_in = schemas.UserCreate(
        username="adminuser_specific_test",  # Changed username for clarity
        password="adminpassword",
        email="testadmin@example.com",  # Changed email to avoid conflict
        role="admin",
        is_active=False
    )
    db_user = crud.create_user(db=db_session, user=user_in)
    assert db_user is not None
    assert db_user.username == "adminuser_specific_test"
    assert db_user.email == "testadmin@example.com"
    assert db_user.role == "admin"
    assert db_user.is_active is False

    # Verify password (optional, as it's hashed)
    # This requires a verification function, e.g., from auth.py if available and suitable
    # from backend.auth import verify_password # Assuming verify_password exists
    # assert verify_password("adminpassword", db_user.hashed_password)

    # Clean up (optional, if db is not reset per test, but db_session fixture should handle it)
    # db_session.delete(db_user)
    # db_session.commit()


def test_create_user_role_is_none(db_session: Session):
    # Explicitly set role to None, should default to "user"
    user_in = schemas.UserCreate(
        username="testroleNone", password="password", role=None)
    db_user = crud.create_user(db=db_session, user=user_in)
    assert db_user.role == "user"


def test_create_user_is_active_is_none(db_session: Session):
    # Explicitly set is_active to None, should default to True
    user_in = schemas.UserCreate(
        username="testactiveNone", password="password", is_active=None)
    db_user = crud.create_user(db=db_session, user=user_in)
    assert db_user.is_active is True

# Test Admin Update User


def test_admin_update_user_all_fields(db_session: Session):
    # 1. Create a user to update
    user_to_update = crud.create_user(db_session, schemas.UserCreate(
        username="user_to_update_all",
        password="initialpass",
        email="initial@example.com",
        role="user",
        is_active=True
    ))
    assert user_to_update is not None

    # 2. Define the updates
    update_data = schemas.UserUpdateAdmin(
        username="updated_username_all",
        email="updated_all@example.com",
        role="admin",
        is_active=False
    )

    # 3. Perform the update
    updated_user = crud.admin_update_user(
        db_session, user_id=user_to_update.id, user_update=update_data)
    assert updated_user is not None

    # 4. Verify the changes
    assert updated_user.username == "updated_username_all"
    assert updated_user.email == "updated_all@example.com"
    assert updated_user.role == "admin"
    assert updated_user.is_active is False
    # Password should not be changed by this function
    assert crud.pwd_context.verify("initialpass", updated_user.hashed_password)


def test_admin_update_user_partial_fields(db_session: Session):
    # 1. Create a user
    user_to_update = crud.create_user(db_session, schemas.UserCreate(
        username="user_to_update_partial",
        password="initialpass_partial",
        email="initial_partial@example.com",
        role="user",
        is_active=True
    ))
    assert user_to_update is not None

    # 2. Define partial updates (only email and role)
    update_data = schemas.UserUpdateAdmin(
        email="updated_partial@example.com",
        role="admin"
    )

    # 3. Perform the update
    updated_user = crud.admin_update_user(
        db_session, user_id=user_to_update.id, user_update=update_data)
    assert updated_user is not None

    # 4. Verify changes and non-changes
    assert updated_user.username == "user_to_update_partial"  # Should not change
    assert updated_user.email == "updated_partial@example.com"  # Should change
    assert updated_user.role == "admin"  # Should change
    assert updated_user.is_active is True  # Should not change


def test_admin_update_user_no_changes(db_session: Session):
    # 1. Create a user
    user_to_update = crud.create_user(db_session, schemas.UserCreate(
        username="user_no_change",
        password="password_no_change",
        email="no_change@example.com",
        role="user",
        is_active=True
    ))
    assert user_to_update is not None

    # 2. Define an empty update (no fields provided)
    update_data = schemas.UserUpdateAdmin()

    # 3. Perform the update
    updated_user = crud.admin_update_user(
        db_session, user_id=user_to_update.id, user_update=update_data)
    assert updated_user is not None

    # 4. Verify no fields changed
    assert updated_user.username == "user_no_change"
    assert updated_user.email == "no_change@example.com"
    assert updated_user.role == "user"
    assert updated_user.is_active is True


def test_admin_update_non_existent_user(db_session: Session):
    update_data = schemas.UserUpdateAdmin(username="ghost_user")
    updated_user = crud.admin_update_user(
        db_session, user_id=999999, user_update=update_data)
    assert updated_user is None
