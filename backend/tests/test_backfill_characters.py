from fastapi.testclient import TestClient
from backend import crud, schemas
from backend.database import User
from backend.settings import get_settings
import os


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
    res = client.post("/api/v1/stories/backfill-characters",
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


def test_backfill_character_thumbnails_repairs_only_current_users_characters(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
):
    create_res = client.post(
        "/api/v1/characters/",
        json={"name": "EndpointThumb", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    character = create_res.json()

    user = db_session.query(User).filter(User.username == "user@example.com").one()
    source_rel_path = (
        f"images/user_{user.id}/story_777/references/endpoint-thumb.png"
    )
    source_abs_path = os.path.join(get_settings().data_dir, source_rel_path)
    os.makedirs(os.path.dirname(source_abs_path), exist_ok=True)
    with open(source_abs_path, "wb") as source_file:
        source_file.write(b"endpoint repair thumbnail")

    crud.add_character_image(
        db_session,
        user.id,
        character["id"],
        source_rel_path,
        prompt_used=None,
        image_style=None,
    )

    res = client.post(
        "/api/v1/characters/backfill-thumbnails",
        headers=regular_user_auth_headers,
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload == {
        "scanned": 1,
        "repaired": 1,
        "already_public": 0,
        "missing_source": 0,
        "no_private_source": 0,
        "copy_failed": 0,
        "skipped": 0,
    }
