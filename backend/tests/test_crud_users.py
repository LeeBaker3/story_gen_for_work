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
