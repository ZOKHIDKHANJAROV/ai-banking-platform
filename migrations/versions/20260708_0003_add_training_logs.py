"""add training logs table"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0005_training_logs"
down_revision = "20260708_0004_model_predictions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("experiment_name", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_version", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("parameters_json", sa.Text(), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )
    op.create_index(
        "ix_training_logs_model_name",
        "training_logs",
        ["model_name"],
        unique=False
    )
    op.create_index(
        "ix_training_logs_run_id",
        "training_logs",
        ["run_id"],
        unique=False
    )


def downgrade() -> None:
    op.drop_index(
        "ix_training_logs_run_id",
        table_name="training_logs"
    )
    op.drop_index(
        "ix_training_logs_model_name",
        table_name="training_logs"
    )
    op.drop_table("training_logs")
