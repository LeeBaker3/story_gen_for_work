"""Tests for the admin bootstrap helper in create_admin.py."""

from __future__ import annotations

import pytest

from backend.database import User

import create_admin


def test_ensure_admin_user_creates_new_admin(db_session):
    """Creates a new admin when the user does not exist."""

    user, action = create_admin.ensure_admin_user(
        db_session,
        username="bootstrap_admin@example.com",
        email="bootstrap_admin@example.com",
        password="secret123",
        create_if_missing=True,
        promote_existing=True,
        set_password=False,
    )

    assert action == "created"
    assert user.username == "bootstrap_admin@example.com"
    assert user.role == "admin"
    assert user.is_active is True


def test_ensure_admin_user_promotes_existing(db_session):
    """Promotes an existing user to admin without changing password by default."""

    existing = User(
        username="existing@example.com",
        email="existing@example.com",
        hashed_password="hash",
        role="user",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(existing)
    db_session.commit()

    user, action = create_admin.ensure_admin_user(
        db_session,
        username="existing@example.com",
        email="existing@example.com",
        password=None,
        create_if_missing=True,
        promote_existing=True,
        set_password=False,
    )

    assert action == "updated"
    assert user.role == "admin"


def test_ensure_admin_user_noop_when_already_admin(db_session):
    """No changes when user is already admin and no password update requested."""

    existing = User(
        username="admin2@example.com",
        email="admin2@example.com",
        hashed_password="hash",
        role="admin",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(existing)
    db_session.commit()

    user, action = create_admin.ensure_admin_user(
        db_session,
        username="admin2@example.com",
        email="admin2@example.com",
        password=None,
        create_if_missing=True,
        promote_existing=True,
        set_password=False,
    )

    assert action == "noop"
    assert user.role == "admin"


def test_ensure_admin_user_set_password_requires_password(db_session):
    """Refuses to update password without a new password."""

    existing = User(
        username="pw@example.com",
        email="pw@example.com",
        hashed_password="hash",
        role="admin",
        is_active=True,
        is_deleted=False,
    )
    db_session.add(existing)
    db_session.commit()

    with pytest.raises(ValueError, match="requires --password"):
        create_admin.ensure_admin_user(
            db_session,
            username="pw@example.com",
            email="pw@example.com",
            password=None,
            create_if_missing=True,
            promote_existing=True,
            set_password=True,
        )
