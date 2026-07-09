import asyncio
import os
import sys

import pytest
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


EXPECTED_HEAD = "20260709_0008_pred_variants"
EXPECTED_TABLE_COLUMNS = {
    "transactions": {
        "id",
        "user_id",
        "amount",
        "currency",
        "country",
        "device_type",
        "status",
        "created_at",
    },
    "fraud_alerts": {
        "id",
        "transaction_id",
        "fraud_score",
        "fraud_probability",
        "risk_level",
        "created_at",
    },
    "outbox_events": {
        "id",
        "transaction_id",
        "topic",
        "payload",
        "status",
        "attempts",
        "last_error",
        "processed_at",
        "created_at",
    },
    "notifications": {
        "id",
        "alert_id",
        "transaction_id",
        "channel",
        "recipient",
        "message",
        "status",
        "attempts",
        "last_error",
        "provider_message_id",
        "delivered_at",
        "created_at",
    },
    "model_predictions": {
        "id",
        "transaction_id",
        "fraud_probability",
        "risk_level",
        "model_name",
        "model_version",
        "model_role",
        "is_live_decision",
        "model_source",
        "features_json",
        "created_at",
    },
    "training_logs": {
        "id",
        "experiment_name",
        "model_name",
        "model_version",
        "run_id",
        "accuracy",
        "parameters_json",
        "metrics_json",
        "status",
        "error_message",
        "created_at",
    },
    "credit_scores": {
        "id",
        "user_id",
        "credit_score",
        "repayment_probability",
        "score_band",
        "model_source",
        "features_json",
        "created_at",
    },
}


def get_postgres_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url.startswith("postgresql"):
        pytest.skip("Postgres DATABASE_URL is required for migration schema checks")

    if sys.platform.startswith("win"):
        pytest.skip("Postgres schema smoke runs in Linux CI; Windows asyncpg loopback is flaky")

    return database_url


@pytest.mark.asyncio
async def test_alembic_upgrade_produces_expected_schema():
    engine = create_async_engine(
        get_postgres_database_url()
    )

    try:
        last_error = None

        for _ in range(5):
            try:
                async with engine.connect() as connection:
                    version_num = await connection.scalar(
                        text("SELECT version_num FROM alembic_version")
                    )

                    assert version_num == EXPECTED_HEAD

                    def inspect_schema(sync_connection):
                        schema_inspector = inspect(
                            sync_connection
                        )
                        discovered = {}

                        for table_name in EXPECTED_TABLE_COLUMNS:
                            discovered[table_name] = {
                                column["name"]
                                for column in schema_inspector.get_columns(table_name)
                            }

                        return discovered

                    discovered_columns = await connection.run_sync(
                        inspect_schema
                    )
                break
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.5)
        else:
            raise last_error
        for table_name, expected_columns in EXPECTED_TABLE_COLUMNS.items():
            assert table_name in discovered_columns
            assert expected_columns.issubset(
                discovered_columns[table_name]
            )
    finally:
        await engine.dispose()
