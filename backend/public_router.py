from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Body
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import io
from datetime import timedelta

from backend import crud, schemas, auth, database, pdf_generator
from backend.database import get_db
from backend.logging_config import app_logger, error_logger
from backend.story_generation_service import generate_story_as_background_task

public_router = APIRouter()


@public_router.post("/users/", response_model=schemas.User, tags=["authentication"])
async def register_user(
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Public endpoint to register a new user (sign up)."""
    # Enforce unique username (and optionally email if provided)
    if crud.get_user_by_username(db, username=user.username):
        raise HTTPException(
            status_code=400, detail="Username already registered")
    if user.email and crud.get_user_by_email(db, email=user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    created = crud.create_user(db=db, user=user)
    return created


@public_router.post("/token", response_model=schemas.Token, tags=["authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@public_router.post("/stories/", response_model=schemas.StoryGenerationTask, status_code=status.HTTP_202_ACCEPTED)
async def create_new_story(
    story_input: schemas.StoryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    draft_id = story_input.draft_id
    app_logger.info(
        f"User {current_user.username} initiating new story creation. Input: {story_input.model_dump(exclude_none=True)}. Draft ID: {draft_id}")

    if story_input.title and crud.get_story_by_title_and_owner(db, title=story_input.title, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A story with this title already exists."
        )

    initial_title = story_input.title or "[AI Title Pending...]"
    db_story = crud.create_story_db_entry(
        db, story_input, current_user.id, title=initial_title, is_draft=False)
    if not db_story:
        raise HTTPException(
            status_code=500, detail="Could not create story shell.")

    task = crud.create_story_generation_task(db, db_story.id, current_user.id)
    if not task:
        raise HTTPException(
            status_code=500, detail="Could not create generation task.")

    background_tasks.add_task(generate_story_as_background_task,
                              task.id, db_story.id, current_user.id, story_input)

    return task


@public_router.get("/stories/generation-status/{task_id}", response_model=schemas.StoryGenerationTask)
async def get_generation_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    task = crud.get_story_generation_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this task")
    return task


@public_router.get("/stories/", response_model=List[schemas.Story])
async def read_user_stories(
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    include_drafts: bool = True
):
    """
    Fetches a list of stories for the currently authenticated user.
    - **skip**: Number of stories to skip for pagination.
    - **limit**: Maximum number of stories to return.
    - **include_drafts**: Whether to include stories marked as drafts.
    """
    app_logger.info(
        f"User {current_user.username} requested their stories. Skip: {skip}, Limit: {limit}, Include Drafts: {include_drafts}")
    stories = crud.get_stories_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit, include_drafts=include_drafts)
    if not stories:
        app_logger.info(f"No stories found for user {current_user.username}.")
    return stories


@public_router.get("/stories/{story_id}", response_model=schemas.Story)
async def read_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    """
    Fetches a single story by its ID.
    Ensures the story belongs to the current user.
    """
    app_logger.info(
        f"User {current_user.username} requested story with ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id, user_id=current_user.id)
    if db_story is None:
        error_logger.warning(
            f"Story with ID {story_id} not found for user {current_user.username}.")
        raise HTTPException(status_code=404, detail="Story not found")
    # This check is redundant if get_story already enforces ownership, but it's good for defense-in-depth
    if db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to access unauthorized story {story_id}.")
        raise HTTPException(
            status_code=403, detail="Not authorized to access this story")
    app_logger.info(
        f"Story {story_id} ({db_story.title}) retrieved for user {current_user.username}.")
    return db_story


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


@public_router.get("/stories/{story_id}/pdf", status_code=status.HTTP_200_OK)
async def export_story_as_pdf_api(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    """API-prefixed PDF export for frontend: /api/v1/stories/{story_id}/pdf

    Mirrors the root-level endpoint in main.py, but lives under the public router.
    """
    app_logger.info(
        f"User {current_user.username} requested PDF for story ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id, user_id=current_user.id)
    if not db_story or db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to access unauthorized or non-existent story PDF: {story_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Story not found or access denied.")

    try:
        pdf_content_bytes = await asyncio.to_thread(pdf_generator.create_story_pdf, db_story)
        app_logger.info(
            f"PDF generated for story {story_id} for user {current_user.username}")

        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in (
            ' ', '-', '_') else '' for c in db_story.title).rstrip()
        if not safe_title:
            safe_title = f"story_{db_story.id}"

        return StreamingResponse(io.BytesIO(pdf_content_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": f"attachment; filename={safe_title}.pdf"})
    except Exception as e:
        error_logger.error(
            f"Failed to generate PDF for story {story_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {e}")
