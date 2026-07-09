"""add notification delivery fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0007_notif_delivery"
down_revision = "20260709_0006_credit_scores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0"
        )
    )
    op.add_column(
        "notifications",
        sa.Column(
            "last_error",
            sa.Text(),
            nullable=True
        )
    )
    op.add_column(
        "notifications",
        sa.Column(
            "provider_message_id",
            sa.String(),
            nullable=True
        )
    )
    op.add_column(
        "notifications",
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column(
        "notifications",
        "delivered_at"
    )
    op.drop_column(
        "notifications",
        "provider_message_id"
    )
    op.drop_column(
        "notifications",
        "last_error"
    )
    op.drop_column(
        "notifications",
        "attempts"
    )
