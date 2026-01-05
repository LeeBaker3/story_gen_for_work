import os

from backend.settings import get_settings
from fastapi.testclient import TestClient


def test_create_character_dedupes_by_name(client: TestClient, regular_user_auth_headers: dict):
    # Create initial character
    payload1 = {"name": "DupHero", "description": "v1", "age": 10}
    res1 = client.post("/api/v1/characters/", json=payload1,
                       headers=regular_user_auth_headers)
    assert res1.status_code == 201, res1.text
    ch1 = res1.json()
    # Create again with same name but different fields
    payload2 = {"name": "dupHERO", "description": "v2",
                "age": 11, "clothing_style": "cape"}
    res2 = client.post("/api/v1/characters/", json=payload2,
                       headers=regular_user_auth_headers)
    assert res2.status_code == 201, res2.text
    ch2 = res2.json()
    # Should refer to same id and reflect updated fields
    assert ch2["id"] == ch1["id"]
    assert ch2["description"] == "v2"
    assert ch2["age"] == 11
    assert ch2["clothing_style"] == "cape"


def test_listing_includes_thumbnail_path_when_current_image_exists(client: TestClient, regular_user_auth_headers: dict, monkeypatch):
    # Mock generate_image to produce bytes to create an image file
    def _fake_generate_image(prompt, style, size):
        return b"\x89PNG\r\n\x1a\nTHUMB"

    monkeypatch.setattr(
        "backend.ai_services.generate_image", _fake_generate_image)

    # Create character with image
    res = client.post(
        "/api/v1/characters/",
        json={"name": "ThumbHero", "generate_image": True},
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 201, res.text

    # List characters; verify thumbnail_path present for this item
    res_list = client.get(
        "/api/v1/characters?page=1&page_size=50", headers=regular_user_auth_headers)
    assert res_list.status_code == 200
    data = res_list.json()
    items = data.get("items", [])
    # find ThumbHero
    thumb_item = next((i for i in items if i["name"] == "ThumbHero"), None)
    assert thumb_item is not None
    assert thumb_item.get("thumbnail_path") is not None
    # File should exist on disk relative to configured DATA_DIR.
    data_dir = get_settings().data_dir
    assert os.path.exists(os.path.join(data_dir, thumb_item["thumbnail_path"]))


def test_story_creation_merge_avoids_duplicate_names(client: TestClient, regular_user_auth_headers: dict, monkeypatch):
    # Create a saved character
    res_char = client.post(
        "/api/v1/characters/",
        json={"name": "MergeStar", "description": "library",
              "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert res_char.status_code == 201
    ch = res_char.json()

    # Prepare story input with a main_characters entry of same name and include character_ids referencing the saved character
    story_in = {
        "title": "Merge Test",
        "genre": "Fantasy",
        "story_outline": "Outline",
        "main_characters": [
            {"name": "MergeStar", "description": "from form"},
            {"name": "NewChar"}
        ],
        "character_ids": [ch["id"]],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)"
    }

    # Mock story generation function to avoid OpenAI
    monkeypatch.setattr(
        "backend.ai_services.generate_story_from_chatgpt",
        lambda story_input: {"Title": "Merge Test Final", "Pages": []}
    )

    res_story = client.post(
        "/stories/", json={"story_input": story_in}, headers=regular_user_auth_headers)
    assert res_story.status_code in (200, 201), res_story.text
    data = res_story.json()
    names = [c["name"] for c in data.get("main_characters", [])]
    # Should contain MergeStar only once and include NewChar
    assert names.count("MergeStar") == 1
    assert "NewChar" in names
