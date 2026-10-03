import os
import re
import tempfile
import uuid
import zlib
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

# Point the app at throwaway storage before it is imported.
_tmp = tempfile.mkdtemp(prefix="agentlens-tests-")
os.environ["AGENTOS_DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["AGENTOS_STORAGE_DIR"] = f"{_tmp}/storage"
os.environ["AGENTOS_QDRANT_URL"] = ""
os.environ["AGENTOS_QDRANT_PATH"] = ":memory:"
os.environ["AGENTOS_LLM_API_KEY"] = "test-key"
os.environ["AGENTOS_USE_CELERY"] = "false"

from agentos.main import app  # noqa: E402
from agentos.rag import embeddings  # noqa: E402

VALID_PASSWORD = "Str0ng!pass"
_DENSE_SIZE = 64


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _bucket(token: str, size: int) -> int:
    return zlib.crc32(token.encode()) % size


def _fake_dense(text: str) -> list[float]:
    vector = [0.0] * _DENSE_SIZE
    for token in _tokens(text):
        vector[_bucket(token, _DENSE_SIZE)] += 1.0
    return vector if any(vector) else [1.0] + [0.0] * (_DENSE_SIZE - 1)


def _fake_sparse(text: str) -> tuple[list[int], list[float]]:
    counts: dict[int, float] = {}
    for token in _tokens(text):
        index = _bucket(token, 1_000_003)
        counts[index] = counts.get(index, 0.0) + 1.0
    return list(counts), list(counts.values())


@pytest.fixture(autouse=True)
def fake_retrieval_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bag-of-words stand-ins, so tests neither download models nor depend on their output."""
    monkeypatch.setattr(embeddings, "dense_size", lambda: _DENSE_SIZE)
    monkeypatch.setattr(embeddings, "embed_dense", lambda texts: [_fake_dense(t) for t in texts])
    monkeypatch.setattr(embeddings, "embed_dense_query", _fake_dense)
    monkeypatch.setattr(embeddings, "embed_sparse", lambda texts: [_fake_sparse(t) for t in texts])
    monkeypatch.setattr(embeddings, "embed_sparse_query", _fake_sparse)
    monkeypatch.setattr(
        embeddings,
        "rerank",
        lambda query, texts: [float(len(set(_tokens(query)) & set(_tokens(t)))) for t in texts],
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A signed-out client; each test gets its own cookie jar."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def signed_in(client: TestClient) -> TestClient:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    response = client.post("/api/v1/auth/signup", json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 201
    return client
