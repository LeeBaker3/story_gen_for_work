import asyncio
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from . import crud, schemas, database, ai_services
from .logging_config import app_logger, error_logger


async def generate_story_as_background_task(task_id: str, story_id: int, user_id: int, story_input: schemas.StoryCreate):
    db: Session = next(database.get_db())
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

        # Prepare base paths for saving assets for this story
        user_images_base_path_for_db = f"images/user_{user_id}"
        story_folder_name_for_db = f"story_{story_id}"

        # Character reference images go under .../references
        char_ref_image_subfolder_name = "references"
        char_ref_image_path_base_for_db = os.path.join(
            user_images_base_path_for_db, story_folder_name_for_db, char_ref_image_subfolder_name
        )
        char_ref_image_dir_on_disk = os.path.join(
            "data", char_ref_image_path_base_for_db)
        os.makedirs(char_ref_image_dir_on_disk, exist_ok=True)

        character_details_map = {}
        for character_input in story_input.main_characters:
            # Build file paths for saving each character reference
            safe_char_name = character_input.name.replace(
                ' ', '_') if character_input.name else f"char_{uuid.uuid4().hex[:8]}"
            char_image_filename = f"{safe_char_name}_ref_story_{story_id}.png"
            char_image_save_path_on_disk = os.path.join(
                char_ref_image_dir_on_disk, char_image_filename
            )
            char_image_path_for_db = os.path.join(
                char_ref_image_path_base_for_db, char_image_filename
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
        # Prepare base paths for per-page images
        story_page_image_path_for_db_base = os.path.join(
            user_images_base_path_for_db, story_folder_name_for_db
        )
        story_page_image_dir_on_disk = os.path.join(
            "data", story_page_image_path_for_db_base)
        os.makedirs(story_page_image_dir_on_disk, exist_ok=True)

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

                image_filename_prefix = "cover" if page_num_int == 0 else f"page_{page_num_int}"
                unique_suffix = uuid.uuid4().hex[:8]
                image_filename = f"{image_filename_prefix}_{unique_suffix}_story_{story_id}_p{page_num_int}.png"
                image_save_path_on_disk = os.path.join(
                    story_page_image_dir_on_disk, image_filename
                )
                image_path_for_db = os.path.join(
                    story_page_image_path_for_db_base, image_filename
                )

                page_image_url = await ai_services.generate_image_for_page(
                    # Use the detailed Image_description from the AI output
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
                page['image_url'] = page_image_url

        app_logger.info(
            f"Completed page image generation for task_id: {task_id}")

        # Step 4: Save the story
        crud.update_story_generation_task_progress(
            db, task_id, 95, schemas.GenerationTaskStep.FINALIZING)
        crud.update_story_with_generated_content(db, story_id, story_content)
        app_logger.info(f"Saved story {story_id} to the database.")

        # Final Step: Update task status to COMPLETED
        crud.update_story_generation_task(
            db,
            task_id,
            status=schemas.GenerationTaskStatus.COMPLETED,
            current_step=schemas.GenerationTaskStep.FINALIZING,
        )
        crud.update_story_generation_task_progress(
            db, task_id, 100, schemas.GenerationTaskStep.FINALIZING)
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
