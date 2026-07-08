from __future__ import annotations

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
from sqlalchemy.sql import func


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:admin@localhost:5432/banking"
)

config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("+asyncpg", "")
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


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
