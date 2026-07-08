"""create core tables"""

from alembic import op
import sqlalchemy as sa


revision = "20260708_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=False),
        sa.Column("device_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )
    op.create_index(
        "ix_transactions_id",
        "transactions",
        ["id"],
        unique=False
    )

    op.create_table(
        "fraud_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column("fraud_score", sa.Float(), nullable=True),
        sa.Column("fraud_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_table("fraud_alerts")
    op.drop_index("ix_transactions_id", table_name="transactions")
    op.drop_table("transactions")
