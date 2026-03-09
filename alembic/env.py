"""Alembic migration environment — async SQLAlchemy configuration.

Supports async PostgreSQL via asyncpg driver.
All ORM models are imported here so Alembic can detect schema changes
with --autogenerate.

Usage:
    alembic upgrade head          # Apply all pending migrations
    alembic downgrade -1          # Roll back last migration
    alembic revision --autogenerate -m "add column foo"
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# ── Import all ORM models so Alembic sees them ──────────────
# These imports are necessary for autogenerate to detect tables.
from shared.utils.database import Base  # noqa: F401
import services.customer.infrastructure.orm_models  # noqa: F401
import services.billing.infrastructure.orm_models  # noqa: F401

# ── Alembic Config ──────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Build async database URL from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "telco")
    password = os.getenv("POSTGRES_PASSWORD", "telco_secret")
    db = os.getenv("POSTGRES_DB", "telcoagent")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed).

    Generates SQL script instead of executing directly.
    Useful for reviewing changes before applying.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    """Execute migrations using an existing connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        # Create schemas like 'customer', 'billing' if they don't exist
        include_object=lambda obj, name, type_, reflected, compare_to: True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations asynchronously using asyncpg."""
    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,  # Single connection for migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the database)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
