from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from datetime import datetime, UTC
from unittest.mock import patch


def test_export_pdf_success(client: TestClient, db_session, regular_user_auth_headers):
    # Arrange: create a story owned by the regular user
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="A Test Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch("backend.pdf_generator.create_story_pdf", return_value=b"%PDF-1.4\n..."):
        resp = client.get(f"/stories/{story.id}/pdf",
                          headers=regular_user_auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/pdf"
        cd = resp.headers.get("content-disposition", "")
        assert f"filename={story.title}.pdf" in cd


def test_export_pdf_unauthorized_for_other_user(client: TestClient, db_session, regular_user_auth_headers, admin_auth_headers):
    # Arrange: create a story owned by admin
    admin_user = db_session.query(database.User).filter_by(
        username="admin@example.com").first()
    story = database.Story(
        title="Admin Story",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=admin_user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    # Regular user should not access admin's story
    resp = client.get(f"/stories/{story.id}/pdf",
                      headers=regular_user_auth_headers)
    assert resp.status_code == 404


def test_export_pdf_filename_sanitization(client: TestClient, db_session, regular_user_auth_headers):
    user = db_session.query(database.User).filter_by(
        username="user@example.com").first()
    story = database.Story(
        title="A/Weird*Title?",
        genre="fantasy",
        story_outline="O",
        main_characters=[],
        num_pages=1,
        owner_id=user.id,
        is_draft=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)

    with patch("backend.pdf_generator.create_story_pdf", return_value=b"%PDF-1.4\n..."):
        resp = client.get(f"/stories/{story.id}/pdf",
                          headers=regular_user_auth_headers)
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        # Sanitized filename should not include illegal characters; fallback keeps alnum, space, -,_
        assert "AWeirdTitle.pdf" in cd or "story_" in cd
