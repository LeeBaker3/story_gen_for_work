#!/usr/bin/env python3
"""Admin bootstrap utility.

This script creates the first admin user (or promotes an existing user) in an
idempotent way.

Design goals:
- No hard-coded credentials.
- Safe defaults (won't silently reset passwords).
- Works with the same DATABASE_URL the app uses.
"""

from __future__ import annotations

import argparse
import os
import sys
from getpass import getpass
from typing import Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend import crud
from backend.auth import get_password_hash
from backend.database import Base
from backend.schemas import UserCreate


def _create_sessionmaker(database_url: str) -> sessionmaker:
    """Create a SQLAlchemy Session factory for the given database URL."""

    connect_args = (
        {"check_same_thread": False}
        if database_url.startswith("sqlite")
        else {}
    )
    engine = create_engine(database_url, connect_args=connect_args)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_admin_user(
    db: Session,
    *,
    username: str,
    email: Optional[str],
    password: Optional[str],
    create_if_missing: bool,
    promote_existing: bool,
    set_password: bool,
) -> Tuple[object, str]:
    """Create or promote a user to admin.

    Parameters:
        db: SQLAlchemy session.
        username: Username to look up (and create if missing).
        email: Email for newly-created users.
        password: Plaintext password for newly-created users, or when updating.
        create_if_missing: If False, error when user doesn't exist.
        promote_existing: If True, promote existing users to admin.
        set_password: If True, update password for existing user (requires password).

    Returns:
        (user, action): The user object and a short action string.

    Raises:
        ValueError: on invalid arguments or missing prerequisites.
    """

    username = username.strip()
    if not username:
        raise ValueError("username is required")

    user = crud.get_user_by_username(db, username=username)
    if user is None:
        if not create_if_missing:
            raise ValueError(
                f"User '{username}' not found and --no-create-if-missing was set")
        if not password:
            raise ValueError("password is required to create a new admin user")

        admin_data = UserCreate(
            username=username,
            email=email,
            password=password,
            role="admin",
            is_active=True,
        )
        user = crud.create_user(db, admin_data)
        # Ensure soft-delete is cleared in case this username ever existed.
        if getattr(user, "is_deleted", False):
            user.is_deleted = False
            db.commit()
            db.refresh(user)
        return user, "created"

    changed = False

    if promote_existing and getattr(user, "role", "user") != "admin":
        user.role = "admin"
        changed = True

    # Ensure admin can log in.
    if getattr(user, "is_active", True) is False:
        user.is_active = True
        changed = True

    # Undo soft delete when bootstrapping.
    if getattr(user, "is_deleted", False) is True:
        user.is_deleted = False
        changed = True

    if set_password:
        if not password:
            raise ValueError(
                "--set-password requires --password (or --prompt-password)")
        user.hashed_password = get_password_hash(password)
        changed = True

    if changed:
        db.commit()
        db.refresh(user)
        return user, "updated"

    return user, "noop"


def _resolve_password(args: argparse.Namespace) -> Optional[str]:
    if args.password:
        return args.password

    # Allow non-interactive CI usage via env.
    env_password = os.getenv("ADMIN_PASSWORD") or os.getenv(
        "CREATE_ADMIN_PASSWORD")
    if env_password:
        return env_password

    if args.prompt_password:
        pw1 = getpass("Admin password: ")
        pw2 = getpass("Confirm password: ")
        if pw1 != pw2:
            raise ValueError("Passwords did not match")
        return pw1

    return None


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(
        description="Create or promote an admin user")
    parser.add_argument(
        "--username",
        "-u",
        help="Username to create/promote (defaults to --email if omitted)",
        default=None,
    )
    parser.add_argument(
        "--email",
        "-e",
        help="Email (used when creating a new user)",
        default=None,
    )
    parser.add_argument(
        "--password",
        help="Admin password (prefer env ADMIN_PASSWORD or --prompt-password)",
        default=None,
    )
    parser.add_argument(
        "--prompt-password",
        action="store_true",
        help="Prompt for password securely (recommended)",
    )
    parser.add_argument(
        "--set-password",
        action="store_true",
        help="Update the password if the user already exists",
    )
    parser.add_argument(
        "--no-create-if-missing",
        action="store_true",
        help="Fail if the user does not already exist",
    )
    parser.add_argument(
        "--no-promote-existing",
        action="store_true",
        help="Do not change role for existing users",
    )
    parser.add_argument(
        "--db-url",
        help="Override DATABASE_URL for this run",
        default=None,
    )

    args = parser.parse_args(argv)

    username = args.username or args.email
    if not username:
        parser.error("Provide --username or --email")

    password = _resolve_password(args)

    # Ensure the DB schema exists (safe no-op if already created).
    database_url = args.db_url or os.getenv(
        "DATABASE_URL", "sqlite:///./story_generator.db")
    SessionLocal = _create_sessionmaker(database_url)
    Base.metadata.create_all(bind=SessionLocal.kw["bind"])

    db = SessionLocal()
    try:
        user, action = ensure_admin_user(
            db,
            username=username,
            email=args.email,
            password=password,
            create_if_missing=not args.no_create_if_missing,
            promote_existing=not args.no_promote_existing,
            set_password=bool(args.set_password),
        )
        print(
            f"{action}: username={getattr(user, 'username', None)} role={getattr(user, 'role', None)} is_active={getattr(user, 'is_active', None)}"
        )
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
