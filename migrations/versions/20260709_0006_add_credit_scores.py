"""add credit scores table"""

from alembic import op
import sqlalchemy as sa


revision = "20260709_0006_credit_scores"
down_revision = "20260708_0005_training_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credit_score", sa.Float(), nullable=False),
        sa.Column("repayment_probability", sa.Float(), nullable=False),
        sa.Column("score_band", sa.String(), nullable=False),
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
        "ix_credit_scores_user_id",
        "credit_scores",
        ["user_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        "ix_credit_scores_user_id",
        table_name="credit_scores"
    )
    op.drop_table("credit_scores")
