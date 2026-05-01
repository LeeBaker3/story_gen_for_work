from typing import Generator

from backend import ai_services, database, story_generation_service


def test_story_generation_full_loop_completes_and_exports_pdf(
    client,
    db_session,
    regular_user_auth_headers,
    monkeypatch,
):
    """Exercise the public story loop from task creation through PDF export."""

    def override_background_db() -> Generator:
        yield db_session

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
            "Title": "Loop Adventure",
            "Main_characters": [
                {
                    "name": "Ava",
                    "description": "A brave explorer.",
                    "reference_image_path": (
                        "images/user_2/story_1/characters/ava.png"
                    ),
                }
            ],
            "Pages": [
                {
                    "Page_number": "Title",
                    "Text": "Loop Adventure",
                    "Image_description": "A bright cover with Ava.",
                    "Characters_in_scene": ["Ava"],
                },
                {
                    "Page_number": 1,
                    "Text": "Ava finds the hidden lantern.",
                    "Image_description": "Ava in a glowing forest.",
                    "Characters_in_scene": ["Ava"],
                },
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

    def fake_create_story_pdf(story):
        assert story.id is not None
        assert story.title == "Loop Adventure"
        assert len(story.pages) == 2
        return b"%PDF-1.4\n% loop test pdf\n"

    monkeypatch.setattr(story_generation_service.database, "get_db", override_background_db)
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
    monkeypatch.setattr(
        "backend.pdf_generator.create_story_pdf",
        fake_create_story_pdf,
    )

    response = client.post(
        "/api/v1/stories/",
        headers=regular_user_auth_headers,
        json={
            "title": "Loop Request",
            "genre": "Fantasy",
            "story_outline": "Ava searches for a lantern.",
            "main_characters": [{"name": "Ava"}],
            "num_pages": 2,
            "image_style": "Default",
            "word_to_picture_ratio": "One image per page",
            "text_density": "Concise (~30-50 words)",
            "editor_settings": {
                "page_format": "square-storybook",
                "text_position": "top-center",
                "font_family": "classic",
                "font_size": 30,
                "font_color": "#123456",
                "text_box_opacity": 0.4,
            },
        },
    )

    assert response.status_code == 202
    task = response.json()
    assert task["status"] == "pending"
    assert task["story_id"] is not None

    status_response = client.get(
        f"/api/v1/stories/generation-status/{task['id']}",
        headers=regular_user_auth_headers,
    )
    assert status_response.status_code == 200
    completed_task = status_response.json()
    assert completed_task["status"] == "completed"
    assert completed_task["progress"] == 100
    assert completed_task["story_id"] == task["story_id"]
    assert completed_task["started_at"] is not None
    assert completed_task["completed_at"] is not None

    story_response = client.get(
        f"/api/v1/stories/{task['story_id']}",
        headers=regular_user_auth_headers,
    )
    assert story_response.status_code == 200
    story = story_response.json()
    assert story["title"] == "Loop Adventure"
    assert story["generated_at"] is not None
    assert story["editor_settings"] == {
        "font_family": "classic",
        "font_size": 30,
        "font_color": "#123456",
        "text_position": "top-center",
        "text_box_opacity": 0.4,
        "page_format": "square-storybook",
    }
    assert [page["page_number"] for page in story["pages"]] == [0, 1]
    assert story["pages"][1]["text"] == "Ava finds the hidden lantern."
    assert story["pages"][1]["image_path"].startswith("images/user_2/story_") and story["pages"][1]["image_path"].endswith("p1.png")

    pdf_response = client.get(
        f"/api/v1/stories/{task['story_id']}/pdf",
        headers=regular_user_auth_headers,
    )
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert (
        pdf_response.headers["content-disposition"]
        == "attachment; filename=Loop Adventure.pdf"
    )
    assert pdf_response.content == b"%PDF-1.4\n% loop test pdf\n"

    db_task = db_session.query(database.StoryGenerationTask).filter_by(
        id=task["id"]
    ).one()
    assert db_task.status == "completed"
    assert db_task.story_id == task["story_id"]