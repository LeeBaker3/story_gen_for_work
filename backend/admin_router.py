from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend import crud, schemas, database
from backend.auth import get_current_admin_user
from backend.logging_config import app_logger, error_logger
from backend.database import get_db

admin_router = APIRouter(
    dependencies=[Depends(get_current_admin_user)]
)

# DynamicList Endpoints


@admin_router.post("/dynamic-lists/", response_model=schemas.DynamicList, status_code=status.HTTP_201_CREATED)
def create_dynamic_list_endpoint(
    dynamic_list: schemas.DynamicListCreate,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=dynamic_list.list_name)
    if db_list:
        raise HTTPException(
            status_code=400, detail=f"Dynamic list '{dynamic_list.list_name}' already exists")
    return crud.create_dynamic_list(db=db, dynamic_list=dynamic_list)


@admin_router.get("/dynamic-lists/", response_model=List[schemas.DynamicList])
def read_dynamic_lists_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    lists = crud.get_dynamic_lists(db, skip=skip, limit=limit)
    return lists


@admin_router.get("/dynamic-lists/{list_name}", response_model=schemas.DynamicList)
def read_dynamic_list_endpoint(
    list_name: str,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if db_list is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found")
    return db_list


@admin_router.put("/dynamic-lists/{list_name}", response_model=schemas.DynamicList)
def update_dynamic_list_endpoint(
    list_name: str,
    dynamic_list_update: schemas.DynamicListUpdate,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if db_list is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found, cannot update.")

    updated_list = crud.update_dynamic_list(
        db, list_name=list_name, dynamic_list_update=dynamic_list_update)
    if updated_list is None:  # Should ideally not happen if previous check passed
        raise HTTPException(
            status_code=500, detail=f"Failed to update dynamic list '{list_name}'.")
    return updated_list


@admin_router.delete("/dynamic-lists/{list_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dynamic_list_endpoint(
    list_name: str,
    db: Session = Depends(get_db)
):
    # Check if any items from this list are in use before deleting the list
    # This is a more complex check, as it involves iterating through all items.
    # For simplicity, we'll rely on the frontend to manage this, or add more detailed checks if required.
    # The cascade delete will remove items, but won't prevent deletion if items are "in use" conceptually.
    # A more robust check would iterate all items in the list and call is_dynamic_list_item_in_use for each.

    # For now, let's check if the list has items that are in use.
    items = crud.get_dynamic_list_items(
        db, list_name=list_name, limit=1000)  # Get all items
    for item in items:
        usage_info = crud.is_dynamic_list_item_in_use(db, item_id=item.id)
        if usage_info["is_in_use"]:  # Explicitly check the 'is_in_use' key
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete list '{list_name}'. Item '{item.item_label}' (ID: {item.id}) is currently in use."
            )

    if not crud.delete_dynamic_list(db, list_name=list_name):
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found")
    return

# DynamicListItem Endpoints


@admin_router.post("/dynamic-lists/{list_name}/items", response_model=schemas.DynamicListItem, status_code=status.HTTP_201_CREATED)
def create_dynamic_list_item_endpoint(
    list_name: str,  # Ensure the item is created for the correct list in the path
    item: schemas.DynamicListItemCreate,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found, cannot add item.")

    # Ensure item.list_name matches the path if provided, or set it
    if item.list_name != list_name:
        # Or raise HTTPException if they must match and item.list_name is also provided in body
        item.list_name = list_name

    # Check for uniqueness of item_value within the list
    existing_items = crud.get_dynamic_list_items(db, list_name=list_name)
    for existing_item in existing_items:
        if existing_item.item_value == item.item_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item with value '{item.item_value}' already exists in list '{list_name}'."
            )

    return crud.create_dynamic_list_item(db=db, item=item)


@admin_router.get("/dynamic-lists/{list_name}/items", response_model=List[schemas.DynamicListItem])
def read_dynamic_list_items_endpoint(
    list_name: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # Admin can choose to see all or only active
    only_active: Optional[bool] = None
):
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found.")

    if only_active is not None:
        items = crud.get_dynamic_list_items(
            db, list_name=list_name, skip=skip, limit=limit, only_active=only_active)
    else:
        items = crud.get_dynamic_list_items(
            db, list_name=list_name, skip=skip, limit=limit)
    return items


# Changed path for clarity
@admin_router.get("/items/{item_id}", response_model=schemas.DynamicListItem)
def read_single_dynamic_list_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")
    return db_item


@admin_router.put("/items/{item_id}", response_model=schemas.DynamicListItem)
def update_dynamic_list_item_endpoint(
    item_id: int,
    item_update: schemas.DynamicListItemUpdate,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")

    # If item_value is being changed, check for uniqueness within its list
    if item_update.item_value is not None and item_update.item_value != db_item.item_value:
        existing_items = crud.get_dynamic_list_items(
            db, list_name=db_item.list_name)
        for existing_item in existing_items:
            if existing_item.item_value == item_update.item_value and existing_item.id != item_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Another item with value '{item_update.item_value}' already exists in list '{db_item.list_name}'."
                )

    updated_item = crud.update_dynamic_list_item(
        db, item_id=item_id, item_update=item_update)
    if updated_item is None:  # Should not happen if previous check passed, but good practice
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found during update")
    return updated_item


@admin_router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dynamic_list_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")

    usage_info = crud.is_dynamic_list_item_in_use(db, item_id=item_id)
    if usage_info["is_in_use"]:  # Explicitly check the 'is_in_use' key
        # Instead of deleting, an admin might prefer to deactivate.
        # For now, we prevent deletion and let admin deactivate via PUT if needed.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Item '{db_item.item_label}' (ID: {item_id}) is currently in use and cannot be deleted. Consider deactivating it instead."
        )

    if not crud.delete_dynamic_list_item(db, item_id=item_id):
        # This case should ideally be caught by the db_item check above
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found for deletion")
    return


@admin_router.get("/items/{item_id}/in-use", response_model=schemas.DynamicListItemUsage)
def check_dynamic_list_item_in_use(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns whether a dynamic list item is currently in use and details of its usage.
    Response model: schemas.DynamicListItemUsage
    """
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found"
        )

    usage_info = crud.is_dynamic_list_item_in_use(db, item_id)

    # Ensure usage_info is always a dictionary matching DynamicListItemUsage schema
    if isinstance(usage_info, bool):  # Case where crud returns simple boolean (item not in use)
        return schemas.DynamicListItemUsage(is_in_use=usage_info, details=[])
    elif isinstance(usage_info, dict) and "is_in_use" in usage_info:
        # Ensure details is a list, even if crud might sometimes not include it when not in use
        details = usage_info.get("details", [])
        if not isinstance(details, list):
            # Log a warning if details is not a list as expected by schema
            app_logger.warning(
                f"Usage details for item {item_id} was not a list: {details}. Defaulting to empty list.")
            details = []
        return schemas.DynamicListItemUsage(is_in_use=usage_info["is_in_use"], details=details)

    # Fallback or error if the return type is unexpected
    error_logger.error(
        f"Unexpected return type from crud.is_dynamic_list_item_in_use for item {item_id}: {type(usage_info)}, value: {usage_info}")
    # Return a default "not in use" state with an error logged, or raise 500
    # Raising 500 might be better to signal an unexpected state from CRUD.
    raise HTTPException(
        status_code=500, detail="Error checking item usage status due to unexpected data format from CRUD.")


# --- Admin User Management Router ---
@admin_router.put("/management/users/{user_id}", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
def admin_update_user_endpoint(user_id: int, user_update: schemas.AdminUserUpdate, db: Session = Depends(get_db), current_admin: schemas.User = Depends(get_current_admin_user)):
    """
    Update a user's details (username, email, role, active status).
    Prevents an admin from changing their own role if they are the sole admin or deactivating themselves.
    """
    app_logger.info(
        f"Admin {current_admin.username} attempting to update details for user ID {user_id} with data: {user_update.model_dump(exclude_unset=True)}")

    target_user = crud.get_user_admin(db, user_id=user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with ID {user_id} not found")

    # Prevent self-deactivation by admin
    if user_id == current_admin.id and user_update.is_active is False:
        error_logger.warning(
            f"Admin {current_admin.username} (ID: {current_admin.id}) attempted to deactivate themselves.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot deactivate their own account."
        )

    # Prevent an admin from changing their own role
    if user_id == current_admin.id and user_update.role is not None and user_update.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot change their own role."
        )

    # Validate role if it's being updated
    if user_update.role is not None and user_update.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user' or 'admin'."
        )

    # Check for username uniqueness if username is being changed
    if user_update.username is not None and user_update.username != target_user.username:
        existing_user_with_username = crud.get_user_by_username(
            db, username=user_update.username)
        if existing_user_with_username and existing_user_with_username.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_update.username}' is already taken."
            )

    updated_user = crud.admin_update_user(
        db, user_id=user_id, user_update=user_update)

    if not updated_user:
        error_logger.error(
            f"Failed to update details for user ID {user_id} by admin {current_admin.username}. crud.admin_update_user returned None.")
        # This could be due to the user not being found by admin_update_user, though checked above.
        # Or a DB issue during commit.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Could not update details for user ID {user_id}.")

    app_logger.info(
        f"User ID {user_id} details updated by admin {current_admin.username}. New details: {updated_user}")
    return updated_user


@admin_router.get("/management/users/", response_model=List[schemas.User], dependencies=[Depends(get_current_admin_user)])
def admin_get_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all users.
    """
    users = crud.get_users_admin(db, skip=skip, limit=limit)
    return users


@admin_router.get("/management/users/{user_id}", response_model=schemas.User, dependencies=[Depends(get_current_admin_user)])
def admin_get_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific user by ID.
    """
    user = crud.get_user_admin(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with ID {user_id} not found")
    return user

# You will need to include admin_user_router in your main FastAPI app (e.g., in main.py)
# Example for main.py:
# from backend.admin_router import router as admin_dynamic_lists_router, admin_user_router
# app.include_router(admin_dynamic_lists_router)
# app.include_router(admin_user_router)
