"""add reservation id to story generation tasks

Revision ID: 20260518_02
Revises: 20260518_01
Create Date: 2026-05-18 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260518_02"
down_revision = "20260518_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "story_generation_tasks",
        sa.Column("reservation_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_story_generation_tasks_reservation_id"),
        "story_generation_tasks",
        ["reservation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_story_generation_tasks_reservation_id"),
        table_name="story_generation_tasks",
    )
    op.drop_column("story_generation_tasks", "reservation_id")