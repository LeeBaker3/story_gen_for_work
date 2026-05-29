"""add worker heartbeats table

Revision ID: 20260520_01
Revises: 20260518_02
Create Date: 2026-05-20 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260520_01"
down_revision = "20260518_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("runtime_id", sa.String(), nullable=False),
        sa.Column("runtime_role", sa.String(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint("runtime_id"),
    )
    op.create_index(
        op.f("ix_worker_heartbeats_runtime_id"),
        "worker_heartbeats",
        ["runtime_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_worker_heartbeats_runtime_role"),
        "worker_heartbeats",
        ["runtime_role"],
        unique=False,
    )
    op.create_index(
        op.f("ix_worker_heartbeats_last_heartbeat_at"),
        "worker_heartbeats",
        ["last_heartbeat_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_worker_heartbeats_last_heartbeat_at"),
        table_name="worker_heartbeats",
    )
    op.drop_index(
        op.f("ix_worker_heartbeats_runtime_role"),
        table_name="worker_heartbeats",
    )
    op.drop_index(
        op.f("ix_worker_heartbeats_runtime_id"),
        table_name="worker_heartbeats",
    )
    op.drop_table("worker_heartbeats")