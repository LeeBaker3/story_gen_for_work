from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend import crud, schemas, database
from backend.auth import get_current_admin_user
from backend.logging_config import app_logger, error_logger
from backend.database import get_db

router = APIRouter(
    prefix="/admin/dynamic-lists",
    tags=["Admin - Dynamic Lists"],
    # Protect all routes in this router
    dependencies=[Depends(get_current_admin_user)]
)

# DynamicList Endpoints


@router.post("/", response_model=schemas.DynamicList, status_code=status.HTTP_201_CREATED)
def create_dynamic_list_endpoint(
    dynamic_list: schemas.DynamicListCreate,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=dynamic_list.list_name)
    if db_list:
        raise HTTPException(
            status_code=400, detail=f"Dynamic list '{dynamic_list.list_name}' already exists")
    return crud.create_dynamic_list(db=db, dynamic_list=dynamic_list)


@router.get("/", response_model=List[schemas.DynamicList])
def read_dynamic_lists_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    lists = crud.get_dynamic_lists(db, skip=skip, limit=limit)
    return lists


@router.get("/{list_name}", response_model=schemas.DynamicList)
def read_dynamic_list_endpoint(
    list_name: str,
    db: Session = Depends(get_db)
):
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if db_list is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found")
    return db_list


@router.delete("/{list_name}", status_code=status.HTTP_204_NO_CONTENT)
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
        if crud.is_dynamic_list_item_in_use(db, item_id=item.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete list '{list_name}'. Item '{item.item_label}' (ID: {item.id}) is currently in use."
            )

    if not crud.delete_dynamic_list(db, list_name=list_name):
        raise HTTPException(
            status_code=404, detail=f"Dynamic list '{list_name}' not found")
    return

# DynamicListItem Endpoints


@router.post("/{list_name}/items", response_model=schemas.DynamicListItem, status_code=status.HTTP_201_CREATED)
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


@router.get("/{list_name}/items", response_model=List[schemas.DynamicListItem])
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
@router.get("/items/{item_id}", response_model=schemas.DynamicListItem)
def read_single_dynamic_list_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")
    return db_item


@router.put("/items/{item_id}", response_model=schemas.DynamicListItem)
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


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dynamic_list_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")

    if crud.is_dynamic_list_item_in_use(db, item_id=item_id):
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


@router.get("/items/{item_id}/in-use", response_model=dict)
def check_dynamic_list_item_in_use(
    item_id: int,
    db: Session = Depends(get_db)
):
    """
    Returns whether a dynamic list item is currently in use (referenced in any stories).
    Response: {"in_use": true/false}
    """
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found"
        )
    in_use = crud.is_dynamic_list_item_in_use(db, item_id)
    return {"in_use": in_use}
