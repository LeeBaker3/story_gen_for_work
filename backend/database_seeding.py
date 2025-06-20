import os
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.database import SessionLocal, DynamicList
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


def _run_seeding_logic(db: Session):
    """
    Contains the actual logic for seeding the database.
    """
    try:
        if not is_database_empty(db):
            app_logger.info(
                "Database already contains data in dynamic_lists. Skipping seeding.")
            return

        seed_script_path = os.path.join(os.path.dirname(
            __file__), '..', 'scripts', 'seed_dynamic_lists.sql')

        if not os.path.exists(seed_script_path):
            app_logger.error(
                f"Seed script not found at {seed_script_path}. Cannot seed database.")
            return

        app_logger.info(
            f"Database appears to be empty. Seeding data from {seed_script_path}...")
        with open(seed_script_path, 'r') as f:
            # Split commands by semicolon and filter out empty ones
            sql_commands = [cmd.strip()
                            for cmd in f.read().split(';') if cmd.strip()]
            for command in sql_commands:
                db.execute(text(command))
        db.commit()
        app_logger.info("Database successfully seeded with dynamic lists.")

    except Exception as e:
        app_logger.error(
            f"An error occurred during database seeding: {e}", exc_info=True)
        db.rollback()
