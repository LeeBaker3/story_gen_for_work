import asyncio
import os
import uuid
from datetime import datetime
import time
from sqlalchemy.orm import Session
from . import crud, schemas, database, ai_services
from .settings import get_settings
from .storage_paths import character_ref_paths, page_image_paths, story_images_abs, story_images_rel
from .logging_config import app_logger, error_logger
from .metrics import PAGE_IMAGE_RETRIES_TOTAL, observe_story_generation


async def generate_story_as_background_task(task_id: str, story_id: int, user_id: int, story_input: schemas.StoryCreate):
    db: Session = next(database.get_db())
    _settings = get_settings()
    start_time = time.perf_counter()
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

        # Upsert generated/merged character details into user's library for reuse
        try:
            upserted = 0
            for _, ch in character_details_map.items():
                try:
                    crud.upsert_character_from_detail(db, user_id, ch)
                    upserted += 1
                except Exception as e:
                    error_logger.error(
                        f"Upsert of character '{ch.get('name')}' failed during background task {task_id}: {e}")
            app_logger.info(
                f"Upserted {upserted} character(s) into user {user_id}'s library during background generation.")
        except Exception as e:
            error_logger.error(
                f"Bulk upsert of characters during background generation failed for task {task_id}: {e}")

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
                    if attempt > 0:
                        PAGE_IMAGE_RETRIES_TOTAL.inc()
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
                        # Record a retry cycle at the task level (increment attempts)
                        crud.update_story_generation_task(
                            db,
                            task_id,
                            status=schemas.GenerationTaskStatus.IN_PROGRESS,
                            error_message=f"Retrying page {page_num_int} image generation (attempt {attempt + 2}/{attempts})",
                        )
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

        # Upsert characters from the generated content into the user's library
        try:
            chars = story_content.get('Main_characters') or story_content.get(
                'main_characters') or []
            upserted = 0
            for ch in chars:
                try:
                    # Normalize keys to expected names
                    char_detail = {
                        'name': ch.get('name') or ch.get('Name'),
                        'description': ch.get('description') or ch.get('Description'),
                        'age': ch.get('age') or ch.get('Age'),
                        'gender': ch.get('gender') or ch.get('Gender'),
                        'clothing_style': ch.get('clothing_style') or ch.get('Clothing_style'),
                        'key_traits': ch.get('key_traits') or ch.get('Key_traits'),
                        'image_style': ch.get('image_style') or ch.get('Image_style'),
                        'reference_image_path': ch.get('reference_image_path') or ch.get('Reference_image_path'),
                    }
                    crud.upsert_character_from_detail(db, user_id, char_detail)
                    upserted += 1
                except Exception as e:
                    error_logger.error(
                        f"Character upsert failure during background task for story {story_id}: {e}")
            app_logger.info(
                f"Upserted {upserted} character(s) into user {user_id}'s library from generated story {story_id}.")
        except Exception as e:
            error_logger.error(
                f"Failed bulk upsert of characters for story {story_id}: {e}")

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

        observe_story_generation(
            status="completed",
            duration_seconds=time.perf_counter() - start_time,
        )

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

        observe_story_generation(
            status="failed",
            duration_seconds=time.perf_counter() - start_time,
        )
    finally:
        db.close()
