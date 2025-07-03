import asyncio
from sqlalchemy.orm import Session
from . import crud, schemas, database, ai_services
from .logging_config import app_logger, error_logger
import uuid
from datetime import datetime


async def generate_story_as_background_task(task_id: str, story_id: int, user_id: int, story_input: schemas.StoryCreate):
    db: Session = next(database.get_db())
    try:
        app_logger.info(
            f"Starting background story generation for task_id: {task_id}")
        crud.update_story_generation_task_status(
            db, task_id, schemas.GenerationTaskStatus.IN_PROGRESS, "Starting story generation...")

        # Step 1: Generate Character Images
        crud.update_story_generation_task_progress(
            db, task_id, 10, "Generating character images...")

        generated_character_details = []
        for character_input in story_input.main_characters:
            character_image_url = await ai_services.generate_character_reference_image(
                character_input, story_input, db, user_id, story_id
            )
            if character_image_url:
                generated_character_details.append({
                    "name": character_input.name,
                    "image_url": character_image_url
                })

        app_logger.info(
            f"Completed character image generation for task_id: {task_id}")

        # Step 2: Generate Story Content
        crud.update_story_generation_task_progress(
            db, task_id, 30, "Generating story content...")
        story_content_input = story_input.model_dump()
        story_content_input['generated_character_details'] = generated_character_details

        story_content = await ai_services.generate_story_from_chatgpt(story_content_input)
        app_logger.info(
            f"Completed story content generation for task_id: {task_id}")

        # Step 3: Generate Page Images
        crud.update_story_generation_task_progress(
            db, task_id, 60, "Generating page images...")
        if 'Pages' in story_content:
            for i, page in enumerate(story_content['Pages']):
                progress = 60 + int((i + 1) / len(story_content['Pages']) * 35)
                crud.update_story_generation_task_progress(
                    db, task_id, progress, f"Generating image for page {i+1}...")

                page_image_url = await ai_services.generate_image_for_page(
                    page_content=page['Text'],
                    style_reference=story_input.artstyle,
                    db=db,
                    user_id=user_id,
                    story_id=story_id,
                    page_number=i+1
                )
                page['image_url'] = page_image_url

        app_logger.info(
            f"Completed page image generation for task_id: {task_id}")

        # Step 4: Save the story
        crud.update_story_generation_task_progress(
            db, task_id, 95, "Saving story...")
        crud.update_story_with_generated_content(db, story_id, story_content)
        app_logger.info(f"Saved story {story_id} to the database.")

        # Final Step: Update task status to COMPLETED
        crud.update_story_generation_task_status(
            db, task_id, schemas.GenerationTaskStatus.COMPLETED, "Story generated successfully.")
        crud.update_story_generation_task_progress(
            db, task_id, 100, "Completed")
        app_logger.info(
            f"Successfully completed story generation for task_id: {task_id}")

    except Exception as e:
        error_logger.error(
            f"Error during background story generation for task_id {task_id}: {e}", exc_info=True)
        crud.update_story_generation_task_status(
            db, task_id, schemas.GenerationTaskStatus.FAILED, str(e))
    finally:
        db.close()
