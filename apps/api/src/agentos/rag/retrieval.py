import asyncio

from agentos.core.config import get_settings
from agentos.rag import embeddings, store


def _location(chunk: dict) -> str:
    if chunk.get("page"):
        return f"page {chunk['page']}"
    lines = f"{chunk['start_line']}-{chunk['end_line']}"
    return f"{chunk['path']}:{lines}" if chunk["path"] else f"lines {lines}"


def _retrieve(user_id: str, question: str, queries: list[str]) -> list[dict]:
    settings = get_settings()
    result_lists = [
        store.hybrid_search(user_id, query, settings.retrieval_candidates) for query in queries
    ]
    # Interleave the lists so every query contributes its best hits to the rerank budget
    # (the cross-encoder is the slow step, so it only sees `retrieval_candidates` chunks).
    candidates: dict[str, dict] = {}
    for rank in range(settings.retrieval_candidates):
        for results in result_lists:
            if rank < len(results):
                candidates.setdefault(results[rank]["point_id"], results[rank])
    if not candidates:
        return []

    # Rerank against the user's actual question, not the planner's sub-queries.
    chunks = list(candidates.values())[: settings.retrieval_candidates]
    scores = embeddings.rerank(question, [chunk["text"] for chunk in chunks])
    ranked = sorted(zip(scores, chunks, strict=True), key=lambda pair: pair[0], reverse=True)
    return [
        {
            "kind": "code" if chunk["kind"] == "codebase" else "document",
            "source": chunk["source_name"],
            "location": _location(chunk),
            "text": chunk["text"],
        }
        for _, chunk in ranked[: settings.retrieval_top_k]
    ]


async def retrieve(user_id: str, question: str, queries: list[str]) -> list[dict]:
    """Hybrid search for each query, then rerank the merged candidates against `question`.

    Returns evidence items: {kind, source, location, text}.
    """
    return await asyncio.to_thread(_retrieve, user_id, question, queries)
