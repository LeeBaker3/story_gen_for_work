import os
from datetime import datetime, timedelta, UTC
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from . import crud, schemas
# Import the logger
from .logging_config import error_logger, app_logger
from .database import SessionLocal, get_db

load_dotenv()  # Load environment variables from .env file

SECRET_KEY = os.getenv(
    "SECRET_KEY", "your-default-secret-key")  # Should be in .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenData(BaseModel):
    username: Optional[str] = None


def verify_password(plain_password, hashed_password):
    error_logger.error(
        f"VERIFY_PWD: Inside. Plain type: {type(plain_password)}, Hashed type: {type(hashed_password)}")

    # Robust checks for input types and values
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        error_logger.error(
            f"VERIFY_PWD: Invalid types for plain_password ('{type(plain_password)}') or hashed_password ('{type(hashed_password)}'). Returning False.")
        return False
    if not plain_password:  # Check for empty plain password
        error_logger.error(
            f"VERIFY_PWD: Plain password is empty. Returning False.")
        return False
    if not hashed_password:  # Check for empty hashed password
        error_logger.error(
            f"VERIFY_PWD: Hashed password is empty. Returning False.")
        return False

    error_logger.error(
        f"VERIFY_PWD: Plain (first 3): '{plain_password[:3]}...', Hashed (first 10): '{hashed_password[:10]}...'")
    try:
        result = pwd_context.verify(plain_password, hashed_password)
        error_logger.error(f"VERIFY_PWD: pwd_context.verify result: {result}")
        return result
    except Exception as e:
        error_logger.error(
            f"VERIFY_PWD: Exception directly from pwd_context.verify: {e}", exc_info=True)
        return False  # Explicitly return False on exception


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(
            UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Add extensive logging here
    app_logger.info(
        f"GET_CURRENT_USER: Token received (first 10): {token[:10] if token else 'No token'}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        app_logger.info(
            f"GET_CURRENT_USER: Attempting jwt.decode with SECRET_KEY (first 5): {SECRET_KEY[:5] if SECRET_KEY else 'None'}... and ALGORITHM: {ALGORITHM}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        app_logger.info(
            f"GET_CURRENT_USER: jwt.decode successful. Payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            app_logger.error(
                "GET_CURRENT_USER: Username (sub) is None in token payload.")
            raise credentials_exception
        app_logger.info(f"GET_CURRENT_USER: Username from token: {username}")
        token_data = schemas.TokenData(username=username)
    except JWTError as e:
        error_logger.error(
            f"GET_CURRENT_USER: JWTError during token decoding: {e}", exc_info=True)
        raise credentials_exception
    except Exception as e:  # Catch any other unexpected errors during decoding
        error_logger.error(
            f"GET_CURRENT_USER: Unexpected error during token decoding phase: {e}", exc_info=True)
        raise credentials_exception

    app_logger.info(
        f"GET_CURRENT_USER: Attempting to fetch user \'{token_data.username}\' from DB.")
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        app_logger.error(
            f"GET_CURRENT_USER: User \'{token_data.username}\' not found in DB.")
        raise credentials_exception

    app_logger.info(
        f"GET_CURRENT_USER: User \'{user.username}\' found and authenticated.")
    return user

# Dependency to get current user, checking if active


async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Dependency for admin users


async def get_current_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return current_user


def authenticate_user(db: Session, username: str, password: str):
    error_logger.error(f"AUTH: Attempting to authenticate user: {username}")

    user = None
    try:
        error_logger.error(
            f"AUTH: Calling crud.get_user_by_username for '{username}'")
        user = crud.get_user_by_username(db, username=username)
        error_logger.error(
            f"AUTH: crud.get_user_by_username returned (user is None? {user is None})")
    except Exception as e:
        error_logger.error(
            f"AUTH: Exception during crud.get_user_by_username for '{username}': {e}", exc_info=True)
        return False

    if not user:
        error_logger.error(
            f"AUTH: Authentication failed: User '{username}' not found (after try-except).")
        return False

    error_logger.error(
        f"AUTH: User '{username}' found. Hashed from DB (first 10): '{user.hashed_password[:10] if user.hashed_password else 'None'}'. Verifying password.")

    # Pre-verification checks for password and user.hashed_password
    if password is None:
        error_logger.error(
            f"AUTH: Password input is None for user '{username}'. Cannot verify.")
        return False
    if not isinstance(password, str):
        error_logger.error(
            f"AUTH: Password input is not a string (type: {type(password)}) for user '{username}'. Cannot verify.")
        return False
    if user.hashed_password is None:  # Should be caught by DB schema ideally, but good to check
        error_logger.error(
            f"AUTH: Hashed password in DB is None for user '{username}'. Cannot verify.")
        return False
    if not isinstance(user.hashed_password, str):
        error_logger.error(
            f"AUTH: Hashed password in DB is not a string (type: {type(user.hashed_password)}) for user '{username}'. Cannot verify.")
        return False
    if not password:  # Check for empty string password
        error_logger.error(
            f"AUTH: Plain password input is empty for user '{username}'. Cannot verify.")
        return False
    if not user.hashed_password:  # Check for empty string hashed_password
        error_logger.error(
            f"AUTH: Hashed password in DB is empty for user '{username}'. Cannot verify.")
        return False

    error_logger.error(
        f"AUTH: Pre-verify checks passed for '{username}'. Plain len: {len(password)}, Hashed len: {len(user.hashed_password)}")

    try:
        plain_preview = password[:3]
        hashed_preview = user.hashed_password[:10]
        error_logger.error(
            f"AUTH: Calling verify_password for '{username}' with plain_preview: '{plain_preview}...' and hashed_preview: '{hashed_preview}...'")

        password_verified = verify_password(password, user.hashed_password)
        error_logger.error(
            f"AUTH: verify_password returned: {password_verified} for user '{username}'")

    except Exception as e:  # This would catch issues if verify_password re-raised an exception
        error_logger.error(
            f"AUTH: Exception during password verification call for user '{username}': {e}", exc_info=True)
        return False

    if not password_verified:
        error_logger.error(
            f"AUTH: Authentication failed: Incorrect password for user '{username}'. Verification result was {password_verified}")
        return False

    app_logger.info(
        f"AUTH: Password verified for user '{username}'. Authentication successful.")
    return user
