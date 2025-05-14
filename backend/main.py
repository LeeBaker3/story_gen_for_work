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


@app.post("/stories/", response_model=schemas.Story, status_code=status.HTTP_201_CREATED)
async def create_new_story(
    story_input: schemas.StoryCreate,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        # Added ratio and text_density to log
        f"User {current_user.username} initiated story creation with input: {story_input.genre}, ratio: {story_input.word_to_picture_ratio}, density: {story_input.text_density}")
    api_logger.debug(
        f"Story creation input for user {current_user.username}: {jsonable_encoder(story_input)}")

    try:
        # 1. Generate story content from ChatGPT
        # This now includes word_to_picture_ratio and text_density
        ai_story_input_dict = story_input.dict()
        generated_content = await asyncio.to_thread(ai_services.generate_story_from_chatgpt, ai_story_input_dict)

        api_logger.info(
            f"ChatGPT generated content for user {current_user.username}")
        api_logger.debug(f"ChatGPT response: {generated_content}")

        story_title = generated_content.get("Title", "Untitled Story")
        ai_pages_data = generated_content.get("Pages", [])

        if not ai_pages_data:
            error_logger.error(
                f"No pages generated by AI for input: {ai_story_input_dict}")
            raise HTTPException(
                status_code=500, detail="AI failed to generate story pages.")

        # 2. Create initial story and character entries in the database
        db_story = crud.create_story_db_entry(
            db=db, story_data=story_input, user_id=current_user.id, title=story_title)
        app_logger.info(
            f"Initial Story '{story_title}' (ID: {db_story.id}) and character entries created in DB for user {current_user.username}")

        # 3. Generate character reference images and update character DB entries
        if story_input.main_characters:
            story_image_root_dir = os.path.join(
                "data", "images", f"user_{current_user.id}", f"story_{db_story.id}")
            app_logger.info(
                f"Starting reference image generation for {len(story_input.main_characters)} characters for story ID {db_story.id} in {story_image_root_dir}.")

            updated_main_characters_for_db = []

            for char_detail_input in story_input.main_characters:
                char_as_dict = jsonable_encoder(char_detail_input)
                char_as_dict['reference_image_path'] = None

                try:
                    api_logger.debug(
                        f"Generating reference image for character '{char_detail_input.name}' for story {db_story.id}")
                    generated_ref_path = await asyncio.to_thread(
                        ai_services.generate_character_reference_image,
                        char_detail_input,
                        story_image_root_dir
                    )
                    char_as_dict['reference_image_path'] = generated_ref_path
                    app_logger.info(
                        f"Reference image for character '{char_detail_input.name}' saved to {generated_ref_path}")
                except Exception as char_img_exc:
                    error_logger.error(
                        f"Failed to generate reference image for character '{char_detail_input.name}' for story {db_story.id}: {char_img_exc}",
                        exc_info=True
                    )
                updated_main_characters_for_db.append(char_as_dict)

            db_story.main_characters = updated_main_characters_for_db
            db.commit()
            db.refresh(db_story)
            app_logger.info(
                f"Finished reference image generation and DB updates for story ID {db_story.id}.")
        else:
            app_logger.info(
                f"No characters provided in input for story ID {db_story.id}. Skipping reference image generation.")

        # 4. Process each page: generate image (if applicable), save page to DB
        created_pages_schemas = []
        for ai_page in ai_pages_data:
            page_text = ai_page.get("Text")
            image_prompt = ai_page.get("Image_description")  # This can be None
            page_number = ai_page.get("Page_number")

            # A page must have text and a page number. Image_description is optional based on ratio.
            if page_text is None or page_number is None:
                error_logger.warning(
                    f"Skipping page due to missing Text or Page_number from AI for story {db_story.id}: {ai_page}")
                continue

            actual_image_path = None  # Initialize to None

            # Only generate image if image_prompt is a non-empty string
            if isinstance(image_prompt, str) and image_prompt.strip():
                image_filename = f"{uuid.uuid4()}.png"
                image_save_path = os.path.join(
                    "data", "images", f"user_{current_user.id}", f"story_{db_story.id}", image_filename)
                try:
                    api_logger.debug(
                        f"Generating image for story {db_story.id}, page {page_number} with prompt: {image_prompt}")
                    actual_image_path = await asyncio.to_thread(
                        ai_services.generate_image_from_dalle, image_prompt, image_save_path)
                    app_logger.info(
                        f"Image saved to {actual_image_path} for story {db_story.id}, page {page_number}")
                except Exception as img_exc:
                    error_logger.error(
                        f"Failed to generate/save image for story {db_story.id}, page {page_number}: {img_exc}", exc_info=True)
                    actual_image_path = None  # Ensure it's None on failure
            else:
                app_logger.info(
                    f"No image generation for story {db_story.id}, page {page_number} as Image_description is null, empty, or not a string ('{image_prompt}').")

            page_create_schema = schemas.PageCreate(
                page_number=page_number,
                text=page_text,
                # Store the original prompt (string or None)
                image_description=image_prompt
            )
            db_page = crud.create_story_page(
                db=db, page=page_create_schema, story_id=db_story.id, image_path=actual_image_path)
            created_pages_schemas.append(schemas.Page.from_orm(db_page))

        db.refresh(db_story)
        final_story = crud.get_story(db, db_story.id)
        if not final_story:
            error_logger.error(
                f"Failed to re-fetch story {db_story.id} after page creation.")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve story after creation.")

        app_logger.info(
            f"Successfully generated story '{final_story.title}' (ID: {final_story.id}) for user {current_user.username}")
        return final_story

    except ValueError as ve:
        error_logger.error(
            f"ValueError during story generation for user {current_user.username}: {ve}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"AI service error: {ve}")
    except ai_services.openai.APIError as api_err:
        error_logger.error(
            f"OpenAI APIError during story generation for user {current_user.username}: {api_err}", exc_info=True)
        raise HTTPException(
            status_code=502, detail=f"AI provider error: {api_err}")
    except HTTPException:
        raise
    except Exception as e:
        error_logger.error(
            f"Unexpected error during story generation for user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {e}")


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
                                 headers={"Content-Disposition": f"attachment; filename=\"{safe_title}.pdf\""})
    except Exception as e:
        error_logger.error(
            f"Failed to generate PDF for story {story_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {e}")
