"""Seed a temporary SQLite database for browser-level E2E tests."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def parse_args() -> argparse.Namespace:
    """Return validated CLI arguments for the E2E seed command."""

    parser = argparse.ArgumentParser(
        description="Seed the temporary E2E database with deterministic data.",
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--private-data-dir", required=True)
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> None:
    """Populate the process environment before importing backend modules."""

    os.environ["DATABASE_URL"] = args.database_url
    os.environ["DATA_DIR"] = args.data_dir
    os.environ["PRIVATE_DATA_DIR"] = args.private_data_dir
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("RUN_ENV", "test")
    os.environ.setdefault("MOUNT_FRONTEND_STATIC", "true")
    os.environ.setdefault("MOUNT_DATA_STATIC", "true")
    os.environ.setdefault("ENABLE_IMAGE_GENERATION", "false")
    os.environ.setdefault("SECRET_KEY", "e2e-secret-key")


def seed_database_state(args: argparse.Namespace) -> None:
    """Create the database schema and insert deterministic E2E records."""

    from backend import auth, database_seeding
    from backend.database import Page, SessionLocal, Story, User, create_db_and_tables

    create_db_and_tables()

    session = SessionLocal()
    try:
        database_seeding.seed_database(session)

        hashed_password = auth.get_password_hash("Passw0rd!")

        admin_user = User(
            username="e2e-admin@example.com",
            email="e2e-admin@example.com",
            hashed_password=hashed_password,
            is_active=True,
            role="admin",
        )
        regular_user = User(
            username="e2e-user@example.com",
            email="e2e-user@example.com",
            hashed_password=hashed_password,
            is_active=True,
            role="user",
        )
        session.add_all([admin_user, regular_user])
        session.flush()

        story = Story(
            title="The Clockwork Forest",
            story_outline=(
                "Mira follows a trail of brass fireflies through a forest of "
                "clockwork trees to find a hidden observatory."
            ),
            genre="Fantasy",
            main_characters=[{"name": "Mira"}],
            num_pages=2,
            tone="Hopeful",
            setting="A forest filled with ticking trees",
            writing_style="Whimsical",
            image_style="Default",
            word_to_picture_ratio="One image per page",
            text_density="Concise (~30-50 words)",
            owner_id=regular_user.id,
            is_draft=False,
            generated_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
            editor_settings={
                "page_format": "square-storybook",
                "layout_mode": "vertical-split",
                "text_position": "bottom-center",
                "font_family": "storybook",
                "font_size": 28,
                "font_color": "#ffffff",
                "text_box_opacity": 0.6,
            },
        )
        session.add(story)
        session.flush()

        session.add_all(
            [
                Page(
                    story_id=story.id,
                    page_number=0,
                    text="The Clockwork Forest",
                    image_description="Cover art showing Mira and brass fireflies.",
                    image_path=None,
                ),
                Page(
                    story_id=story.id,
                    page_number=1,
                    text=(
                        "Mira followed the brass fireflies until the trees "
                        "opened around a hidden observatory."
                    ),
                    image_description="Mira reaches the observatory clearing.",
                    image_path=None,
                ),
            ]
        )

        session.commit()
    finally:
        session.close()


def ensure_directories(args: argparse.Namespace) -> None:
    """Create the storage directories required by the seeded app."""

    Path(args.data_dir).mkdir(parents=True, exist_ok=True)
    Path(args.private_data_dir).mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Seed the E2E app database and storage directories."""

    args = parse_args()
    configure_environment(args)
    ensure_directories(args)
    seed_database_state(args)


if __name__ == "__main__":
    main()