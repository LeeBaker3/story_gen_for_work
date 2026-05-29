"""add stripe billing tables

Revision ID: 20260518_01
Revises:
Create Date: 2026-05-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260518_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account_entitlements",
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
    )
    op.add_column(
        "account_entitlements",
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
    )
    op.add_column(
        "account_entitlements",
        sa.Column("current_period_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "account_entitlements",
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "usage_ledger_entries",
        sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_account_entitlements_stripe_customer_id"),
        "account_entitlements",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_entitlements_stripe_subscription_id"),
        "account_entitlements",
        ["stripe_subscription_id"],
        unique=False,
    )
    op.create_table(
        "processed_stripe_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_processed_stripe_events_event_id"),
        "processed_stripe_events",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_processed_stripe_events_id"),
        "processed_stripe_events",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_processed_stripe_events_id"),
        table_name="processed_stripe_events",
    )
    op.drop_index(
        op.f("ix_processed_stripe_events_event_id"),
        table_name="processed_stripe_events",
    )
    op.drop_table("processed_stripe_events")
    op.drop_index(
        op.f("ix_account_entitlements_stripe_subscription_id"),
        table_name="account_entitlements",
    )
    op.drop_index(
        op.f("ix_account_entitlements_stripe_customer_id"),
        table_name="account_entitlements",
    )
    op.drop_column("usage_ledger_entries", "billing_period_start")
    op.drop_column("account_entitlements", "cancel_at_period_end")
    op.drop_column("account_entitlements", "current_period_started_at")
    op.drop_column("account_entitlements", "stripe_subscription_id")
    op.drop_column("account_entitlements", "stripe_customer_id")