from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from backend import crud, schemas, database
from backend.auth import get_current_admin_user
from backend.image_style_mapping import get_admin_image_style_mapping_state
from backend.logging_config import app_logger, error_logger
from backend.database import get_db
from backend.settings import get_settings
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone

admin_router = APIRouter(
    dependencies=[Depends(get_current_admin_user)]
)


@admin_router.get("/stats", response_model=schemas.AdminStats)
def get_admin_stats(db: Session = Depends(get_db)):
    """Aggregate high-level application stats for the admin dashboard.

    Now leverages precise task tracking fields (duration_ms, attempts) when available.
    Falls back gracefully if legacy rows lack new fields.
    """
    # Import models locally to avoid circular import issues
    from backend.database import User, Story, Character, StoryGenerationTask

    # Time window
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    # Users
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(
        User.is_active == True).scalar() or 0

    # Stories
    total_stories = db.query(func.count(Story.id)).scalar() or 0
    generated_stories = db.query(func.count(Story.id)).filter(
        Story.is_draft == False).scalar() or 0
    draft_stories = total_stories - generated_stories

    # Characters
    try:
        total_characters = db.query(func.count(Character.id)).scalar() or 0
    except Exception:
        total_characters = 0

    # Tasks last 24h
    tasks_24h_q = db.query(StoryGenerationTask).filter(
        StoryGenerationTask.created_at >= since_24h)
    tasks_last_24h = tasks_24h_q.count()
    tasks_completed_last_24h = tasks_24h_q.filter(
        StoryGenerationTask.status
        == schemas.GenerationTaskStatus.COMPLETED.value).count()
    tasks_failed_last_24h = tasks_24h_q.filter(
        StoryGenerationTask.status
        == schemas.GenerationTaskStatus.FAILED.value).count()
    tasks_in_progress = db.query(StoryGenerationTask).filter(
        StoryGenerationTask.status.in_([
            schemas.GenerationTaskStatus.PENDING.value,
            schemas.GenerationTaskStatus.IN_PROGRESS.value,
        ])).count()

    # Precise avg duration (prefer duration_ms; fallback to updated_at-created_at)
    durations = []
    total_attempts = 0
    completed_tasks = []
    if tasks_completed_last_24h:
        completed_tasks = tasks_24h_q.filter(
            StoryGenerationTask.status
            == schemas.GenerationTaskStatus.COMPLETED.value).all()
        for t in completed_tasks:
            try:
                # Prefer explicit duration_ms
                if getattr(t, 'duration_ms', None):
                    durations.append(t.duration_ms / 1000.0)
                elif t.created_at and t.updated_at:
                    durations.append(
                        (t.updated_at - t.created_at).total_seconds())
                # Sum attempts if present
                total_attempts += getattr(t, 'attempts', 0) or 0
            except Exception:
                pass
    avg_duration = round(sum(durations) / len(durations),
                         2) if durations else None
    avg_attempts = round(total_attempts / len(completed_tasks),
                         2) if completed_tasks else None

    success_rate = None
    denom = tasks_completed_last_24h + tasks_failed_last_24h
    if denom > 0:
        success_rate = tasks_completed_last_24h / denom

    return schemas.AdminStats(
        total_users=total_users,
        active_users=active_users,
        total_stories=total_stories,
        generated_stories=generated_stories,
        draft_stories=draft_stories,
        total_characters=total_characters,
        tasks_last_24h=tasks_last_24h,
        tasks_in_progress=tasks_in_progress,
        tasks_failed_last_24h=tasks_failed_last_24h,
        tasks_completed_last_24h=tasks_completed_last_24h,
        avg_task_duration_seconds_last_24h=avg_duration,
        success_rate_last_24h=success_rate,
        # New metric: average attempts over completed tasks in the last 24h
        avg_attempts_last_24h=avg_attempts,
    )


@admin_router.get(
    "/broadcasts",
    response_model=List[schemas.AdminBroadcast],
)
def list_admin_broadcasts(db: Session = Depends(get_db)):
    """Return recent broadcast records for the admin dashboard."""

    from backend.database import AdminBroadcast

    return db.query(AdminBroadcast).order_by(AdminBroadcast.sent_at.desc()).all()


@admin_router.post(
    "/broadcasts",
    response_model=schemas.AdminBroadcast,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_broadcast(
    broadcast: schemas.AdminBroadcastCreate,
    db: Session = Depends(get_db),
    current_admin_user=Depends(get_current_admin_user),
):
    """Persist a minimal broadcast record and mark it sent to active users."""

    from backend.database import AdminBroadcast, User

    recipient_count = db.query(func.count(User.id)).filter(
        User.is_active == True,
        User.is_deleted == False,
    ).scalar() or 0

    db_broadcast = AdminBroadcast(
        title=broadcast.title,
        message=broadcast.message,
        target_scope="all_active_users",
        status="sent",
        recipient_count=recipient_count,
        created_by_user_id=current_admin_user.id,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(db_broadcast)
    db.commit()
    db.refresh(db_broadcast)
    return db_broadcast


@admin_router.get(
    "/analytics",
    response_model=schemas.AdminAnalyticsSummary,
)
def get_admin_analytics(db: Session = Depends(get_db)):
    """Return product-facing usage summaries for the admin dashboard."""

    from backend.database import AdminBroadcast, Character, Story
    from backend.database import StoryGenerationTask, User

    now = datetime.now(timezone.utc)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    users_registered_last_7d = db.query(func.count(User.id)).filter(
        User.created_at >= since_7d,
    ).scalar() or 0
    stories_created_last_7d = db.query(func.count(Story.id)).filter(
        Story.created_at >= since_7d,
    ).scalar() or 0
    stories_generated_last_7d = db.query(func.count(Story.id)).filter(
        Story.generated_at >= since_7d,
        Story.is_draft == False,
    ).scalar() or 0
    characters_created_last_7d = db.query(func.count(Character.id)).filter(
        Character.created_at >= since_7d,
    ).scalar() or 0
    active_story_authors_last_7d = db.query(
        func.count(func.distinct(Story.owner_id))
    ).filter(Story.created_at >= since_7d).scalar() or 0

    completed_tasks_last_7d = db.query(func.count(StoryGenerationTask.id)).filter(
        StoryGenerationTask.created_at >= since_7d,
        StoryGenerationTask.status == schemas.GenerationTaskStatus.COMPLETED.value,
    ).scalar() or 0
    failed_tasks_last_7d = db.query(func.count(StoryGenerationTask.id)).filter(
        StoryGenerationTask.created_at >= since_7d,
        StoryGenerationTask.status == schemas.GenerationTaskStatus.FAILED.value,
    ).scalar() or 0

    generation_success_rate_last_7d = None
    if completed_tasks_last_7d + failed_tasks_last_7d > 0:
        generation_success_rate_last_7d = completed_tasks_last_7d / (
            completed_tasks_last_7d + failed_tasks_last_7d
        )

    broadcasts_sent_last_30d = db.query(func.count(AdminBroadcast.id)).filter(
        AdminBroadcast.sent_at >= since_30d,
    ).scalar() or 0
    broadcast_recipients_last_30d = db.query(
        func.coalesce(func.sum(AdminBroadcast.recipient_count), 0)
    ).filter(AdminBroadcast.sent_at >= since_30d).scalar() or 0

    return schemas.AdminAnalyticsSummary(
        users_registered_last_7d=users_registered_last_7d,
        stories_created_last_7d=stories_created_last_7d,
        stories_generated_last_7d=stories_generated_last_7d,
        characters_created_last_7d=characters_created_last_7d,
        active_story_authors_last_7d=active_story_authors_last_7d,
        generation_success_rate_last_7d=generation_success_rate_last_7d,
        broadcasts_sent_last_30d=broadcasts_sent_last_30d,
        broadcast_recipients_last_30d=broadcast_recipients_last_30d,
    )

# DynamicList Endpoints


@admin_router.get(
    "/image-style-mappings",
    response_model=schemas.AdminImageStyleMappingState,
)
def read_image_style_mapping_state_endpoint(
    db: Session = Depends(get_db),
):
    """Return the effective image style mapping state for admin tooling."""

    settings = get_settings()
    return get_admin_image_style_mapping_state(
        db=db,
        mapping_enabled=getattr(settings, "enable_image_style_mapping", False),
    )


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
@admin_router.get("/dynamic-lists/items/{item_id}", response_model=schemas.DynamicListItem)
def read_single_dynamic_list_item_endpoint(
    item_id: int,
    db: Session = Depends(get_db)
):
    db_item = crud.get_dynamic_list_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(
            status_code=404, detail=f"Dynamic list item with ID {item_id} not found")
    return db_item


@admin_router.put("/dynamic-lists/items/{item_id}", response_model=schemas.DynamicListItem)
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


@admin_router.delete("/dynamic-lists/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@admin_router.get("/dynamic-lists/items/{item_id}/in-use", response_model=schemas.DynamicListItemUsage)
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

    # Ensure the response conforms to the DynamicListItemUsage schema
    return schemas.DynamicListItemUsage(
        is_in_use=usage_info.get("is_in_use", False),
        details=usage_info.get("details", [])
    )


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
    crud.create_admin_audit_event(
        db,
        admin_user_id=current_admin.id,
        event_type="user_update",
        target_type="user",
        target_id=updated_user.id,
        metadata_json={
            "user_id": updated_user.id,
            "changed_fields": sorted(user_update.model_dump(exclude_unset=True).keys()),
        },
    )
    return updated_user


@admin_router.get("/management/users/", response_model=List[schemas.User], dependencies=[Depends(get_current_admin_user)])
def admin_get_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve all users, excluding soft-deleted accounts by default.
    """
    users = crud.admin_get_users(db, skip=skip, limit=limit)
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


@admin_router.delete("/management/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin_user)])
def admin_soft_delete_user_endpoint(user_id: int, db: Session = Depends(get_db), current_admin: schemas.User = Depends(get_current_admin_user)):
    """Soft delete a user (set is_deleted=True and deactivate). Prevent deleting self."""
    if user_id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Admins cannot delete their own account.")
    user = crud.get_user_admin(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with ID {user_id} not found")
    ok = crud.soft_delete_user_admin(db, user_id=user_id)
    if not ok:
        # Could be already deleted
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"User with ID {user_id} not found or already deleted")
    crud.create_admin_audit_event(
        db,
        admin_user_id=current_admin.id,
        event_type="user_soft_delete",
        target_type="user",
        target_id=user_id,
        metadata_json={
            "user_id": user_id,
            "changed_fields": ["is_active", "is_deleted"],
        },
    )
    return


@admin_router.get("/privacy-requests", response_model=List[schemas.PrivacyRequest])
def admin_list_privacy_requests(
    db: Session = Depends(get_db),
):
    """List privacy requests for manual admin review."""

    return crud.get_privacy_requests_admin(db)


@admin_router.patch(
    "/privacy-requests/{request_id}",
    response_model=schemas.PrivacyRequest,
)
def admin_update_privacy_request(
    request_id: int,
    payload: schemas.PrivacyRequestUpdate,
    db: Session = Depends(get_db),
    current_admin: schemas.User = Depends(get_current_admin_user),
):
    """Update a privacy request's manual workflow status."""

    privacy_request = crud.get_privacy_request(db, request_id=request_id)
    if privacy_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privacy request with ID {request_id} not found",
        )

    previous_status = privacy_request.status
    updated_request = crud.update_privacy_request_status(
        db,
        request_id=request_id,
        status_value=payload.status,
        admin_user_id=current_admin.id,
    )
    if updated_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privacy request with ID {request_id} not found",
        )

    if previous_status != updated_request.status:
        crud.create_admin_audit_event(
            db,
            admin_user_id=current_admin.id,
            event_type="privacy_request_status_change",
            target_type="privacy_request",
            target_id=updated_request.id,
            metadata_json={
                "privacy_request_id": updated_request.id,
                "user_id": updated_request.user_id,
                "request_type": updated_request.request_type,
                "old_status": previous_status,
                "new_status": updated_request.status,
            },
        )

    return updated_request


# --- Admin Content Moderation ---

@admin_router.get(
    "/moderation/stories",
    response_model=schemas.PaginatedStories,
)
def admin_list_stories(
    page: int = 1,
    page_size: int = 20,
    user_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    include_hidden: bool = False,
    include_deleted: bool = False,
    db: Session = Depends(get_db)
) -> dict:
    total, items = crud.list_stories_admin(
        db,
        page=page,
        page_size=page_size,
        user_id=user_id,
        status=status_filter,
        created_from=created_from,
        created_to=created_to,
        include_hidden=include_hidden,
        include_deleted=include_deleted,
    )
    # Normalize legacy enum values for response validation (e.g., short text_density labels)
    legacy_text_density_map = {
        "Concise": schemas.TextDensity.CONCISE.value,
        "Standard": schemas.TextDensity.STANDARD.value,
        "Detailed": schemas.TextDensity.DETAILED.value,
    }
    for s in items:
        try:
            if getattr(s, "text_density", None) in legacy_text_density_map:
                setattr(s, "text_density",
                        legacy_text_density_map[s.text_density])
        except Exception:
            # Non-fatal: leave value as-is
            pass
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


class HideStoryRequest(schemas.BaseModel):  # lightweight inline schema
    is_hidden: bool


@admin_router.patch("/moderation/stories/{story_id}/hide", response_model=schemas.Story)
def admin_hide_story(
    story_id: int,
    payload: HideStoryRequest,
    db: Session = Depends(get_db),
    current_admin: schemas.User = Depends(get_current_admin_user),
):
    story = crud.set_story_hidden_admin(
        db, story_id=story_id, is_hidden=payload.is_hidden)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Story with ID {story_id} not found")
    crud.create_admin_audit_event(
        db,
        admin_user_id=current_admin.id,
        event_type="story_visibility_change",
        target_type="story",
        target_id=story.id,
        metadata_json={
            "story_id": story.id,
            "changed_fields": ["is_hidden"],
        },
    )
    # Normalize legacy enum values before response
    try:
        legacy_text_density_map = {
            "Concise": schemas.TextDensity.CONCISE.value,
            "Standard": schemas.TextDensity.STANDARD.value,
            "Detailed": schemas.TextDensity.DETAILED.value,
        }
        if getattr(story, "text_density", None) in legacy_text_density_map:
            setattr(story, "text_density",
                    legacy_text_density_map[story.text_density])
    except Exception:
        pass
    return story


@admin_router.delete("/moderation/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_soft_delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_admin: schemas.User = Depends(get_current_admin_user),
):
    ok = crud.soft_delete_story_admin(db, story_id=story_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Story with ID {story_id} not found")
    crud.create_admin_audit_event(
        db,
        admin_user_id=current_admin.id,
        event_type="story_soft_delete",
        target_type="story",
        target_id=story_id,
        metadata_json={
            "story_id": story_id,
            "changed_fields": ["is_deleted"],
        },
    )
    return

# You will need to include admin_user_router in your main FastAPI app (e.g., in main.py)
# Example for main.py:
# from backend.admin_router import router as admin_dynamic_lists_router, admin_user_router
# app.include_router(admin_dynamic_lists_router)
# app.include_router(admin_user_router)
