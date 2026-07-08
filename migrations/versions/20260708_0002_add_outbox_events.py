"""add outbox events"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0002_outbox_events"
down_revision = "20260708_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )
    op.create_index(
        "ix_outbox_events_transaction_id",
        "outbox_events",
        ["transaction_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_events_transaction_id",
        table_name="outbox_events"
    )
    op.drop_table("outbox_events")
