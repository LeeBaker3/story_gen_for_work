from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend import crud, schemas, auth
from backend.database import get_db
from backend.logging_config import app_logger

public_router = APIRouter()


@public_router.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(auth.get_current_active_user)):
    """
    Fetch the current logged-in user.
    """
    app_logger.info(f"User {current_user.username} is fetching their details.")
    return current_user


@public_router.get("/dynamic-lists/{list_name}/active-items", response_model=List[schemas.DynamicListItemPublic])
def get_public_list_items(list_name: str, db: Session = Depends(get_db)):
    items = crud.get_active_dynamic_list_items(db, list_name=list_name)
    if not items:
        # This is not ideal, as it could mean the list is empty or doesn't exist.
        # For a public endpoint, we might not want to reveal which it is.
        # However, for the purpose of this exercise, we'll make it explicit.
        db_list = crud.get_dynamic_list(db, list_name=list_name)
        if not db_list:
            raise HTTPException(
                status_code=404, detail=f"Dynamic list '{list_name}' not found.")
        # If the list exists but is empty, return an empty list.
        return []
    return items
