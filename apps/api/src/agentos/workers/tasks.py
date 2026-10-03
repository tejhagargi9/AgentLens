from agentos.workers.celery_app import celery_app


@celery_app.task(name="ingest_repository")
def ingest_repository(repository_id: str) -> None:
    """Clone, chunk, embed and index a repository into Qdrant."""
    raise NotImplementedError
