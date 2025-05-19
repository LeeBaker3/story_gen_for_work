from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse  # Added for PDF streaming
from fastapi.staticfiles import StaticFiles  # Added for static files
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid  # For unique image filenames
import asyncio
import os
import io  # Added for BytesIO
from typing import List  # Added for List type hint

# Added pdf_generator
from . import crud, schemas, auth, database, ai_services, pdf_generator
from .logging_config import app_logger, api_logger, error_logger

# Create database tables
database.Base.metadata.create_all(bind=database.engine)

app = FastAPI()


@app.get("/genres/", response_model=List[schemas.StoryGenre])
async def get_story_genres():
    app_logger.info("Requested story genres list.")
    sorted_genres = sorted([genre.value for genre in schemas.StoryGenre])
    return sorted_genres

# Mount static files directory for frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static_frontend")

# Mount static files directory (for images)
# This will serve files from the 'data' directory under the '/static_content' path
# e.g., an image at data/images/user_1/story_1/foo.png will be accessible at /static_content/images/user_1/story_1/foo.png
app.mount("/static_content", StaticFiles(directory="data"),
          name="static_content")

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


@app.get("/stories/", response_model=List[schemas.Story])
async def read_user_stories(
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
    skip: int = 0,
    limit: int = 100  # Default to 100 stories, can be adjusted
):
    app_logger.info(
        f"User {current_user.username} requested their stories. Skip: {skip}, Limit: {limit}")
    stories = crud.get_stories_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit)
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


@app.post("/stories/", response_model=schemas.Story)
async def create_new_story(
    story_input: schemas.StoryCreate,
    db: Session = Depends(database.get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} initiating new story creation with input: {story_input.model_dump(exclude_none=True)}")

    # Determine initial title for DB entry
    initial_title = story_input.title if story_input.title and story_input.title.strip(
    ) else "[AI Title Pending...]"
    app_logger.info(f"Initial title for DB: {initial_title}")

    db_story = crud.create_story_db_entry(
        db=db,
        story_data=story_input,  # Corrected: Pass the story_input object directly
        user_id=current_user.id,
        title=initial_title
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
        for char_detail_input in story_input.main_characters:
            # char_detail_dict = char_detail_input.model_dump(exclude_none=True) # Not needed if passing model directly
            try:
                # Assuming generate_character_reference_image now expects 'character' (Pydantic model)
                # and handles its own image saving path construction using user_id, story_id,
                # returning updated character details with 'reference_image_path' relative to 'data/'.
                # If it needs explicit paths, its signature and call would be different.
                # For now, only fixing the 'character_data' to 'character' based on error.
                updated_char_info_dict = ai_services.generate_character_reference_image(
                    character=char_detail_input,  # Changed from character_data=char_detail_dict
                    user_id=current_user.id,
                    story_id=db_story.id,
                    image_style_enum=story_input.image_style
                    # If generate_character_reference_image needs save_directory_on_disk and db_path_prefix:
                    # save_directory_on_disk=char_ref_image_dir_on_disk,
                    # db_path_prefix=char_ref_image_path_base_for_db
                )
                updated_main_characters.append(updated_char_info_dict)
                app_logger.info(
                    f"Generated reference image and updated details for character: {updated_char_info_dict.get('name')}")
            except Exception as e:
                error_logger.error(
                    f"Error generating reference image for character {char_detail_input.name}: {e}", exc_info=True)
                # Append original dict if error, or handle differently
                updated_main_characters.append(
                    char_detail_input.model_dump(exclude_none=True))

    ai_story_input_data = story_input.model_dump(exclude_none=True)
    ai_story_input_data['main_characters'] = updated_main_characters

    app_logger.info(
        f"Data prepared for AI story generation: {ai_story_input_data}")

    try:
        generated_content = ai_services.generate_story_from_chatgpt(
            ai_story_input_data)
        app_logger.info(
            f"Story content successfully generated by AI. Title: {generated_content.get('Title')}")
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

    final_story_title = initial_title
    if initial_title == "[AI Title Pending...]" or not story_input.title:
        final_story_title = generated_content.get(
            "Title", "Untitled Story from AI")
    app_logger.info(f"Final story title determined as: {final_story_title}")

    if db_story.title != final_story_title:
        db_story = crud.update_story_title(
            db=db, story_id=db_story.id, new_title=final_story_title)
        app_logger.info(
            f"Story ID {db_story.id} title updated to: {db_story.title}")

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
    for page_data_from_ai in generated_content.get("Pages", []):
        page_number_from_ai = page_data_from_ai.get("Page_number")

        # Convert "Title" page number to 0 for DB storage.
        # Assumes Page model's page_number field in DB is an Integer.
        # If your Page model expects a string for page_number, this conversion isn't needed.
        db_page_number = 0 if page_number_from_ai == "Title" else int(
            page_number_from_ai)

        page_to_create = schemas.PageCreate(
            page_number=db_page_number,
            text=page_data_from_ai.get("text", page_data_from_ai.get(
                "Text", "")),  # Handle potential casing diff from AI
            image_description=page_data_from_ai.get(
                # Handle casing
                "image_description", page_data_from_ai.get("Image_description"))
        )

        db_page = crud.create_story_page(
            db=db,
            page=page_to_create,  # Corrected keyword argument from page_data to page
            story_id=db_story.id
            # The create_story_page function in crud.py handles the optional image_path,
            # which will be None initially here. It will be updated later if an image is generated.
        )

        if page_to_create.image_description:
            try:
                # Differentiating cover image filename slightly for clarity, though not strictly necessary
                image_filename_prefix = "cover" if db_page_number == 0 else f"page_{db_page.page_number}"
                # Create a unique filename for the image
                unique_suffix = uuid.uuid4().hex[:8]
                image_filename = f"{image_filename_prefix}_{unique_suffix}_story_{db_story.id}_pageid_{db_page.id}.png"

                # Full path on disk where the image will be saved
                image_save_path_on_disk = os.path.join(
                    story_page_image_dir_on_disk, image_filename)

                # Call DALL-E service to generate and save the image
                image_generation_result = ai_services.generate_image_from_dalle(
                    prompt=page_to_create.image_description,
                    image_path=image_save_path_on_disk  # Pass the full disk path for saving
                )

                # The path to be stored in the database (relative to the 'data' directory)
                image_path_for_db = os.path.join(
                    story_page_image_path_for_db_base, image_filename)

                # image_generation_result['image_path'] should be image_save_path_on_disk
                # We use our constructed image_path_for_db for the database.
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
