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


@app.post("/stories/", response_model=schemas.Story, status_code=status.HTTP_201_CREATED)
async def create_new_story(
    story_input: schemas.StoryCreate,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user)
):
    app_logger.info(
        f"User {current_user.username} initiated story creation with input: title='{story_input.title}', genre='{story_input.genre}', ratio='{story_input.word_to_picture_ratio}', density='{story_input.text_density}'")
    api_logger.debug(
        f"Story creation input for user {current_user.username}: {jsonable_encoder(story_input)}")

    story_data_for_ai_and_db = story_input.model_dump()

    # Determine initial title: user's input or placeholder if blank
    initial_title = story_input.title if story_input.title and story_input.title.strip(
    ) else "[AI Title Pending...]"

    try:
        # 1. Create an initial story entry in DB to get an ID
        db_story = crud.create_story_db_entry(
            db=db,
            story_data=story_input,  # Pass the original Pydantic model
            user_id=current_user.id,
            title=initial_title  # Use determined initial title
        )
        app_logger.info(
            f"Initial Story (ID: {db_story.id}, Title: '{initial_title}') created in DB for user {current_user.username}")

        # 2. Generate character reference images and update story_data_for_ai_and_db
        #    Also, prepare a list of character dicts for updating the DB directly.
        updated_db_characters_with_refs = []
        if story_data_for_ai_and_db.get("main_characters"):
            story_image_root_dir = os.path.join(
                "data", "images", f"user_{current_user.id}", f"story_{db_story.id}")
            # Ensure root story directory exists (ai_services functions also create subdirs)
            os.makedirs(story_image_root_dir, exist_ok=True)
            app_logger.info(
                f"Starting reference image generation for {len(story_data_for_ai_and_db['main_characters'])} characters for story ID {db_story.id} in {story_image_root_dir}.")

            characters_for_ai_prompt = []
            for char_input_data_dict in story_data_for_ai_and_db["main_characters"]:
                # Create a Pydantic model instance for generate_character_reference_image
                # Use the existing CharacterDetail schema
                char_detail_model = schemas.CharacterDetail(
                    **char_input_data_dict)

                # Work on a copy for AI prompt list
                temp_char_dict_for_ai = char_input_data_dict.copy()
                # Work on a copy for DB update list
                temp_char_dict_for_db = char_input_data_dict.copy()

                try:
                    api_logger.debug(
                        f"Generating reference image for character '{char_detail_model.name}' for story {db_story.id}")
                    # generate_character_reference_image now returns a dict
                    ref_image_generation_result = await asyncio.to_thread(
                        ai_services.generate_character_reference_image,
                        char_detail_model,  # Pass the Pydantic model
                        story_image_root_dir
                    )
                    generated_ref_path = ref_image_generation_result["image_path"]
                    revised_prompt_for_ref = ref_image_generation_result["revised_prompt"]
                    gen_id_for_ref = ref_image_generation_result["gen_id"]

                    temp_char_dict_for_ai['reference_image_path'] = generated_ref_path
                    temp_char_dict_for_ai['reference_image_revised_prompt'] = revised_prompt_for_ref
                    temp_char_dict_for_ai['reference_image_gen_id'] = gen_id_for_ref

                    temp_char_dict_for_db['reference_image_path'] = generated_ref_path
                    temp_char_dict_for_db['reference_image_revised_prompt'] = revised_prompt_for_ref
                    temp_char_dict_for_db['reference_image_gen_id'] = gen_id_for_ref
                    app_logger.info(
                        f"Reference image for character '{char_detail_model.name}' saved to {generated_ref_path}")
                    api_logger.info(
                        f"Reference image revised prompt for '{char_detail_model.name}': {revised_prompt_for_ref}")

                    # NEW: Generate detailed description from the reference image
                    if generated_ref_path:
                        try:
                            api_logger.debug(
                                f"Generating detailed visual description for '{char_detail_model.name}' from {generated_ref_path}")
                            detailed_description = await asyncio.to_thread(
                                ai_services.generate_detailed_description_from_image,
                                generated_ref_path,
                                char_detail_model.name,
                                char_detail_model  # Pass the full initial character detail model
                            )
                            temp_char_dict_for_ai['detailed_visual_description_from_reference'] = detailed_description
                            temp_char_dict_for_db['detailed_visual_description_from_reference'] = detailed_description
                            app_logger.info(
                                f"Generated detailed visual description for '{char_detail_model.name}'.")
                            app_logger.info(
                                f"Detailed visual description for '{char_detail_model.name}': {detailed_description}")
                        except Exception as desc_exc:
                            error_logger.error(
                                f"Failed to generate detailed visual description for '{char_detail_model.name}': {desc_exc}", exc_info=True)
                            # Explicitly set to None on failure
                            temp_char_dict_for_ai['detailed_visual_description_from_reference'] = None
                            temp_char_dict_for_db['detailed_visual_description_from_reference'] = None
                    else:
                        app_logger.warning(
                            f"Skipping detailed visual description generation for character '{char_detail_model.name}' because reference image path is missing.")
                        temp_char_dict_for_ai['detailed_visual_description_from_reference'] = None
                        temp_char_dict_for_db['detailed_visual_description_from_reference'] = None

                except Exception as char_img_exc:
                    error_logger.error(
                        f"Failed to generate reference image for character '{char_detail_model.name}' for story {db_story.id}: {char_img_exc}",
                        exc_info=True
                    )
                    temp_char_dict_for_ai['reference_image_path'] = None
                    temp_char_dict_for_db['reference_image_path'] = None
                    temp_char_dict_for_ai['reference_image_revised_prompt'] = None
                    temp_char_dict_for_db['reference_image_revised_prompt'] = None
                    temp_char_dict_for_ai['reference_image_gen_id'] = None
                    temp_char_dict_for_db['reference_image_gen_id'] = None
                    # Explicitly set detailed description to None if reference image generation fails
                    temp_char_dict_for_ai['detailed_visual_description_from_reference'] = None
                    temp_char_dict_for_db['detailed_visual_description_from_reference'] = None

                characters_for_ai_prompt.append(temp_char_dict_for_ai)
                updated_db_characters_with_refs.append(temp_char_dict_for_db)

            # Update the main_characters in story_data_for_ai_and_db for the ChatGPT prompt
            story_data_for_ai_and_db["main_characters"] = characters_for_ai_prompt

            # Update the characters in the database with their reference image paths
            db_story.main_characters = updated_db_characters_with_refs  # This is a JSON field
            db.commit()
            db.refresh(db_story)
            app_logger.info(
                f"Character reference paths updated in DB for story ID {db_story.id}.")
        else:
            app_logger.info(
                f"No characters provided in input for story ID {db_story.id}. Skipping reference image generation.")

        # 3. Generate story content (text and image descriptions) using ChatGPT
        #    story_data_for_ai_and_db will contain the user's title if provided, or None
        generated_content = await asyncio.to_thread(
            ai_services.generate_story_from_chatgpt,
            story_data_for_ai_and_db  # This now includes the optional title from user
        )
        api_logger.info(
            f"ChatGPT generated content for user {current_user.username}")
        api_logger.debug(f"ChatGPT response: {generated_content}")

        # Use AI title ONLY if user did not provide one initially
        ai_generated_title = generated_content.get(
            "Title", "Untitled Story by AI")
        final_story_title = initial_title if initial_title != "[AI Title Pending...]" else ai_generated_title

        ai_pages_data = generated_content.get("Pages", [])

        if not ai_pages_data:
            error_logger.error(
                f"No pages generated by AI for input: {story_data_for_ai_and_db}")
            # Rollback or delete the initial story entry?
            # For now, let it be and raise error.
            crud.delete_story_db_entry(db=db, story_id=db_story.id)
            app_logger.warning(
                f"Rolled back story entry {db_story.id} due to AI page generation failure.")
            raise HTTPException(
                status_code=500, detail="AI failed to generate story pages.")

        # 4. Update story title in DB if it changed from initial_title (e.g. AI generated it)
        if db_story.title != final_story_title:
            db_story.title = final_story_title
            db.commit()
            db.refresh(db_story)
            app_logger.info(
                f"Story ID {db_story.id} title finalized to '{final_story_title}'.")

        # 5. Process each page: generate DALL-E image (if applicable), save page to DB
        created_pages_schemas = []
        story_page_image_dir = os.path.join(  # Re-affirm story_image_root_dir for clarity
            "data", "images", f"user_{current_user.id}", f"story_{db_story.id}")

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
                    story_page_image_dir, image_filename)
                try:
                    api_logger.debug(
                        f"Generating image for story {db_story.id}, page {page_number} with prompt: {image_prompt}")
                    # generate_image_from_dalle returns a dict, but we only need the path here for now.
                    # The revised_prompt and gen_id for page images are not currently stored.
                    image_gen_result = await asyncio.to_thread(
                        ai_services.generate_image_from_dalle, image_prompt, image_save_path)
                    actual_image_path = image_gen_result["image_path"]
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
                                 headers={"Content-Disposition": f"attachment; filename={safe_title}.pdf"})
    except Exception as e:
        error_logger.error(
            f"Failed to generate PDF for story {story_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate PDF: {e}")
