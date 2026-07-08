"""add notifications table"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0003"
down_revision = "20260708_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )
    op.create_index(
        "ix_notifications_alert_id",
        "notifications",
        ["alert_id"],
        unique=False
    )
    op.create_index(
        "ix_notifications_transaction_id",
        "notifications",
        ["transaction_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_transaction_id",
        table_name="notifications"
    )
    op.drop_index(
        "ix_notifications_alert_id",
        table_name="notifications"
    )
    op.drop_table("notifications")
