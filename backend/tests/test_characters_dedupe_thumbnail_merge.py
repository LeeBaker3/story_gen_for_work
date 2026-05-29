import os
import uuid
from datetime import UTC, datetime

from backend.settings import get_settings
from backend import crud
from backend.database import User
from backend import schemas
from backend.database import Story
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


def test_listing_prefers_public_character_thumbnail_over_private_story_asset(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
    monkeypatch,
):
    def _fake_generate_image(prompt, style, size):
        return b"\x89PNG\r\n\x1a\nPUBLIC"

    monkeypatch.setattr(
        "backend.ai_services.generate_image", _fake_generate_image)

    create_res = client.post(
        "/api/v1/characters/",
        json={"name": "FallbackThumb", "generate_image": True},
        headers=regular_user_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    character = create_res.json()
    public_path = character["current_image"]["file_path"]

    user = db_session.query(User).filter(
        User.username == "user@example.com").one()
    blocked_path = f"images/user_{user.id}/story_99/references/fallback.png"
    crud.add_character_image(
        db_session,
        user.id,
        character["id"],
        blocked_path,
        prompt_used=None,
        image_style=None,
    )

    res_list = client.get(
        "/api/v1/characters?page=1&page_size=50",
        headers=regular_user_auth_headers,
    )
    assert res_list.status_code == 200, res_list.text
    items = res_list.json()["items"]
    thumb_item = next(
        (item for item in items if item["id"] == character["id"]), None)
    assert thumb_item is not None
    assert thumb_item["thumbnail_path"] == public_path


def test_listing_omits_thumbnail_when_only_private_story_asset_exists(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
):
    create_res = client.post(
        "/api/v1/characters/",
        json={"name": "PrivateOnly", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    character = create_res.json()

    user = db_session.query(User).filter(
        User.username == "user@example.com").one()
    crud.add_character_image(
        db_session,
        user.id,
        character["id"],
        f"images/user_{user.id}/story_123/references/private-only.png",
        prompt_used=None,
        image_style=None,
    )

    res_list = client.get(
        "/api/v1/characters?page=1&page_size=50",
        headers=regular_user_auth_headers,
    )
    assert res_list.status_code == 200, res_list.text
    items = res_list.json()["items"]
    thumb_item = next(
        (item for item in items if item["id"] == character["id"]), None)
    assert thumb_item is not None
    assert thumb_item["thumbnail_path"] is None


def test_backfill_thumbnails_repairs_public_thumbnail_from_story_asset(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
):
    create_res = client.post(
        "/api/v1/characters/",
        json={"name": "StoryAssetOnly", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    character = create_res.json()

    user = db_session.query(User).filter(
        User.username == "user@example.com").one()
    source_rel_path = (
        f"images/user_{user.id}/story_321/references/story-asset-only.png"
    )
    source_abs_path = os.path.join(get_settings().data_dir, source_rel_path)
    os.makedirs(os.path.dirname(source_abs_path), exist_ok=True)
    with open(source_abs_path, "wb") as source_file:
        source_file.write(b"story asset thumbnail")

    crud.add_character_image(
        db_session,
        user.id,
        character["id"],
        source_rel_path,
        prompt_used=None,
        image_style=None,
    )

    res_list = client.get(
        "/api/v1/characters?page=1&page_size=50",
        headers=regular_user_auth_headers,
    )
    assert res_list.status_code == 200, res_list.text
    items = res_list.json()["items"]
    thumb_item = next(
        (item for item in items if item["id"] == character["id"]), None)
    assert thumb_item is not None
    assert thumb_item["thumbnail_path"] is None

    res_backfill = client.post(
        "/api/v1/characters/backfill-thumbnails",
        headers=regular_user_auth_headers,
    )
    assert res_backfill.status_code == 200, res_backfill.text
    payload = res_backfill.json()
    assert payload["scanned"] >= 1
    assert payload["repaired"] == 1
    assert payload["already_public"] == 0

    refreshed_list = client.get(
        "/api/v1/characters?page=1&page_size=50",
        headers=regular_user_auth_headers,
    )
    assert refreshed_list.status_code == 200, refreshed_list.text
    refreshed_items = refreshed_list.json()["items"]
    thumb_item = next(
        (item for item in refreshed_items if item["id"] == character["id"]), None)
    assert thumb_item is not None
    thumbnail_path = thumb_item["thumbnail_path"]
    assert thumbnail_path is not None
    assert thumbnail_path != source_rel_path
    assert thumbnail_path.startswith(
        f"images/user_{user.id}/characters/{character['id']}/"
    )

    materialized_abs_path = os.path.join(
        get_settings().data_dir, thumbnail_path)
    assert os.path.exists(materialized_abs_path)
    with open(materialized_abs_path, "rb") as materialized_file:
        assert materialized_file.read() == b"story asset thumbnail"

    repaired_character = crud.get_character(
        db_session, user.id, character["id"])
    assert repaired_character is not None
    assert repaired_character.current_image is not None
    assert repaired_character.current_image.file_path == thumbnail_path
    assert any(image.file_path ==
               source_rel_path for image in repaired_character.images)
    assert any(image.file_path ==
               thumbnail_path for image in repaired_character.images)


def test_listing_leaves_thumbnail_null_when_story_asset_source_is_missing(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
):
    create_res = client.post(
        "/api/v1/characters/",
        json={"name": "MissingStoryAsset", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    character = create_res.json()

    user = db_session.query(User).filter(
        User.username == "user@example.com").one()
    missing_source_rel_path = (
        f"images/user_{user.id}/story_654/references/missing-story-asset.png"
    )
    crud.add_character_image(
        db_session,
        user.id,
        character["id"],
        missing_source_rel_path,
        prompt_used=None,
        image_style=None,
    )

    res_list = client.get(
        "/api/v1/characters?page=1&page_size=50",
        headers=regular_user_auth_headers,
    )
    assert res_list.status_code == 200, res_list.text
    items = res_list.json()["items"]
    thumb_item = next(
        (item for item in items if item["id"] == character["id"]), None)
    assert thumb_item is not None
    assert thumb_item["thumbnail_path"] is None

    res_backfill = client.post(
        "/api/v1/characters/backfill-thumbnails",
        headers=regular_user_auth_headers,
    )
    assert res_backfill.status_code == 200, res_backfill.text
    payload = res_backfill.json()
    assert payload["repaired"] == 0
    assert payload["missing_source"] == 1

    repaired_character = crud.get_character(
        db_session, user.id, character["id"])
    assert repaired_character is not None
    assert repaired_character.current_image is not None
    assert repaired_character.current_image.file_path == missing_source_rel_path
    assert len(repaired_character.images) == 1


def test_story_creation_merge_avoids_duplicate_names(
    client: TestClient,
    db_session,
    regular_user_auth_headers: dict,
    monkeypatch,
):
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

    task_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    monkeypatch.setattr(
        "backend.crud.create_story_generation_task",
        lambda db, story_id, user_id, reservation_id=None: schemas.StoryGenerationTask(
            id=task_id,
            story_id=story_id,
            user_id=user_id,
            status=schemas.GenerationTaskStatus.PENDING,
            created_at=now,
            updated_at=now,
        ),
    )
    monkeypatch.setattr(
        "backend.public_router.story_generation_service"
        ".generate_story_as_background_task",
        lambda *args, **kwargs: None,
    )

    res_story = client.post(
        "/api/v1/stories/",
        json=story_in,
        headers=regular_user_auth_headers,
    )
    assert res_story.status_code == 202, res_story.text

    story_id = res_story.json()["story_id"]
    db_story = db_session.query(Story).filter(Story.id == story_id).one()
    names = [c["name"] for c in db_story.main_characters]
    assert names.count("MergeStar") == 1
    assert "NewChar" in names
