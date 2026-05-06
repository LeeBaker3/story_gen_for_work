import os
import secrets
from hashlib import sha256
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
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class TokenData(BaseModel):
    username: Optional[str] = None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def hash_password_reset_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def password_reset_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(
        minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )


def should_expose_password_reset_token_preview() -> bool:
    return os.getenv("TESTING") == "true" or os.getenv("RUN_ENV", "dev") != "prod"


def issue_password_reset_token(db: Session, user: schemas.User) -> tuple[str, datetime]:
    token = create_password_reset_token()
    expires_at = password_reset_expiry()
    crud.set_user_password_reset_token(
        db,
        user,
        token_hash=hash_password_reset_token(token),
        expires_at=expires_at,
    )
    return token, expires_at


def issue_password_reset_token_preview() -> str:
    return create_password_reset_token()


def get_valid_password_reset_user(db: Session, token: str):
    user = crud.get_user_by_password_reset_token_hash(
        db,
        hash_password_reset_token(token),
    )
    if not user:
        return None

    expires_at = user.password_reset_token_expires_at
    if expires_at is None:
        return None

    if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at < datetime.now(UTC):
        crud.clear_user_password_reset_token(db, user)
        return None

    return user


def reset_user_password(db: Session, user: schemas.User, new_password: str):
    return crud.update_user_password(db, user, get_password_hash(new_password))


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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError as e:
        error_logger.error(f"JWT Error: {e}")
        raise credentials_exception

    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: schemas.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Dependency for admin users


async def get_current_admin_user(current_user: schemas.User = Depends(get_current_active_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def authenticate_user(db: Session, username: str, password: str):
    user = crud.get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
