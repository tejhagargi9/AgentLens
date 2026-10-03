from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import Connection, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.schema import CreateColumn

from agentos.core.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> AsyncEngine:
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session."""
    async with get_sessionmaker()() as session:
        yield session


def _add_missing_columns(connection: Connection) -> None:
    """Add columns that models gained after a table was first created.

    Covers additive changes only (new nullable or defaulted columns), which keeps existing
    local databases working. Anything else needs a real migration tool.
    """
    inspector = inspect(connection)
    for table in Base.metadata.sorted_tables:
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing:
                continue
            ddl = CreateColumn(column).compile(dialect=connection.dialect)
            connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}"))
            if (table.name, column.name) == ("sources", "status"):
                connection.execute(
                    text("UPDATE sources SET status = 'ready' WHERE kind = 'github'")
                )


async def create_tables() -> None:
    """Create missing tables and columns. Stands in for migrations until the schema settles."""
    from agentos.db import models  # noqa: F401  (registers the models on Base.metadata)

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_add_missing_columns)
