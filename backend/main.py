from backend.monitoring_router import monitoring_router
from fastapi import FastAPI, Depends, HTTPException, status, Body, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import asyncio
import os
import io
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from backend import crud, schemas, auth, database, ai_services, pdf_generator
from backend.admin_router import admin_router
from backend.public_router import public_router
from backend.logging_config import app_logger, error_logger
from backend.database_seeding import seed_database
from backend.database import get_db, SessionLocal
from backend.story_generation_service import generate_story_as_background_task

# Drop all tables (for development purposes to apply schema changes)
# IMPORTANT: This will delete all existing data. Remove or comment out for production.
# database.Base.metadata.drop_all(bind=database.engine) # Commented out to prevent locking issues

# Create database tables
database.Base.metadata.create_all(bind=database.engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Application startup: Checking database for initial data.")
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(lifespan=lifespan)

# This must be defined before it's used in the router inclusion.

app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(public_router, prefix="/api/v1", tags=["public"])
app.include_router(monitoring_router, prefix="/api/v1/admin",
                   tags=["admin-monitoring"])


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


@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=400, detail="Username already registered")
    return crud.create_user(db=db, user=user)


@app.get("/")
async def root():
    return {"message": "Story Generator API"}

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


# This endpoint was moved to public_router.py to be included in the /api/v1 prefix.


# This endpoint was moved to public_router.py to be included in the /api/v1 prefix.


@app.put("/stories/{story_id}/title", response_model=schemas.Story)
async def update_story_title_endpoint(
    story_id: int,
    title_update: schemas.StoryTitleUpdate,  # This schema will need to be created
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} attempting to update title for story ID: {story_id} to '{title_update.title}'")
    db_story = crud.get_story(db, story_id=story_id, user_id=current_user.id)

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
    db_story = crud.get_story(db, story_id=story_id, user_id=current_user.id)

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
    existing_draft = crud.get_story(
        db, story_id=story_id, user_id=current_user.id)
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


@app.post("/stories/", response_model=schemas.Story, status_code=status.HTTP_201_CREATED)
async def create_new_story(
    story_input: schemas.StoryCreate,  # This is the base input from the user
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
    # Optional: ID of the draft being finalized
    draft_id: Optional[int] = Body(None)
):
    app_logger.info(
        f"User {current_user.username} initiating new story creation. Input: {story_input.model_dump(exclude_none=True)}. Draft ID: {draft_id}")

    # Check if a story with the same title already exists for this user, but only if not finalizing a draft
    if not draft_id and story_input.title and crud.get_story_by_title_and_owner(db, title=story_input.title, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A story with this title already exists."
        )

    # Create a story shell first
    initial_title = story_input.title or "[AI Title Pending...]"
    db_story = crud.create_story_db_entry(
        db=db,
        story_data=story_input,
        user_id=current_user.id,
        title=initial_title,  # Use the derived initial title
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
                    # Build file paths for saving
                    char_image_filename = f"{char_detail_input.name.replace(' ', '_')}_ref_story_{db_story.id}.png"
                    char_image_save_path_on_disk = os.path.join(
                        char_ref_image_dir_on_disk, char_image_filename)
                    char_image_path_for_db = os.path.join(
                        char_ref_image_path_base_for_db, char_image_filename)
                    updated_char_info_dict = await ai_services.generate_character_reference_image(
                        character=char_detail_input,
                        story_input=story_input,
                        db=db,
                        user_id=current_user.id,
                        story_id=db_story.id,
                        image_save_path_on_disk=char_image_save_path_on_disk,
                        image_path_for_db=char_image_path_for_db
                    )
                    # Add reference_image_path to character dict for DB/frontend
                    char_dict = char_detail_input.model_dump(exclude_none=True)
                    char_dict['reference_image_path'] = char_image_path_for_db if updated_char_info_dict else None
                    updated_main_characters.append(char_dict)
                    app_logger.info(
                        f"Generated reference image and updated details for character: {char_detail_input.name}")
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
                        # Build file paths for saving
                        char_image_filename = f"{char_detail_input.name.replace(' ', '_')}_ref_story_{db_story.id}.png"
                        char_image_save_path_on_disk = os.path.join(
                            char_ref_image_dir_on_disk, char_image_filename)
                        char_image_path_for_db = os.path.join(
                            char_ref_image_path_base_for_db, char_image_filename)

                        updated_char_info_dict = await ai_services.generate_character_reference_image(
                            character=char_detail_input,  # Pass the Pydantic model
                            story_input=story_input,
                            db=db,
                            user_id=current_user.id,
                            story_id=db_story.id,
                            image_save_path_on_disk=char_image_save_path_on_disk,
                            image_path_for_db=char_image_path_for_db
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
    character_name_to_ref_image_map = {
        char['name']: char.get('reference_image_path')
        for char in updated_main_characters if char.get('reference_image_path')
    }

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
            image_path_for_db = None  # Initialize to None
            try:
                image_filename_prefix = "cover" if db_page_number == 0 else f"page_{db_page.page_number}"
                unique_suffix = uuid.uuid4().hex[:8]
                image_filename = f"{image_filename_prefix}_{unique_suffix}_story_{db_story.id}_pageid_{db_page.id}.png"
                image_save_path_on_disk = os.path.join(
                    story_page_image_dir_on_disk, image_filename)

                image_path_for_db = os.path.join(
                    story_page_image_path_for_db_base, image_filename)

                # Get reference images for characters in the scene
                characters_in_scene = page_data_from_ai.get(
                    "Characters_in_scene", [])
                reference_image_paths_for_page = [
                    character_name_to_ref_image_map[char_name]
                    for char_name in characters_in_scene if char_name in character_name_to_ref_image_map
                ]

                image_generation_result = await ai_services.generate_image_for_page(
                    page_content=page_to_create.image_description,
                    style_reference=str(story_input.image_style.value) if hasattr(
                        story_input.image_style, 'value') else str(story_input.image_style),
                    db=db,
                    user_id=current_user.id,
                    story_id=db_story.id,
                    page_number=db_page.page_number,
                    image_save_path_on_disk=image_save_path_on_disk,
                    image_path_for_db=image_path_for_db,
                    reference_image_paths=reference_image_paths_for_page
                )

                app_logger.info(
                    f"Image generation result for page {db_page.page_number}: {image_generation_result}")

                if image_generation_result and image_path_for_db:
                    db_page = crud.update_page_image_path(
                        db=db, page_id=db_page.id, image_path=image_path_for_db)
                    app_logger.info(
                        f"Generated and saved image for page_number {db_page.page_number} (DB ID: {db_page.id}) at {image_path_for_db} (on disk: {image_save_path_on_disk})")
                else:
                    error_logger.warning(
                        f"Image generation failed for page {db_page.page_number} of story {db_story.id}. No image path to update.")

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


@app.get("/tasks/{task_id}", response_model=schemas.StoryGenerationTask)
async def get_story_generation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} requested status of story generation task ID: {task_id}")
    task = crud.get_story_generation_task(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view this task")
    return task


# --- Public Endpoints for Dynamic Content ---


@app.get("/dynamic-lists/{list_name}/items", response_model=List[schemas.DynamicListItemPublic])
def get_public_list_items_endpoint(
    list_name: str,
    db: Session = Depends(get_db)
):
    """
    Public endpoint to fetch active, public-facing items for a given dynamic list.
    Returns a simplified list of items (value and label) for frontend dropdowns.
    """
    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynamic list '{list_name}' not found."
        )

    return crud.get_public_list_items(db, list_name=list_name)


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
