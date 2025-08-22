from fastapi.testclient import TestClient
from backend import schemas


def test_backfill_characters_populates_library(client: TestClient, regular_user_auth_headers: dict):
    # Create a story with main characters
    story_in = {
        "title": "Backfill Test",
        "genre": "Sci-Fi",
        "story_outline": "A short outline",
        "main_characters": [
            {"name": "LibHero", "gender": "non-binary"},
            {"name": "Sidekick"}
        ],
        "num_pages": 1,
        "image_style": "Default",
        "word_to_picture_ratio": "One image per page",
        "text_density": "Concise (~30-50 words)"
    }
    res_story = client.post("/stories/drafts/", json=story_in,
                            headers=regular_user_auth_headers)
    assert res_story.status_code == 200

    # Call backfill endpoint
    res = client.post("/stories/backfill-characters",
                      json={"include_drafts": True},
                      headers=regular_user_auth_headers)
    assert res.status_code == 200
    assert "upserted" in res.json()

    # Now list characters and expect at least the two we provided
    res_list = client.get("/api/v1/characters/",
                          headers=regular_user_auth_headers)
    assert res_list.status_code == 200
    payload = res_list.json()
    names = {item["name"] for item in payload.get("items", [])}
    assert {"LibHero", "Sidekick"}.issubset(names)
