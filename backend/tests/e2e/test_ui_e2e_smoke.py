"""Minimal browser-level smoke tests for the Story Generator UI."""

from __future__ import annotations

import json
import os

import pytest
from playwright.sync_api import Page, expect


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("RUN_UI_E2E") != "true",
        reason="UI E2E tests run only when explicitly enabled.",
    ),
]


REGULAR_USERNAME = "e2e-user@example.com"
ADMIN_USERNAME = "e2e-admin@example.com"
PASSWORD = "Passw0rd!"
SEEDED_STORY_TITLE = "The Clockwork Forest"
SEEDED_STORY_LINE = (
    "Mira followed the brass fireflies until the trees opened around a hidden observatory."
)


def open_index(page: Page, app_base_url: str) -> None:
    """Navigate to the real frontend served by the FastAPI app."""

    page.add_init_script(
        script=(
            "window.STORY_GENERATOR_CONFIG = "
            f"{{ apiBaseUrl: {json.dumps(app_base_url)} }};"
        )
    )
    page.goto(f"{app_base_url}/static/index.html", wait_until="networkidle")


def login(page: Page, username: str, password: str) -> None:
    """Authenticate through the real login form."""

    login_form = page.locator("#login-form")
    login_form.locator("#login-username").fill(username)
    login_form.locator("#login-password").fill(password)
    login_form.get_by_role("button", name="Login").click()


def test_app_boots_to_existing_frontend(page: Page, app_base_url: str) -> None:
    """The mounted frontend should load from the real FastAPI server."""

    open_index(page, app_base_url)

    expect(page).to_have_title("Story Generator")
    expect(page.get_by_role("heading", name="Story Generator")).to_be_visible()
    expect(page.get_by_role("button", name="Login / Sign Up")).to_be_visible()


def test_regular_user_can_open_seeded_story_from_library(
    page: Page,
    app_base_url: str,
) -> None:
    """A regular user can log in and open the seeded completed story."""

    open_index(page, app_base_url)
    login(page, REGULAR_USERNAME, PASSWORD)

    expect(page.get_by_role("button", name="My Stories")).to_be_visible()
    page.get_by_role("button", name="My Stories").click()

    story_item = page.locator("#user-stories-list .story-item").filter(
        has=page.get_by_role("heading", name=SEEDED_STORY_TITLE)
    )
    expect(story_item).to_have_count(1)
    story_item.get_by_role("button", name="View Story").click()

    expect(page.get_by_role("heading", name="Story Preview")).to_be_visible()
    expect(page.locator("#story-preview-content")).to_contain_text(SEEDED_STORY_TITLE)
    expect(page.locator("#story-preview-content")).to_contain_text(SEEDED_STORY_LINE)


def test_admin_user_can_reach_admin_panel(page: Page, app_base_url: str) -> None:
    """An admin can log in and load the existing admin page."""

    open_index(page, app_base_url)
    login(page, ADMIN_USERNAME, PASSWORD)

    admin_link = page.get_by_role("link", name="Admin Panel")
    expect(admin_link).to_be_visible()
    admin_link.click()

    expect(page).to_have_url(f"{app_base_url}/static/admin.html")
    expect(page.get_by_role("heading", name="Admin Panel")).to_be_visible()
    expect(page.locator("#admin-sidebar")).to_contain_text("User Management")