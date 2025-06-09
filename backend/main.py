from fastapi import FastAPI, Depends, HTTPException, status, Body  # Added Body
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
# Added PlainTextResponse
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles  # Added for static files
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid  # For unique image filenames
import asyncio
import os
import io  # Added for BytesIO
# Added for List, Optional, and Dict type hints
from typing import List, Optional, Dict

# Added pdf_generator
from . import crud, schemas, auth, database, ai_services, pdf_generator
# Import routers from admin_router.py
from .admin_router import router as admin_dynamic_lists_router, admin_user_router
from .logging_config import app_logger, api_logger, error_logger

# Drop all tables (for development purposes to apply schema changes)
# IMPORTANT: This will delete all existing data. Remove or comment out for production.
# database.Base.metadata.drop_all(bind=database.engine) # Commented out to prevent locking issues

# Create database tables
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Include routers from admin_router.py
app.include_router(admin_dynamic_lists_router)
app.include_router(admin_user_router)

# Mount static files directory for frontend
# Conditionally mount based on an environment variable
RUN_ENV = os.environ.get("RUN_ENV")
if RUN_ENV != "test":
    # Attempt to mount the frontend directory. If it doesn't exist, log an error but continue.
    # This is to prevent crashes if the backend is run in an environment where 'frontend' isn't present.
    frontend_dir = "frontend"
    if not os.path.exists(frontend_dir) or not os.path.isdir(frontend_dir):
        app_logger.warning(
            f"Frontend directory '{frontend_dir}' not found. Static files for frontend will not be served.")
    else:
        app.mount("/static", StaticFiles(directory=frontend_dir),
                  name="static_frontend")
        app_logger.info(
            f"Mounted frontend static files from directory: {frontend_dir}")

    # Mount static files directory (for images)
    # This will serve files from the 'data' directory under the '/static_content' path
    # e.g., an image at data/images/user_1/story_1/foo.png will be accessible at /static_content/images/user_1/story_1/foo.png
    data_dir = "data"
    if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
        app_logger.warning(
            f"Data directory '{data_dir}' not found. Static content will not be served.")
    else:
        app.mount("/static_content", StaticFiles(directory=data_dir),
                  name="static_content")
        app_logger.info(f"Mounted static content from directory: {data_dir}")
else:
    app_logger.info(
        "Skipping mounting of frontend and data static files in test environment (RUN_ENV=test).")

# Dependency to get DB session


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    error_logger.error(
        # Existing log
        f"LOGIN_TOKEN: Attempting login for username: {form_data.username}")
    user = auth.authenticate_user(db, form_data.username, form_data.password)

    if not user:
        error_logger.error(
            # New log
            f"LOGIN_TOKEN: auth.authenticate_user returned no user for {form_data.username}. Raising 401.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    error_logger.error(
        # New log
        f"LOGIN_TOKEN: User {user.username} authenticated successfully. Creating access token.")

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    error_logger.error(
        # New log
        f"LOGIN_TOKEN: Access token created for {user.username}. Token (first 10): {access_token[:10]}...")

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/")
async def root():
    return {"message": "Story Generator API"}

# Placeholder for current user endpoint (requires token verification)


@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(current_user: schemas.User = Depends(auth.get_current_active_user)):
    return current_user

# Admin only placeholder endpoint


@app.get("/admin/placeholder")
async def admin_placeholder_endpoint(current_user: schemas.User = Depends(auth.get_current_admin_user)):
    return PlainTextResponse("This is a placeholder for the admin dashboard.", media_type="text/plain")

# --- Admin User Management Endpoints --- # REMOVE THIS SECTION
# All routes previously under "/admin/users" and "/admin/dynamic-lists" and "/admin/dynamic-list-items"
# are now handled by the routers imported from admin_router.py.
# The following duplicated definitions will be removed:
# @app.get("/admin/users", response_model=List[schemas.User], tags=["Admin - User Management"]) ...
# ... all admin user management endpoints ...
# @app.delete("/admin/users/{user_id}", status_code=204, tags=["Admin - User Management"]) ...

@app.get("/stories/", response_model=List[schemas.Story])
async def read_user_stories(
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
    skip: int = 0,
    limit: int = 100,  # Default to 100 stories, can be adjusted
    include_drafts: bool = True  # FR24: Added to fetch drafts or only published
):
    app_logger.info(
        f"User {current_user.username} requested their stories. Skip: {skip}, Limit: {limit}, Include Drafts: {include_drafts}")
    stories = crud.get_stories_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit, include_drafts=include_drafts)
    if not stories:
        app_logger.info(f"No stories found for user {current_user.username}.")
    # Return empty list if no stories, frontend handles this.
    return stories


@app.get("/stories/{story_id}", response_model=schemas.Story)
async def read_story(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} requested story with ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id)
    if db_story is None:
        error_logger.warning(
            f"Story with ID {story_id} not found for user {current_user.username}.")
        raise HTTPException(status_code=404, detail="Story not found")
    if db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to access unauthorized story {story_id}.")
        raise HTTPException(
            status_code=403, detail="Not authorized to access this story")
    app_logger.info(
        f"Story {story_id} ({db_story.title}) retrieved for user {current_user.username}.")
    return db_story


@app.put("/stories/{story_id}/title", response_model=schemas.Story)
async def update_story_title_endpoint(
    story_id: int,
    title_update: schemas.StoryTitleUpdate,  # This schema will need to be created
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} attempting to update title for story ID: {story_id} to '{title_update.title}'")
    db_story = crud.get_story(db, story_id=story_id)

    if not db_story:
        error_logger.warning(
            f"Story with ID {story_id} not found for title update attempt by user {current_user.username}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    if db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to update title for unauthorized story {story_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to update this story's title")

    updated_story = crud.update_story_title(
        db=db, story_id=story_id, new_title=title_update.title)
    if not updated_story:
        # This case should ideally not be reached if the above checks pass and crud.update_story_title is robust
        error_logger.error(
            f"Failed to update title for story {story_id} for user {current_user.username}, though initial checks passed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not update story title")

    app_logger.info(
        f"Story ID {story_id} title successfully updated to '{updated_story.title}' by user {current_user.username}.")
    return updated_story


@app.delete("/stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story_endpoint(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} attempting to delete story ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id)

    if not db_story:
        error_logger.warning(
            f"Story with ID {story_id} not found for deletion attempt by user {current_user.username}.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    if db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to delete unauthorized story {story_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to delete this story")

    # Attempt to delete associated images first (optional, depends on desired behavior)
    # This is a simplified example; more robust error handling and path construction might be needed.
    # Consider moving image deletion logic into the crud.delete_story_db_entry function.
    story_image_folder_on_disk = os.path.join(
        "data", "images", f"user_{current_user.id}", f"story_{story_id}")
    if os.path.exists(story_image_folder_on_disk):
        try:
            # shutil.rmtree(story_image_folder_on_disk) # More thorough, but requires import shutil
            # For now, let's assume we only delete files if the folder might contain other things or for simplicity
            # This part needs careful implementation based on how images are stored and if subfolders exist.
            # For now, we will rely on the CRUD operation to handle DB consistency.
            # Physical file deletion can be complex and might be handled by a background task or specific utility.
            app_logger.info(
                f"Image folder found for story {story_id}: {story_image_folder_on_disk}. Deferring physical file deletion.")
        except Exception as e:
            error_logger.error(
                f"Error trying to delete image folder {story_image_folder_on_disk} for story {story_id}: {e}")
            # Decide if this should prevent story deletion from DB or just log.

    deleted_successfully = crud.delete_story_db_entry(db=db, story_id=story_id)

    if not deleted_successfully:
        error_logger.error(
            f"Failed to delete story {story_id} from database for user {current_user.username}, though initial checks passed.")
        # crud.delete_story_db_entry should ideally raise an exception if it fails internally after checks.
        # If it returns False, it implies a condition not caught by pre-checks (e.g. DB error during delete)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Could not delete story from database.")

    app_logger.info(
        f"Story ID {story_id} successfully deleted by user {current_user.username}.")
    # No content is returned for a 204 response, so no need for 'return' with a body.
    return  # FastAPI will handle the 204 response


@app.post("/stories/drafts/", response_model=schemas.Story)
async def create_story_draft_endpoint(
    story_input: schemas.StoryCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} creating a new story draft with input: {story_input.model_dump(exclude_none=True)}")
    try:
        db_story_draft = crud.create_story_draft(
            db=db, story_data=story_input, user_id=current_user.id
        )
        app_logger.info(
            f"Story draft created with ID: {db_story_draft.id} for user {current_user.username}")
        return db_story_draft
    except Exception as e:
        error_logger.error(
            f"Error creating story draft for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create story draft: {str(e)}"
        )


@app.put("/stories/drafts/{story_id}", response_model=schemas.Story)
async def update_story_draft_endpoint(
    story_id: int,
    # Use StoryCreate as it contains all editable fields for a draft
    story_update_data: schemas.StoryCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} updating draft ID: {story_id} with data: {story_update_data.model_dump(exclude_none=True)}")

    # Verify the draft exists and belongs to the user
    existing_draft = crud.get_story(db, story_id=story_id)
    if not existing_draft or existing_draft.owner_id != current_user.id or not existing_draft.is_draft:
        error_logger.warning(
            f"User {current_user.username} attempted to update non-existent or unauthorized draft ID: {story_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found or not authorized to update")

    try:
        updated_draft = crud.update_story_draft(
            db=db, story_id=story_id, story_update_data=story_update_data, user_id=current_user.id
        )
        if not updated_draft:
            # This case should be caught by the check above, but as a safeguard:
            error_logger.error(
                f"Update_story_draft returned None for draft {story_id} for user {current_user.username} despite initial checks.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Draft not found during update attempt.")

        app_logger.info(
            f"Story draft ID: {updated_draft.id} updated successfully by user {current_user.username}")
        return updated_draft
    except Exception as e:
        error_logger.error(
            f"Error updating story draft ID {story_id} for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not update story draft: {str(e)}"
        )


@app.post("/stories/", response_model=schemas.Story)
async def create_new_story(
    story_input: schemas.StoryCreate,  # This is the base input from the user
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
    # Optional: ID of the draft being finalized
    draft_id: Optional[int] = Body(None)
):
    app_logger.info(
        f"User {current_user.username} initiating new story creation. Input: {story_input.model_dump(exclude_none=True)}. Draft ID: {draft_id}")

    # Ensure db_story is typed for clarity
    db_story: Optional[database.Story] = None
    # initial_title is used for the first DB entry before AI generation, or for finalize_story_draft call.
    initial_title_for_db_operation = story_input.title if story_input.title and story_input.title.strip(
    ) else "[AI Title Pending...]"

    if draft_id:
        app_logger.info(
            f"Finalizing draft ID: {draft_id} for user {current_user.username}")
        # First, update the draft with any last-minute changes from story_input.
        # crud.update_story_draft should fetch the draft, check ownership, update fields, and return the updated draft.
        # It should not change is_draft status.
        updated_draft_before_finalize = crud.update_story_draft(
            db, draft_id, story_input, current_user.id)
        if not updated_draft_before_finalize:
            error_logger.warning(
                f"Draft ID {draft_id} not found or not authorized for finalization by user {current_user.username}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Draft to finalize not found or not authorized.")

        # Now, finalize it (sets is_draft=False, generated_at, and potentially a new title if provided by initial_title_for_db_operation)
        # The title passed here is the one from the current user input, which might update the draft's existing title.
        db_story = crud.finalize_story_draft(
            db, draft_id, current_user.id, title=initial_title_for_db_operation)
        if not db_story:
            error_logger.error(
                f"Failed to finalize draft {draft_id} for user {current_user.username} after successful update.")
            raise HTTPException(
                status_code=500, detail="Internal server error: Unable to finalize draft.")
        app_logger.info(
            f"Draft {draft_id} finalized. Story ID is now {db_story.id}, Title: {db_story.title}")
    else:
        app_logger.info(
            f"Creating new story from scratch (not from draft) for user {current_user.username}. Initial title for DB: {initial_title_for_db_operation}")
        db_story = crud.create_story_db_entry(
            db=db,
            story_data=story_input,
            user_id=current_user.id,
            title=initial_title_for_db_operation,  # Use the derived initial title
            is_draft=False
        )
        if not db_story:
            error_logger.error(
                f"Failed to create preliminary story entry for user {current_user.username}.")
            raise HTTPException(
                status_code=500, detail="Internal server error: Unable to create story entry.")
        app_logger.info(
            f"Preliminary story entry created with ID: {db_story.id}, Title: {db_story.title}")

    # Prepare paths for character reference images
    user_images_base_path_for_db = f"images/user_{current_user.id}"
    story_folder_name_for_db = f"story_{db_story.id}"
    char_ref_image_subfolder_name = "references"

    # Path relative to 'data/' for storing in DB character details
    char_ref_image_path_base_for_db = os.path.join(
        user_images_base_path_for_db, story_folder_name_for_db, char_ref_image_subfolder_name)
    # Actual disk directory to save reference images
    char_ref_image_dir_on_disk = os.path.join(
        "data", char_ref_image_path_base_for_db)
    os.makedirs(char_ref_image_dir_on_disk, exist_ok=True)

    updated_main_characters = []
    if story_input.main_characters:
        if not draft_id:  # Only generate new reference images if NOT finalizing a draft
            app_logger.info(
                f"Generating new character reference images as this is not a draft finalization.")
            for char_detail_input in story_input.main_characters:
                try:
                    updated_char_info_dict = ai_services.generate_character_reference_image(
                        character=char_detail_input,
                        user_id=current_user.id,
                        story_id=db_story.id,
                        image_style_enum=story_input.image_style
                    )
                    updated_main_characters.append(updated_char_info_dict)
                    app_logger.info(
                        f"Generated reference image and updated details for character: {updated_char_info_dict.get('name')}")
                except Exception as e:
                    error_logger.error(
                        f"Error generating reference image for character {char_detail_input.name}: {e}", exc_info=True)
                    updated_main_characters.append(
                        char_detail_input.model_dump(exclude_none=True))
        # If finalizing a draft, check for missing reference images and generate them
        else:
            app_logger.info(
                f"Draft finalization (ID: {draft_id}): Checking for missing character reference images.")
            for char_detail_input in story_input.main_characters:
                # Convert CharacterDetailCreate to dict to check/update reference_image_path
                char_dict = char_detail_input.model_dump(exclude_none=True)
                if not char_dict.get('reference_image_path'):
                    app_logger.info(
                        f"Missing reference image for character: {char_detail_input.name}. Generating now.")
                    try:
                        updated_char_info_dict = ai_services.generate_character_reference_image(
                            character=char_detail_input,  # Pass the Pydantic model
                            user_id=current_user.id,
                            story_id=db_story.id,
                            image_style_enum=story_input.image_style  # Use story's image style
                        )
                        updated_main_characters.append(updated_char_info_dict)
                        app_logger.info(
                            f"Generated reference image and updated details for character: {updated_char_info_dict.get('name')}")
                    except Exception as e:
                        error_logger.error(
                            f"Error generating reference image for character {char_detail_input.name} during draft finalization: {e}", exc_info=True)
                        # Append original details if generation fails
                        updated_main_characters.append(char_dict)
                else:
                    app_logger.info(
                        f"Character {char_detail_input.name} already has a reference image: {char_dict.get('reference_image_path')}. Using existing.")
                    updated_main_characters.append(char_dict)
    else:
        app_logger.info(
            "No main characters provided in input. Skipping reference image generation.")

    ai_story_input_data = story_input.model_dump(exclude_none=True)
    ai_story_input_data['main_characters'] = updated_main_characters

    app_logger.info(
        f"Data prepared for AI story generation: {ai_story_input_data}")

    try:
        generated_content = ai_services.generate_story_from_chatgpt(
            ai_story_input_data)
        app_logger.info(
            f"Story content successfully generated by AI. Title from AI: {generated_content.get('Title')}")
    except ValueError as ve:
        error_logger.error(
            f"ValueError during AI story generation: {ve}", exc_info=True)
        crud.delete_story_db_entry(db=db, story_id=db_story.id)
        app_logger.warning(
            f"Preliminary story entry {db_story.id} deleted due to AI generation error.")
        raise HTTPException(
            status_code=400, detail=f"AI Generation Error: {str(ve)}")
    except Exception as e:
        error_logger.error(
            f"Unexpected error during AI story generation: {e}", exc_info=True)
        crud.delete_story_db_entry(db=db, story_id=db_story.id)
        app_logger.warning(
            f"Preliminary story entry {db_story.id} deleted due to AI generation error.")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate story content: {str(e)}")

    # Determine the final story title
    # Priority: 1. AI-generated title, 2. User-provided title (if not placeholder), 3. Default
    final_story_title: str
    ai_provided_title = generated_content.get("Title")
    user_provided_title_stripped = story_input.title.strip() if story_input.title else None

    if ai_provided_title:
        final_story_title = ai_provided_title
    elif user_provided_title_stripped and user_provided_title_stripped != "[AI Title Pending...]":
        final_story_title = user_provided_title_stripped
    else:
        # If AI provides no title, and user provided nothing or only placeholder, use a default.
        # This case also covers when initial_title_for_db_operation was "[AI Title Pending...]" and AI didn't override.
        final_story_title = "Untitled Story"

    app_logger.info(
        f"Final story title determined as: '{final_story_title}'. Current db_story.title: '{db_story.title}'")

    if db_story.title != final_story_title:
        updated_story_obj = crud.update_story_title(
            db=db, story_id=db_story.id, new_title=final_story_title)
        if updated_story_obj:
            db_story = updated_story_obj  # Ensure db_story is the updated object for the response
            app_logger.info(
                f"Story ID {db_story.id} title updated by AI/logic to: '{db_story.title}'")
        else:
            error_logger.error(
                f"crud.update_story_title returned None for story {db_story.id} when trying to set title to '{final_story_title}'. Proceeding with title '{db_story.title}'.")
            # If update fails, db_story retains its previous title. The response will reflect that.

    # Prepare base paths for story page images
    # user_images_base_path_for_db defined earlier: f"images/user_{current_user.id}"
    # story_folder_name_for_db defined earlier: f"story_{db_story.id}"
    story_page_image_path_for_db_base = os.path.join(
        # e.g., images/user_1/story_123
        user_images_base_path_for_db, story_folder_name_for_db)
    story_page_image_dir_on_disk = os.path.join(
        "data", story_page_image_path_for_db_base)  # e.g., data/images/user_1/story_123
    # Ensure directory exists
    os.makedirs(story_page_image_dir_on_disk, exist_ok=True)

    created_pages_db = []
    # The character_name_to_ref_image_map is not strictly needed if iterating updated_main_characters directly below,
    # but it's harmless if updated_main_characters is the source of truth.

    for page_data_from_ai in generated_content.get("Pages", []):
        page_number_from_ai = page_data_from_ai.get("Page_number")
        db_page_number = 0 if page_number_from_ai == "Title" else int(
            page_number_from_ai)

        page_to_create = schemas.PageCreate(
            page_number=db_page_number,
            text=page_data_from_ai.get(
                "text", page_data_from_ai.get("Text", "")),
            image_description=page_data_from_ai.get(
                "image_description", page_data_from_ai.get("Image_description"))
        )

        db_page = crud.create_story_page(
            db=db,
            page=page_to_create,
            story_id=db_story.id
        )

        if page_to_create.image_description:
            try:
                image_filename_prefix = "cover" if db_page_number == 0 else f"page_{db_page.page_number}"
                unique_suffix = uuid.uuid4().hex[:8]
                image_filename = f"{image_filename_prefix}_{unique_suffix}_story_{db_story.id}_pageid_{db_page.id}.png"
                image_save_path_on_disk = os.path.join(
                    story_page_image_dir_on_disk, image_filename)

                char_name_for_ref_prompt: Optional[str] = None
                char_ref_paths_for_page: Optional[List[str]] = None

                page_characters_in_scene = page_data_from_ai.get(
                    "Characters_in_scene", [])
                app_logger.debug(
                    f"Page {db_page.page_number} (AI: {page_number_from_ai}): Characters in scene from AI: {page_characters_in_scene}")

                if page_characters_in_scene:
                    for char_name_in_scene in page_characters_in_scene:
                        found_char_detail = next((
                            char_detail for char_detail in updated_main_characters
                            if char_detail.get("name") == char_name_in_scene
                        ), None)

                        if found_char_detail:
                            # Always set the character name if a character from the scene is identified in main_characters
                            char_name_for_ref_prompt = found_char_detail.get(
                                "name")
                            ref_path_from_char_detail = found_char_detail.get(
                                "reference_image_path")

                            if ref_path_from_char_detail:
                                full_ref_image_disk_path = os.path.join(
                                    "data", ref_path_from_char_detail)
                                if os.path.exists(full_ref_image_disk_path):
                                    char_ref_paths_for_page = [
                                        full_ref_image_disk_path]
                                    app_logger.info(
                                        f"Found reference image for character '{char_name_for_ref_prompt}' for page {db_page.page_number}: {full_ref_image_disk_path}")
                                    break  # Use the first character found with an existing reference image
                                else:
                                    error_logger.warning(
                                        f"Reference image file for character '{char_name_for_ref_prompt}' ({full_ref_image_disk_path}) does not exist. Will not use for edit, but name is set.")
                            # else: No reference_image_path recorded for this character detail. Character name is still set.
                        # else: Character name from scene not found in main_characters list.
                        if char_ref_paths_for_page:  # If we found a valid ref path, stop searching chars in scene
                            break

                app_logger.debug(
                    f"Page {db_page.page_number}: char_name_for_ref_prompt='{char_name_for_ref_prompt}', char_ref_paths_for_page={char_ref_paths_for_page}")

                image_generation_result = ai_services.generate_image(
                    page_image_description=page_to_create.image_description,
                    image_path=image_save_path_on_disk,
                    character_reference_image_paths=char_ref_paths_for_page,
                    character_name_for_reference=char_name_for_ref_prompt
                )

                image_path_for_db = os.path.join(
                    story_page_image_path_for_db_base, image_filename)
                db_page = crud.update_page_image_path(
                    db=db, page_id=db_page.id, image_path=image_path_for_db)
                app_logger.info(
                    f"Generated and saved image for page_number {db_page.page_number} (DB ID: {db_page.id}) at {image_path_for_db} (on disk: {image_save_path_on_disk})")
            except Exception as e:
                error_logger.error(
                    f"Failed to generate or save image for page_number {db_page.page_number} (DB ID: {db_page.id}): {e}", exc_info=True)

        created_pages_db.append(db_page)

    db.refresh(db_story)

    story_response = schemas.Story.model_validate(db_story)

    app_logger.info(
        f"Story creation process completed for story ID {db_story.id}. Title: {story_response.title}. Pages: {len(story_response.pages)}")
    return story_response


@app.get("/stories/{story_id}/pdf", status_code=status.HTTP_200_OK)
async def export_story_as_pdf(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} requested PDF for story ID: {story_id}")
    db_story = crud.get_story(db, story_id=story_id)
    if not db_story or db_story.owner_id != current_user.id:
        error_logger.warning(
            f"User {current_user.username} attempted to access unauthorized or non-existent story PDF: {story_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Story not found or access denied.")

    try:
        # Use asyncio.to_thread for the potentially blocking PDF generation call
        pdf_content_bytes = await asyncio.to_thread(pdf_generator.create_story_pdf, db_story)
        app_logger.info(
            f"PDF generated for story {story_id} for user {current_user.username}")

        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in (
            ' ', '-', '_') else '' for c in db_story.title).rstrip()
        if not safe_title:  # handle cases where title might become empty after sanitization
            safe_title = f"story_{db_story.id}"

        return StreamingResponse(io.BytesIO(pdf_content_bytes), media_type="application/pdf",
                                 headers={"Content-Disposition": f"attachment; filename={safe_title}.pdf"})
    except Exception as e:
        error_logger.error(
            f"Failed to generate PDF for story {story_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {e}")


# Dependency for getting current user
async def get_current_active_user(current_user: schemas.User = Depends(auth.get_current_active_user)):
    # Add any checks for active status if necessary, e.g., user.disabled
    if not current_user:  # Or any other active check
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Endpoint to get a specific story draft by ID


@app.get("/stories/drafts/{story_id}", response_model=schemas.Story)
async def read_story_draft(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    db_story_draft = crud.get_story_draft(
        db, story_id=story_id, user_id=current_user.id)
    if db_story_draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return db_story_draft


# --- Admin Endpoints for Dynamic Content Management (FR-ADM-05) --- # REMOVE THIS SECTION
# All routes previously under "/admin/users" and "/admin/dynamic-lists" and "/admin/dynamic-list-items"
# are now handled by the routers imported from admin_router.py.
# The following duplicated definitions will be removed:
# # Dynamic Lists
# @app.post("/admin/dynamic-lists/", response_model=schemas.DynamicList, tags=["Admin - Dynamic Content"]) ...
# ... all admin dynamic list and dynamic list item endpoints ...
# @app.get("/admin/dynamic-list-items/{item_id}/in-use", response_model=dict, tags=["Admin - Dynamic Content"]) ...


# --- Public Endpoints for Dynamic Content ---


@app.get("/dynamic-lists/{list_name}/active-items", response_model=List[schemas.DynamicListItem])
def get_active_list_items(
    list_name: str,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to fetch active and sorted items for a given dynamic list.
    Used for populating frontend dropdowns (e.g., genres, image styles).
    """
    # First, check if the list itself exists to provide a clear 404 if not
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynamic list '{list_name}' not found."
        )

    items = crud.get_active_dynamic_list_items(db, list_name=list_name)
    # No need to check if items is None or empty here, an empty list is a valid response
    return items
