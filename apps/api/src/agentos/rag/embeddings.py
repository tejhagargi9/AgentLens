"""Local embedding and reranking models (fastembed, ONNX on CPU).

Models are downloaded to AGENTOS_MODEL_CACHE_DIR on first use and loaded once per process.
All functions here are blocking; call them from a worker thread.
"""

from functools import lru_cache
from pathlib import Path

from fastembed import SparseTextEmbedding, TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder

from agentos.core.config import get_settings

SparseVector = tuple[list[int], list[float]]


def _cache_dir() -> str:
    path = Path(get_settings().model_cache_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


@lru_cache
def _dense_model() -> TextEmbedding:
    return TextEmbedding(get_settings().embedding_model, cache_dir=_cache_dir())


@lru_cache
def _sparse_model() -> SparseTextEmbedding:
    return SparseTextEmbedding(get_settings().sparse_model, cache_dir=_cache_dir())


@lru_cache
def _reranker() -> TextCrossEncoder:
    return TextCrossEncoder(get_settings().reranker_model, cache_dir=_cache_dir())


@lru_cache
def dense_size() -> int:
    return len(embed_dense(["dimension probe"])[0])


def embed_dense(texts: list[str]) -> list[list[float]]:
    return [vector.tolist() for vector in _dense_model().embed(texts)]


def embed_dense_query(text: str) -> list[float]:
    return next(iter(_dense_model().query_embed(text))).tolist()


def embed_sparse(texts: list[str]) -> list[SparseVector]:
    """BM25 term weights for documents (IDF is applied by Qdrant at query time)."""
    return [(e.indices.tolist(), e.values.tolist()) for e in _sparse_model().embed(texts)]


def embed_sparse_query(text: str) -> SparseVector:
    embedding = next(iter(_sparse_model().query_embed(text)))
    return embedding.indices.tolist(), embedding.values.tolist()


def rerank(query: str, texts: list[str]) -> list[float]:
    """Cross-encoder relevance score for each text against the query (higher is better)."""
    return list(_reranker().rerank(query, texts))
