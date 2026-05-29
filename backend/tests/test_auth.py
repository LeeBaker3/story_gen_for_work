"""Dedicated unit tests for authentication helpers and dependencies."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from backend import auth, crud, schemas


def _create_test_user(
    db_session: Session,
    username: str,
    password: str,
    *,
    email: str | None = None,
    is_active: bool = True,
    role: str = "user",
):
    """Create a test user and optionally override mutable auth fields."""

    created_user = crud.create_user(
        db_session,
        schemas.UserCreate(
            username=username,
            email=email or username,
            password=password,
            is_active=is_active,
            role=role,
        ),
    )
    if created_user.role != role:
        created_user.role = role
        db_session.commit()
        db_session.refresh(created_user)
    return created_user


def test_authenticate_user_valid_credentials(db_session: Session) -> None:
    """Valid credentials should return the matching user record."""

    user = auth.authenticate_user(
        db_session,
        username="user@example.com",
        password="userpassword",
    )

    assert user is not None
    assert user.email == "user@example.com"


def test_authenticate_user_wrong_password(db_session: Session) -> None:
    """Wrong passwords should not authenticate a user."""

    user = auth.authenticate_user(
        db_session,
        username="user@example.com",
        password="wrong-password",
    )

    assert user in (None, False)


def test_authenticate_user_unknown_username(db_session: Session) -> None:
    """Unknown usernames should not authenticate a user."""

    user = auth.authenticate_user(
        db_session,
        username="missing@example.com",
        password="irrelevant",
    )

    assert user in (None, False)


def test_create_access_token_contains_sub() -> None:
    """The generated JWT should preserve the provided subject claim."""

    token = auth.create_access_token(data={"sub": "user@example.com"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

    assert payload["sub"] == "user@example.com"


def test_create_access_token_uses_default_sixty_minute_expiry() -> None:
    """The default token expiry should be about one hour from issuance."""

    issued_at = datetime.now(UTC)
    token = auth.create_access_token(data={"sub": "user@example.com"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
    expires_in = expires_at - issued_at

    assert timedelta(minutes=59) <= expires_in <= timedelta(minutes=61)


def test_get_current_user_valid_token(db_session: Session) -> None:
    """A valid token should resolve to the matching user."""

    token = auth.create_access_token(data={"sub": "user@example.com"})

    user = asyncio.run(auth.get_current_user(token=token, db=db_session))

    assert user.email == "user@example.com"


def test_get_current_user_expired_token(db_session: Session) -> None:
    """Expired tokens should be rejected with 401."""

    expired_token = jwt.encode(
        {
            "sub": "user@example.com",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_user(token=expired_token, db=db_session))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_invalid_signature(db_session: Session) -> None:
    """Tokens signed with a different secret should be rejected with 401."""

    invalid_token = jwt.encode(
        {
            "sub": "user@example.com",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "wrong-secret",
        algorithm=auth.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_user(token=invalid_token, db=db_session))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_malformed_token(db_session: Session) -> None:
    """Malformed JWT strings should be rejected with 401."""

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_user(token="not-a-jwt", db=db_session))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_user_missing_sub(db_session: Session) -> None:
    """Tokens without a subject should be rejected with 401."""

    missing_sub_token = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(minutes=5)},
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_user(
            token=missing_sub_token, db=db_session))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_get_current_active_user_inactive_user(db_session: Session) -> None:
    """Inactive users should be rejected by the active-user dependency."""

    inactive_user = _create_test_user(
        db_session,
        username="inactive@example.com",
        email="inactive@example.com",
        password="inactive-password",
        is_active=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_active_user(current_user=inactive_user))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Inactive user"


def test_get_current_admin_user_non_admin(db_session: Session) -> None:
    """Non-admin users should be rejected by the admin dependency."""

    regular_user = _create_test_user(
        db_session,
        username="member@example.com",
        email="member@example.com",
        password="member-password",
        role="user",
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.get_current_admin_user(current_user=regular_user))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


def test_get_current_admin_user_admin(db_session: Session) -> None:
    """Admin users should pass the admin dependency unchanged."""

    admin_user = _create_test_user(
        db_session,
        username="local-admin@example.com",
        email="local-admin@example.com",
        password="admin-password",
        role="admin",
    )

    current_user = asyncio.run(
        auth.get_current_admin_user(current_user=admin_user))

    assert current_user.id == admin_user.id
    assert current_user.role == "admin"


def test_issue_password_reset_token_persists_hashed_token(
    db_session: Session,
) -> None:
    """Issuing a reset token should persist only its hash and expiry."""

    user = _create_test_user(
        db_session,
        username="resettable@example.com",
        email="resettable@example.com",
        password="initial-password",
    )

    token, expires_at = auth.issue_password_reset_token(db_session, user)
    db_session.refresh(user)

    assert token
    assert user.password_reset_token_hash == auth.hash_password_reset_token(
        token)
    assert user.password_reset_token_hash != token
    assert user.password_reset_token_expires_at is not None
    stored_expires_at = user.password_reset_token_expires_at
    if (
        stored_expires_at.tzinfo is None
        or stored_expires_at.tzinfo.utcoffset(stored_expires_at) is None
    ):
        stored_expires_at = stored_expires_at.replace(tzinfo=UTC)
    assert stored_expires_at <= expires_at


def test_get_valid_password_reset_user_rejects_expired_tokens(
    db_session: Session,
) -> None:
    """Expired reset tokens should be rejected and cleared."""

    user = _create_test_user(
        db_session,
        username="expired-reset@example.com",
        email="expired-reset@example.com",
        password="initial-password",
    )
    token, _ = auth.issue_password_reset_token(db_session, user)
    user.password_reset_token_expires_at = datetime.now(
        UTC) - timedelta(minutes=1)
    db_session.commit()
    db_session.refresh(user)

    resolved_user = auth.get_valid_password_reset_user(db_session, token)
    db_session.refresh(user)

    assert resolved_user is None
    assert user.password_reset_token_hash is None
    assert user.password_reset_token_expires_at is None
