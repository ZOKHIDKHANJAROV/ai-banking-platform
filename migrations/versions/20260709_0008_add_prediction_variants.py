"""add prediction variant audit fields"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0008_pred_variants"
down_revision = "20260709_0007_notif_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "model_predictions",
        sa.Column(
            "model_name",
            sa.String(),
            nullable=False,
            server_default="FraudDetectionModel"
        )
    )
    op.add_column(
        "model_predictions",
        sa.Column(
            "model_version",
            sa.String(),
            nullable=True
        )
    )
    op.add_column(
        "model_predictions",
        sa.Column(
            "model_role",
            sa.String(),
            nullable=False,
            server_default="CHAMPION"
        )
    )
    op.add_column(
        "model_predictions",
        sa.Column(
            "is_live_decision",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true()
        )
    )


def downgrade() -> None:
    op.drop_column(
        "model_predictions",
        "is_live_decision"
    )
    op.drop_column(
        "model_predictions",
        "model_role"
    )
    op.drop_column(
        "model_predictions",
        "model_version"
    )
    op.drop_column(
        "model_predictions",
        "model_name"
    )
