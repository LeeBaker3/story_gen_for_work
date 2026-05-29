"""One-off repair script for public character thumbnails."""

import argparse

from backend import crud
from backend.database import SessionLocal


def main() -> int:
    """Run character thumbnail backfill for a single user."""

    parser = argparse.ArgumentParser(
        description="Backfill public character thumbnails for one user.",
    )
    parser.add_argument("user_id", type=int, help="User ID to repair.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        counts = crud.backfill_public_character_thumbnails(db, args.user_id)
    finally:
        db.close()

    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
