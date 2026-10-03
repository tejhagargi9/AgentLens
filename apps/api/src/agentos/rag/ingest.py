"""Indexing pipeline for uploaded sources: load -> chunk -> embed -> store in Qdrant."""

import asyncio
import logging
import uuid
from pathlib import Path

from sqlalchemy import select

from agentos.core.config import get_settings
from agentos.db.models import Source
from agentos.db.session import get_sessionmaker
from agentos.rag import store
from agentos.rag.chunking import chunk_source

logger = logging.getLogger(__name__)

# Keeps in-process indexing tasks alive until they finish (asyncio only holds weak references).
_tasks: set[asyncio.Task] = set()


def _index(source: Source) -> int:
    chunks = chunk_source(source.kind, Path(source.storage_path))
    if not chunks:
        raise ValueError("No readable text was found in this file")
    store.index_chunks(str(source.user_id), str(source.id), source.name, source.kind, chunks)
    return len(chunks)


async def ingest_source(source_id: uuid.UUID) -> None:
    """Index one uploaded source and record the outcome on its row."""
    async with get_sessionmaker()() as session:
        source = await session.get(Source, source_id)
        if source is None or source.kind == "github":
            return
        source.status, source.error = "indexing", None
        await session.commit()

    try:
        status, error, chunk_count = "ready", None, await asyncio.to_thread(_index, source)
    except Exception as exc:
        logger.exception("Indexing failed for source %s", source_id)
        status, error, chunk_count = "failed", str(exc)[:500], None

    async with get_sessionmaker()() as session:
        source = await session.get(Source, source_id)
        if source is None:  # deleted while it was being indexed
            await asyncio.to_thread(store.delete_source, str(source_id))
            return
        source.status, source.error, source.chunk_count = status, error, chunk_count
        await session.commit()


def schedule_ingestion(source_id: uuid.UUID) -> None:
    """Queue indexing: on a Celery worker if enabled, otherwise in this process."""
    if get_settings().use_celery:
        from agentos.workers.tasks import ingest_source_task

        ingest_source_task.delay(str(source_id))
        return
    task = asyncio.get_running_loop().create_task(ingest_source(source_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def resume_unfinished() -> None:
    """Re-queue uploads left pending or mid-index, e.g. after a restart."""
    async with get_sessionmaker()() as session:
        unfinished = await session.scalars(
            select(Source.id).where(
                Source.kind != "github", Source.status.in_(["pending", "indexing"])
            )
        )
        for source_id in unfinished:
            schedule_ingestion(source_id)
