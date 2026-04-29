from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status, Body
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import asyncio
import io
import os
import shutil
from datetime import timedelta

from backend import crud, schemas, auth, database, pdf_generator, ai_services
from backend.database import get_db
from backend.logging_config import app_logger, error_logger
from backend.rate_limiting import limiter
from backend.settings import get_settings
from backend import story_generation_service
from backend import storage_paths
from backend.storage_paths import page_image_paths

public_router = APIRouter()
settings = get_settings()

VALID_TEXT_POSITIONS = {"top", "bottom", "left", "right", "center"}


def _character_detail_from_saved_character(
    character: database.Character,
) -> schemas.CharacterDetail:
    """Convert a saved Character row into a story CharacterDetail payload."""

    return schemas.CharacterDetail(
        name=character.name,
        description=character.description,
        age=character.age,
        gender=character.gender,
        clothing_style=character.clothing_style,
        key_traits=character.key_traits,
        reference_image_path=character.current_image.file_path
        if getattr(character, "current_image", None)
        else None,
    )


def _merge_selected_characters_into_story_input(
    story_input: schemas.StoryCreate,
    db: Session,
    user_id: int,
) -> schemas.StoryCreate:
    """Enrich selected story characters with saved library details and images."""

    if not story_input.character_ids:
        return story_input

    saved_characters = db.query(database.Character).filter(
        database.Character.user_id == user_id,
        database.Character.id.in_(story_input.character_ids),
    ).all()

    saved_by_name = {
        (character.name or "").strip().casefold(): character
        for character in saved_characters
        if (character.name or "").strip()
    }

    merged_characters: List[schemas.CharacterDetail] = []
    for character in story_input.main_characters or []:
        key = (character.name or "").strip().casefold()
        saved_character = saved_by_name.pop(key, None) if key else None
        if saved_character is None:
            merged_characters.append(character)
            continue

        saved_detail = _character_detail_from_saved_character(saved_character)
        merged_characters.append(
            character.model_copy(
                update={
                    "description": character.description or saved_detail.description,
                    "age": character.age if character.age is not None else saved_detail.age,
                    "gender": character.gender or saved_detail.gender,
                    "clothing_style": character.clothing_style
                    or saved_detail.clothing_style,
                    "key_traits": character.key_traits or saved_detail.key_traits,
                    "reference_image_path": character.reference_image_path
                    or saved_detail.reference_image_path,
                }
            )
        )

    for saved_character in saved_by_name.values():
        merged_characters.append(
            _character_detail_from_saved_character(saved_character)
        )

    return story_input.model_copy(update={"main_characters": merged_characters})


def _get_story_or_404(
    db: Session,
    story_id: int,
    user_id: int,
) -> database.Story:
    """Return a user-owned story or raise a 404."""

    db_story = crud.get_story(db, story_id=story_id, user_id=user_id)
    if db_story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return db_story


def _get_story_page_or_404(
    db_story: database.Story,
    page_id: int,
) -> database.Page:
    """Return a page from a story or raise a 404."""

    for page in db_story.pages or []:
        if page.id == page_id:
            return page
    raise HTTPException(status_code=404, detail="Page not found")


def _extract_reference_image_paths(db_story: database.Story) -> List[str]:
    """Return all known saved reference image paths for a story."""

    paths: List[str] = []
    for character in db_story.main_characters or []:
        if not isinstance(character, dict):
            continue
        path = character.get("reference_image_path") or character.get(
            "Reference_image_path"
        )
        if path:
            paths.append(path)
    return paths
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
@limiter.limit(settings.login_rate_limit)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return an access token."""

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
    story_input = _merge_selected_characters_into_story_input(
        story_input,
        db,
        current_user.id,
    )
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

    background_tasks.add_task(
        story_generation_service.generate_story_as_background_task,
        task.id,
        db_story.id,
        current_user.id,
        story_input,
    )

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


@public_router.get("/stories/{story_id}/pages/{page_id}/image")
async def read_story_page_image_api(
    story_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Return one generated story page image for the story owner only."""

    db_story = db.query(database.Story).filter(
        database.Story.id == story_id
    ).first()
    if db_story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    if db_story.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this story",
        )

    db_page = _get_story_page_or_404(db_story, page_id)

    if not db_page.image_path:
        raise HTTPException(status_code=404, detail="Page image not found")

    try:
        is_private_story_image = storage_paths.is_private_story_asset_path(
            db_page.image_path
        )
        image_path = storage_paths.resolve_data_path(db_page.image_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Page image not found") from exc

    if not is_private_story_image or not os.path.isfile(image_path):
        raise HTTPException(status_code=404, detail="Page image not found")

    return FileResponse(image_path)


@public_router.put("/stories/{story_id}/title", response_model=schemas.Story)
async def update_story_title_api(
    story_id: int,
    title_update: schemas.StoryTitleUpdate,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Update a story title via the API-prefixed public router."""

    db_story = _get_story_or_404(
        db, story_id=story_id, user_id=current_user.id)
    updated_story = crud.update_story_title(
        db=db,
        story_id=db_story.id,
        new_title=title_update.title,
    )
    if updated_story is None:
        raise HTTPException(
            status_code=500, detail="Could not update story title")
    return updated_story


@public_router.put("/stories/{story_id}/editor", response_model=schemas.Story)
async def save_story_editor_api(
    story_id: int,
    editor_update: schemas.StoryEditorUpdate,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Persist title, document defaults, and per-page editor overrides."""

    updated_story = crud.save_story_editor(
        db=db,
        story_id=story_id,
        user_id=current_user.id,
        editor_update=editor_update,
    )
    if updated_story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return updated_story


@public_router.post(
    "/stories/{story_id}/pages/{page_id}/restore-text",
    response_model=schemas.Page,
)
async def restore_story_page_text_api(
    story_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Restore one page's text to the original generated content."""

    restored_page = crud.restore_page_text(
        db=db,
        story_id=story_id,
        page_id=page_id,
        user_id=current_user.id,
    )
    if restored_page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return restored_page


@public_router.post(
    "/stories/{story_id}/pages/{page_id}/restore-image",
    response_model=schemas.Page,
)
async def restore_story_page_image_api(
    story_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Restore one page's image to the original generated asset."""

    restored_page = crud.restore_page_image(
        db=db,
        story_id=story_id,
        page_id=page_id,
        user_id=current_user.id,
    )
    if restored_page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return restored_page


@public_router.post(
    "/stories/{story_id}/pages/{page_id}/regenerate-image",
    response_model=schemas.Page,
)
async def regenerate_story_page_image_api(
    story_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Regenerate a single page image using the current editor text position."""

    db_story = _get_story_or_404(
        db, story_id=story_id, user_id=current_user.id)
    db_page = _get_story_page_or_404(db_story, page_id)
    effective_settings = crud.get_effective_page_editor_settings(
        db_story, db_page)
    text_position = str(effective_settings.get("text_position") or "bottom")
    guidance = story_generation_service._text_position_guidance(text_position)
    style_reference = db_story.image_style or schemas.ImageStyle.DEFAULT.value
    base_prompt = db_page.image_description or db_page.text or db_story.title
    prompt_content = f"{base_prompt}. {guidance}"
    reference_paths = _extract_reference_image_paths(db_story)
    image_save_path_on_disk, image_path_for_db = page_image_paths(
        current_user.id,
        story_id,
        db_page.page_number,
    )

    new_image_path = await ai_services.generate_image_for_page(
        page_content=prompt_content,
        style_reference=style_reference,
        db=db,
        user_id=current_user.id,
        story_id=story_id,
        page_number=db_page.page_number,
        image_save_path_on_disk=image_save_path_on_disk,
        image_path_for_db=image_path_for_db,
        reference_image_paths=reference_paths or None,
    )
    if new_image_path is None:
        raise HTTPException(
            status_code=502,
            detail="Image generation did not return a new page image.",
        )

    state = crud.get_page_editor_state(db_page)
    db_page.image_path = new_image_path
    db_page.editor_state = state
    db.commit()
    db.refresh(db_page)
    return db_page


@public_router.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    """Delete a story owned by the current authenticated user."""
    app_logger.info(
        f"User {current_user.username} attempting to delete story ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id, user_id=current_user.id)

    if not db_story:
        error_logger.warning(
            f"Story with ID {story_id} not found for deletion attempt by user {current_user.username}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    if db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to delete unauthorized story {story_id}.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this story",
        )

    deleted_successfully = crud.delete_story_db_entry(db=db, story_id=story_id)
    if not deleted_successfully:
        error_logger.error(
            f"Failed to delete story {story_id} from database for user {current_user.username}, though initial checks passed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete story from database.",
        )

    story_image_dir = storage_paths.story_images_abs(current_user.id, story_id)
    try:
        if os.path.isdir(story_image_dir):
            shutil.rmtree(story_image_dir)
    except OSError as exc:
        app_logger.warning(
            "Could not delete story images for story %s: %s",
            story_id,
            exc,
        )

    app_logger.info(
        f"Story ID {story_id} successfully deleted by user {current_user.username}.")
    return


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
