import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import SessionLocal, DynamicList, DynamicListItem
from backend.logging_config import app_logger


def is_database_empty(db: Session) -> bool:
    """
    Checks if the dynamic_lists table is empty.
    """
    return db.query(DynamicList).first() is None


def seed_database(db: Session = None):
    """
    Executes the SQL script to seed the database with initial dynamic list data.
    If a session is provided, it uses it. Otherwise, it creates a new session.
    """
    if db:
        _run_seeding_logic(db)
    else:
        # If no session is passed, create one and ensure it's closed
        session = SessionLocal()
        try:
            _run_seeding_logic(session)
        finally:
            session.close()


def _seed_defaults_programmatically(db: Session):
    """Fallback seeding using ORM to avoid path/dialect issues in tests.

    Inserts a minimal, sensible default set for the lists used across the app/tests.
    Uses upserts by checking existence first to remain idempotent.
    """
    try:
        # Ensure parent lists exist
        lists = {
            "genres": "Story Genres",
            "image_styles": "Image Styles",
            "writing_styles": "Writing Styles",
            "word_to_picture_ratio": "Word to Picture Ratio",
            "text_density": "Text Density",
            "genders": "Genders",
        }
        for name, label in lists.items():
            if not db.query(DynamicList).filter_by(list_name=name).first():
                db.add(DynamicList(list_name=name, list_label=label))

        # Seed items (only if not present)
        def ensure_item(list_name: str, value: str, label: str, sort: int):
            exists = db.query(DynamicListItem).filter_by(
                list_name=list_name, item_value=value
            ).first()
            if not exists:
                db.add(DynamicListItem(
                    list_name=list_name,
                    item_value=value,
                    item_label=label,
                    is_active=True,
                    sort_order=sort,
                    additional_config=None,
                ))

        genres = [
            "Children's", "Sci-Fi", "Drama", "Horror", "Action",
            "Fantasy", "Mystery", "Romance", "Thriller", "Comedy",
        ]
        for i, g in enumerate(genres, start=1):
            ensure_item("genres", g, g if g !=
                        "Children's" else "Children’s", i)

        image_styles = [
            "Default", "Cartoon", "Watercolor", "Photorealistic",
            "Pixel Art", "Fantasy Art", "Sci-Fi Concept Art", "Anime",
            "Vintage Comic Book Art", "Minimalist", "Noir",
        ]
        for i, s in enumerate(image_styles, start=1):
            ensure_item("image_styles", s, s, i)

        # Minimal other lists
        ratios = [
            "One image per page",
            "One image per two pages",
            "One image per paragraph",
        ]
        for i, r in enumerate(ratios, start=1):
            ensure_item("word_to_picture_ratio", r, r, i)

        densities = [
            "Concise (~30-50 words)",
            "Standard (~60-90 words)",
            "Detailed (~100-150 words)",
        ]
        for i, d in enumerate(densities, start=1):
            ensure_item("text_density", d, d, i)

        genders = ["Female", "Male", "Non-binary",
                   "Other", "Prefer not to say"]
        for i, g in enumerate(genders, start=1):
            ensure_item("genders", g, g, i)

        db.commit()
        app_logger.info("Programmatic fallback seeding completed.")
    except Exception as e:
        app_logger.error(
            f"Programmatic fallback seeding failed: {e}", exc_info=True)
        db.rollback()


def _run_seeding_logic(db: Session):
    """
    Contains the actual logic for seeding the database.
    """
    try:
        if not is_database_empty(db):
            app_logger.info(
                "Database already contains data in dynamic_lists. Skipping seeding.")
            return

        # Always seed a safe baseline programmatically first (idempotent)
        app_logger.info(
            "Seeding baseline dynamic lists/items programmatically...")
        _seed_defaults_programmatically(db)

        # Optionally apply the SQL script to add/align any additional items
        seed_script_path = os.path.join(os.path.dirname(
            __file__), '..', 'scripts', 'seed_dynamic_lists.sql')
        if os.path.exists(seed_script_path):
            app_logger.info(
                f"Applying SQL seed script for completeness: {seed_script_path}...")
            with open(seed_script_path, 'r') as f:
                # Split commands by semicolon and filter out empty ones
                sql_commands = [cmd.strip()
                                for cmd in f.read().split(';') if cmd.strip()]
                for command in sql_commands:
                    db.execute(text(command))
            db.commit()
            app_logger.info("SQL seed script applied.")
        else:
            app_logger.warning(
                f"Seed script not found at {seed_script_path}. Skipping script application.")

    except Exception as e:
        app_logger.error(
            f"An error occurred during database seeding: {e}", exc_info=True)
        db.rollback()
