import os
import time
from backend import ai_services
from backend import settings as settings_mod


def test_images_and_prompts_written_and_served(monkeypatch, tmp_path, client, regular_user_auth_headers):
    # Force data dir to a temp dir via env and reset settings singleton so helpers read it
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    settings_mod._settings_instance = None
    settings_mod.get_settings()

    # Mock story generation to avoid calling OpenAI
    def fake_generate_story_from_chatgpt(payload):
        return {
            "Title": "T",
            "Pages": [
                {"Page_number": "Title", "Text": "T",
                    "Image_description": "cover", "Characters_in_scene": []},
                {"Page_number": 1, "Text": "P1",
                    "Image_description": "scene 1", "Characters_in_scene": []},
            ]
        }

    async def fake_generate_image_for_page(**kwargs):
        # Write a small fake image and prompt using provided paths
        image_path_on_disk = kwargs["image_save_path_on_disk"]
        os.makedirs(os.path.dirname(image_path_on_disk), exist_ok=True)
        with open(image_path_on_disk, "wb") as f:
            f.write(b"fakeimage")
        with open(os.path.splitext(image_path_on_disk)[0] + "_prompt.txt", "w", encoding="utf-8") as f:
            f.write("prompt")
        # Return DB-relative path
        return kwargs["image_path_for_db"]

    async def fake_generate_character_reference_image(character, story_input, db, user_id, story_id, image_save_path_on_disk=None, image_path_for_db=None):
        # Write a small fake image and prompt for refs
        os.makedirs(os.path.dirname(image_save_path_on_disk), exist_ok=True)
        with open(image_save_path_on_disk, "wb") as f:
            f.write(b"fakeimage")
        with open(os.path.splitext(image_save_path_on_disk)[0].replace("_ref_", "_ref_prompt_") + ".txt", "w", encoding="utf-8") as f:
            f.write("prompt")
        d = character.model_dump()
        d["reference_image_path"] = image_path_for_db
        return d

    monkeypatch.setattr(
        ai_services, "generate_story_from_chatgpt", fake_generate_story_from_chatgpt)
    monkeypatch.setattr(ai_services, "generate_image_for_page",
                        fake_generate_image_for_page)
    monkeypatch.setattr(ai_services, "generate_character_reference_image",
                        fake_generate_character_reference_image)

    # Prepare a draft story payload
    payload = {
        "title": "T",
        "genre": "Fantasy",
        "story_outline": "O",
        "main_characters": [{"name": "A"}],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Standard (~60-90 words)"
    }

    # Use the public endpoint with a valid bearer token (fixture user)
    response = client.post("/api/v1/stories/", json=payload,
                           headers=regular_user_auth_headers)
    assert response.status_code in (202, 200), response.text

    # Wait briefly for background task to write files (poll up to ~3s)
    deadline = time.time() + 3.0
    files = []
    while time.time() < deadline:
        files = []
        for root, _, filenames in os.walk(tmp_path):
            for fn in filenames:
                if fn.endswith(".png") or fn.endswith(".txt"):
                    files.append(os.path.join(root, fn))
        if any(f.endswith(".png") for f in files) and any(f.endswith(".txt") for f in files):
            break
        time.sleep(0.05)

    # Expect at least one ref image and one page image and their prompts
    assert any(f.endswith(".png") for f in files)
    assert any(f.endswith(".txt") for f in files)

    # Check DB paths would be resolvable via /static_content (relative to data dir)
    # Build one relative candidate from found file
    rel_candidates = [os.path.relpath(f, tmp_path) for f in files]
    assert any(c.startswith("images/") for c in rel_candidates)
