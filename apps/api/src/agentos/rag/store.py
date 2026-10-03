"""Qdrant storage and hybrid search. Blocking; call from a worker thread."""

import threading
import uuid
from functools import lru_cache
from pathlib import Path

from qdrant_client import QdrantClient, models

from agentos.core.config import get_settings
from agentos.rag import embeddings
from agentos.rag.chunking import Chunk

_DENSE = "dense"
_SPARSE = "bm25"
_BATCH = 64
# Embedded Qdrant is not thread-safe, and indexing runs alongside searches.
_lock = threading.Lock()


@lru_cache
def _client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    if settings.qdrant_path == ":memory:":
        return QdrantClient(location=":memory:")
    Path(settings.qdrant_path).mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=settings.qdrant_path)


def _collection() -> str:
    name = get_settings().qdrant_collection
    client = _client()
    if not client.collection_exists(name):
        client.create_collection(
            name,
            vectors_config={
                _DENSE: models.VectorParams(
                    size=embeddings.dense_size(), distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                _SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        if get_settings().qdrant_url:  # payload indexes only exist on a real server
            for field in ("user_id", "source_id"):
                client.create_payload_index(name, field, models.PayloadSchemaType.KEYWORD)
    return name


def _match(key: str, value: str) -> models.FieldCondition:
    return models.FieldCondition(key=key, match=models.MatchValue(value=value))


def index_chunks(
    user_id: str, source_id: str, source_name: str, kind: str, chunks: list[Chunk]
) -> None:
    """Embed and store chunks, replacing anything already indexed for this source."""
    delete_source(source_id)
    for start in range(0, len(chunks), _BATCH):
        batch = chunks[start : start + _BATCH]
        # The path is embedded with the text so "where is X" questions can match file names.
        texts = [f"{chunk.path}\n{chunk.text}" if chunk.path else chunk.text for chunk in batch]
        dense = embeddings.embed_dense(texts)
        sparse = embeddings.embed_sparse(texts)
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector={
                    _DENSE: dense[i],
                    _SPARSE: models.SparseVector(indices=sparse[i][0], values=sparse[i][1]),
                },
                payload={
                    "user_id": user_id,
                    "source_id": source_id,
                    "source_name": source_name,
                    "kind": kind,
                    "path": chunk.path,
                    "language": chunk.language,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "page": chunk.page,
                    "text": chunk.text,
                },
            )
            for i, chunk in enumerate(batch)
        ]
        with _lock:
            _client().upsert(_collection(), points)


def delete_source(source_id: str) -> None:
    with _lock:
        name = get_settings().qdrant_collection
        if _client().collection_exists(name):
            _client().delete(
                name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[_match("source_id", source_id)])
                ),
            )


def hybrid_search(user_id: str, query: str, limit: int) -> list[dict]:
    """Dense + BM25 search over one user's chunks, fused with Reciprocal Rank Fusion.

    Returns payload dicts, each with an added "point_id".
    """
    owned = models.Filter(must=[_match("user_id", user_id)])
    dense = embeddings.embed_dense_query(query)
    sparse_indices, sparse_values = embeddings.embed_sparse_query(query)
    with _lock:
        name = get_settings().qdrant_collection
        if not _client().collection_exists(name):
            return []
        response = _client().query_points(
            name,
            prefetch=[
                models.Prefetch(query=dense, using=_DENSE, limit=limit, filter=owned),
                models.Prefetch(
                    query=models.SparseVector(indices=sparse_indices, values=sparse_values),
                    using=_SPARSE,
                    limit=limit,
                    filter=owned,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
    return [{**point.payload, "point_id": str(point.id)} for point in response.points]
