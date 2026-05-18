import asyncio
from typing import Generator
from datetime import UTC, datetime

from backend import ai_services, crud, database, story_generation_service, story_worker


def test_run_single_worker_iteration_completes_pending_task(
    db_session,
    monkeypatch,
):
    """The single worker should claim and complete one queued task."""

    owner = db_session.query(database.User).filter(
        database.User.username == "user@example.com"
    ).first()
    assert owner is not None

    story = database.Story(
        title="Queued Story",
        story_outline="A queued outline.",
        genre="Fantasy",
        main_characters=[{"name": "Ava"}],
        num_pages=1,
        image_style="Default",
        word_to_picture_ratio="One image per page",
        text_density="Concise (~30-50 words)",
        owner_id=owner.id,
        is_draft=False,
        editor_settings={
            "font_family": "storybook",
            "font_size": 28,
            "font_color": "#ffffff",
            "text_position": "bottom-center",
            "text_box_opacity": 0.6,
            "page_format": "letter",
            "layout_mode": "full-page-overlay",
        },
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    task = crud.create_story_generation_task(db_session, story.id, owner.id)
    assert task is not None

    async def fake_generate_character_reference_image(
        character_input,
        story_input,
        db,
        user_id,
        story_id,
        image_save_path_on_disk,
        image_path_for_db,
    ):
        return {
            **character_input.model_dump(exclude_none=True),
            "reference_image_path": image_path_for_db,
        }

    def fake_generate_story_from_chatgpt(story_input):
        return {
            "Title": "Queued Story Complete",
            "Main_characters": [
                {
                    "name": "Ava",
                    "reference_image_path": (
                        "images/user_2/story_1/characters/ava.png"
                    ),
                }
            ],
            "Pages": [
                {
                    "Page_number": 1,
                    "Text": "Ava solves the queued task.",
                    "Image_description": "Ava in a bright workshop.",
                    "Characters_in_scene": ["Ava"],
                }
            ],
        }

    async def fake_generate_image_for_page(
        page_content,
        style_reference,
        db,
        user_id,
        story_id,
        page_number,
        image_save_path_on_disk,
        image_path_for_db,
        **kwargs,
    ):
        return image_path_for_db

    monkeypatch.setattr(
        story_worker,
        "SessionLocal",
        lambda: db_session,
    )

    def override_background_db() -> Generator:
        yield db_session

    monkeypatch.setattr(
        story_generation_service.database,
        "get_db",
        override_background_db,
    )
    monkeypatch.setattr(
        ai_services,
        "generate_character_reference_image",
        fake_generate_character_reference_image,
    )
    monkeypatch.setattr(
        ai_services,
        "generate_story_from_chatgpt",
        fake_generate_story_from_chatgpt,
    )
    monkeypatch.setattr(
        ai_services,
        "generate_image_for_page",
        fake_generate_image_for_page,
    )

    processed = asyncio.run(story_worker.run_single_worker_iteration())

    assert processed is True
    refreshed_task = db_session.query(database.StoryGenerationTask).filter(
        database.StoryGenerationTask.id == task.id,
    ).one()
    refreshed_story = db_session.query(database.Story).filter(
        database.Story.id == story.id,
    ).one()
    assert refreshed_task.status == "completed"
    assert refreshed_task.progress == 100
    assert refreshed_story.title == "Queued Story Complete"
    assert len(refreshed_story.pages) == 1
    assert refreshed_story.pages[0].text == "Ava solves the queued task."