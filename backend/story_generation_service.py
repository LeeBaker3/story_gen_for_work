import asyncio
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from . import crud, schemas, database, ai_services
from .settings import get_settings
from .storage_paths import character_ref_paths, page_image_paths, story_images_abs, story_images_rel
from .logging_config import app_logger, error_logger


async def generate_story_as_background_task(task_id: str, story_id: int, user_id: int, story_input: schemas.StoryCreate):
    db: Session = next(database.get_db())
    _settings = get_settings()
    try:
        app_logger.info(
            f"Starting background story generation for task_id: {task_id}")
        crud.update_story_generation_task(
            db,
            task_id,
            status=schemas.GenerationTaskStatus.IN_PROGRESS,
            current_step=schemas.GenerationTaskStep.INITIALIZING,
        )

        # Step 1: Generate Character Images and build a lookup map
        crud.update_story_generation_task_progress(
            db, task_id, 10, schemas.GenerationTaskStep.GENERATING_CHARACTER_IMAGES)

        # Ensure base story directory exists
        os.makedirs(story_images_abs(user_id, story_id), exist_ok=True)

        character_details_map = {}
        for character_input in story_input.main_characters:
            # Build file paths for saving each character reference via helper
            char_image_save_path_on_disk, char_image_path_for_db = character_ref_paths(
                user_id, story_id, character_input.name or "character"
            )

            # The service returns a dictionary of the (possibly updated) character's details
            char_details = await ai_services.generate_character_reference_image(
                character_input, story_input, db, user_id, story_id,
                image_save_path_on_disk=char_image_save_path_on_disk,
                image_path_for_db=char_image_path_for_db
            )
            if char_details and char_details.get('reference_image_path'):
                character_details_map[character_input.name] = char_details

        app_logger.info(
            f"Completed character image generation for task_id: {task_id}. Details: {character_details_map}")

        # Step 2: Generate Story Content
        crud.update_story_generation_task_progress(
            db, task_id, 30, schemas.GenerationTaskStep.GENERATING_TEXT)
        story_content_input = story_input.model_dump()
        # Pass the full character details map to the story generation prompt if needed
        story_content_input['main_characters'] = list(
            character_details_map.values())

        story_content = ai_services.generate_story_from_chatgpt(
            story_content_input)
        # Some tests may mock this as an async function; await if coroutine
        if asyncio.iscoroutine(story_content):
            story_content = await story_content
        app_logger.info(
            f"Completed story content generation for task_id: {task_id}")

        # Step 3: Generate Page Images
        crud.update_story_generation_task_progress(
            db, task_id, 60, schemas.GenerationTaskStep.GENERATING_PAGE_IMAGES)
        # Ensure base dir exists (already ensured above) for per-page images

        failed_pages = 0
        if 'Pages' in story_content:
            for i, page in enumerate(story_content['Pages']):
                progress = 60 + int((i + 1) / len(story_content['Pages']) * 35)
                crud.update_story_generation_task_progress(
                    db, task_id, progress, schemas.GenerationTaskStep.GENERATING_PAGE_IMAGES)

                # Determine which reference images to use for this page
                characters_in_scene = page.get('Characters_in_scene', [])
                reference_paths_for_page = []
                for char_name in characters_in_scene:
                    if char_name in character_details_map and character_details_map[char_name].get('reference_image_path'):
                        reference_paths_for_page.append(
                            character_details_map[char_name]['reference_image_path'])

                # Extract image style from Pydantic enum
                image_style = story_input.image_style
                if hasattr(image_style, 'value'):
                    image_style = image_style.value

                # Skip image generation if there's no image description (e.g., based on ratio rule)
                image_description = page.get('Image_description')
                if not image_description:
                    page['image_url'] = None
                    continue

                # Build a unique filename for this page image
                raw_page_num = page.get('Page_number', i + 1)
                try:
                    page_num_int = 0 if raw_page_num == "Title" else int(
                        raw_page_num)
                except Exception:
                    page_num_int = i + 1

                image_save_path_on_disk, image_path_for_db = page_image_paths(
                    user_id, story_id, page_num_int
                )

                # Retry page image generation with exponential backoff if it returns None
                attempts = max(1, getattr(_settings, 'retry_max_attempts', 3))
                backoff = max(0.1, float(
                    getattr(_settings, 'retry_backoff_base', 1.0)))
                page_image_url = None
                for attempt in range(attempts):
                    page_image_url = await ai_services.generate_image_for_page(
                        page_content=image_description,
                        style_reference=image_style,
                        characters_in_scene=characters_in_scene,
                        db=db,
                        user_id=user_id,
                        story_id=story_id,
                        page_number=page_num_int,
                        image_save_path_on_disk=image_save_path_on_disk,
                        image_path_for_db=image_path_for_db,
                        reference_image_paths=reference_paths_for_page,
                    )
                    if page_image_url:
                        break
                    # backoff before next attempt, unless last
                    if attempt < attempts - 1:
                        await asyncio.sleep(backoff * (2 ** attempt))
                page['image_url'] = page_image_url
                if not page_image_url:
                    failed_pages += 1

        app_logger.info(
            f"Completed page image generation for task_id: {task_id}")

        # Step 4: Save the story
        crud.update_story_generation_task_progress(
            db, task_id, 95, schemas.GenerationTaskStep.FINALIZING)
        crud.update_story_with_generated_content(db, story_id, story_content)
        app_logger.info(f"Saved story {story_id} to the database.")

        # Final Step: Update task status to COMPLETED (even if some images failed; text is generated)
        crud.update_story_generation_task(
            db,
            task_id,
            status=schemas.GenerationTaskStatus.COMPLETED,
            current_step=schemas.GenerationTaskStep.FINALIZING,
        )
        crud.update_story_generation_task_progress(
            db, task_id, 100, schemas.GenerationTaskStep.FINALIZING)
        if failed_pages:
            # Store a brief summary in error_message without marking as FAILED
            crud.update_story_generation_task(
                db,
                task_id,
                error_message=f"Completed with {failed_pages} page image(s) missing due to generation failures."
            )
        app_logger.info(
            f"Successfully completed story generation for task_id: {task_id}")

    except Exception as e:
        error_logger.error(
            f"Error during background story generation for task_id {task_id}: {e}", exc_info=True)
        crud.update_story_generation_task(
            db,
            task_id,
            status=schemas.GenerationTaskStatus.FAILED,
            error_message=str(e),
            current_step=schemas.GenerationTaskStep.FINALIZING,
        )
    finally:
        db.close()
