"""add model predictions table"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0002"
down_revision = "20260708_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("model_source", sa.String(), nullable=False),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )
    op.create_index(
        "ix_model_predictions_transaction_id",
        "model_predictions",
        ["transaction_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        "ix_model_predictions_transaction_id",
        table_name="model_predictions"
    )
    op.drop_table("model_predictions")
