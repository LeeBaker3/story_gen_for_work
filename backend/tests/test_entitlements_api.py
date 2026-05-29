from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend import auth
from backend.database import AccountEntitlement, Page, Story, User
from backend.settings import get_settings


def _auth_headers_for(username: str) -> dict[str, str]:
    token = auth.create_access_token(data={"sub": username})
    return {"Authorization": f"Bearer {token}"}


def test_signup_provisions_trial_and_reads_entitlement(
    client: TestClient,
    db_session: Session,
):
    response = client.post(
        "/api/v1/users/",
        json={
            "username": "trial-user@example.com",
            "email": "trial-user@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200, response.text
    created_user = response.json()

    entitlement = (
        db_session.query(AccountEntitlement)
        .filter(AccountEntitlement.user_id == created_user["id"])
        .first()
    )
    assert entitlement is not None

    entitlement_response = client.get(
        "/api/v1/users/me/entitlement",
        headers=_auth_headers_for("trial-user@example.com"),
    )

    assert entitlement_response.status_code == 200, entitlement_response.text
    payload = entitlement_response.json()
    settings = get_settings()
    assert payload["access_state"] == "trial"
    assert payload["active_entitlement"] is True
    assert payload["story_credits"]["total"] == settings.trial_story_credits
    assert payload["story_credits"]["remaining"] == settings.trial_story_credits
    assert payload["image_credits"]["total"] == settings.trial_image_credits
    assert payload["image_credits"]["remaining"] == settings.trial_image_credits
    assert payload["trial_expires_at"] is not None


def test_story_generation_blocked_before_background_task_when_story_credits_exhausted(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    user = db_session.query(User).filter(User.username == "user@example.com").first()
    assert user is not None

    db_session.add(
        AccountEntitlement(
            user_id=user.id,
            access_state="trial",
            story_credits_total=0,
            image_credits_total=3,
        )
    )
    db_session.commit()

    with patch(
        "backend.public_router.story_generation_service.generate_story_as_background_task"
    ) as mock_background_task:
        response = client.post(
            "/api/v1/stories/",
            headers=regular_user_auth_headers,
            json={
                "title": "Blocked story",
                "genre": "Fantasy",
                "story_outline": "Should fail before generation starts.",
                "main_characters": [],
                "num_pages": 1,
                "image_style": "Default",
            },
        )

    assert response.status_code == 402, response.text
    assert response.json()["detail"]["code"] == "quota_exhausted"
    assert response.json()["detail"]["credit_bucket"] == "story"
    mock_background_task.assert_not_called()


def test_page_image_regeneration_blocked_before_provider_call_when_image_credits_exhausted(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(User.username == "user@example.com").first()
    assert owner is not None

    db_session.add(
        AccountEntitlement(
            user_id=owner.id,
            access_state="trial",
            story_credits_total=3,
            image_credits_total=0,
        )
    )

    story = Story(
        title="Image Locked",
        story_outline="A story to edit.",
        genre="Fantasy",
        main_characters=[],
        num_pages=1,
        owner_id=owner.id,
        is_draft=False,
        image_style="Default",
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    page = Page(
        story_id=story.id,
        page_number=1,
        text="A dragon by the sea",
        image_description="Dragon scene",
        image_path="images/user_1/story_1/page1.png",
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)

    with patch(
        "backend.public_router.ai_services.generate_image_for_page",
        new_callable=AsyncMock,
    ) as mock_generate:
        response = client.post(
            f"/api/v1/stories/{story.id}/pages/{page.id}/regenerate-image",
            headers=regular_user_auth_headers,
        )

    assert response.status_code == 402, response.text
    assert response.json()["detail"]["code"] == "quota_exhausted"
    assert response.json()["detail"]["credit_bucket"] == "image"
    mock_generate.assert_not_awaited()


def test_character_regeneration_blocked_before_provider_call_when_image_credits_exhausted(
    client: TestClient,
    db_session: Session,
    regular_user_auth_headers: dict,
):
    owner = db_session.query(User).filter(User.username == "user@example.com").first()
    assert owner is not None

    db_session.add(
        AccountEntitlement(
            user_id=owner.id,
            access_state="trial",
            story_credits_total=3,
            image_credits_total=0,
        )
    )
    db_session.commit()

    create_response = client.post(
        "/api/v1/characters/",
        json={"name": "Quota Character", "generate_image": False},
        headers=regular_user_auth_headers,
    )
    assert create_response.status_code == 201, create_response.text
    char_id = create_response.json()["id"]

    with patch("backend.ai_services.generate_image") as mock_generate:
        response = client.post(
            f"/api/v1/characters/{char_id}/regenerate-image",
            json={"description": "new look"},
            headers=regular_user_auth_headers,
        )

    assert response.status_code == 402, response.text
    assert response.json()["detail"]["code"] == "quota_exhausted"
    assert response.json()["detail"]["credit_bucket"] == "image"
    mock_generate.assert_not_called()