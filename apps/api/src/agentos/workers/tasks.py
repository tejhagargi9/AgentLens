import asyncio
import uuid

from agentos.rag.ingest import ingest_source
from agentos.workers.celery_app import celery_app


@celery_app.task(name="ingest_source")
def ingest_source_task(source_id: str) -> None:
    """Chunk, embed and index an uploaded source. Used when AGENTOS_USE_CELERY is on."""
    asyncio.run(ingest_source(uuid.UUID(source_id)))
