from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Integer
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Table
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.sql import func


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/banking"
)
connectable_database_url = database_url

if connectable_database_url.startswith(
    "postgresql://"
):
    connectable_database_url = connectable_database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1
    )

config.set_main_option(
    "sqlalchemy.url",
    connectable_database_url
)

target_metadata = MetaData()

Table(
    "transactions",
    target_metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("user_id", Integer, nullable=False),
    Column("amount", Float, nullable=False),
    Column("currency", String, default="USD"),
    Column("country", String, nullable=False),
    Column("device_type", String, nullable=False),
    Column("status", String, default="PENDING"),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "fraud_alerts",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("transaction_id", Integer),
    Column("fraud_score", Float),
    Column("fraud_probability", Float, nullable=False),
    Column("risk_level", String),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "model_predictions",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("transaction_id", Integer, nullable=False, index=True),
    Column("fraud_probability", Float, nullable=False),
    Column("risk_level", String, nullable=False),
    Column("model_source", String, nullable=False),
    Column("features_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "training_logs",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("experiment_name", String, nullable=False),
    Column("model_name", String, nullable=False, index=True),
    Column("model_version", Integer, nullable=True),
    Column("run_id", String, nullable=True, index=True),
    Column("accuracy", Float, nullable=True),
    Column("parameters_json", Text, nullable=False),
    Column("metrics_json", Text, nullable=False),
    Column("status", String, nullable=False),
    Column("error_message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "credit_scores",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False, index=True),
    Column("credit_score", Float, nullable=False),
    Column("repayment_probability", Float, nullable=False),
    Column("score_band", String, nullable=False),
    Column("model_source", String, nullable=False),
    Column("features_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "outbox_events",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("transaction_id", Integer, nullable=False),
    Column("topic", String, nullable=False),
    Column("payload", Text, nullable=False),
    Column("status", String, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("last_error", Text, nullable=True),
    Column("processed_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)

Table(
    "notifications",
    target_metadata,
    Column("id", Integer, primary_key=True),
    Column("alert_id", Integer, nullable=False, index=True),
    Column("transaction_id", Integer, nullable=False, index=True),
    Column("channel", String, nullable=False),
    Column("recipient", String, nullable=False),
    Column("message", String, nullable=False),
    Column("status", String, nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("last_error", Text, nullable=True),
    Column("provider_message_id", String, nullable=True),
    Column("delivered_at", DateTime(timezone=True), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now())
)


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable_url = config.get_main_option(
        "sqlalchemy.url"
    )

    if connectable_url.startswith(
        "postgresql+asyncpg://"
    ):
        asyncio.run(run_async_migrations_online())
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


async def run_async_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        await connection.run_sync(configure_and_run_migrations)

    await connectable.dispose()


def configure_and_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
