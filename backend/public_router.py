from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Body
from sqlalchemy.orm import Session
from typing import List, Optional

from backend import crud, schemas, auth
from backend.database import get_db
from backend.logging_config import app_logger
from backend.story_generation_service import generate_story_as_background_task

public_router = APIRouter()


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
