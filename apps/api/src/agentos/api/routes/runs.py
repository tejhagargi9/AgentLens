import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from agentos.agents.graph import get_graph
from agentos.api.deps import CurrentUser, SessionDep
from agentos.core.security import decrypt_secret
from agentos.db.models import Source
from agentos.llm import LLMNotConfiguredError, describe_error, require_llm_configured

router = APIRouter()
logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _evidence_refs(items: list[dict]) -> list[dict]:
    return [{k: item[k] for k in ("id", "kind", "source", "location")} for item in items]


def _public_detail(node: str, update: dict) -> dict:
    """What the browser is shown for each agent: results, without bulky evidence text."""
    match node:
        case "planner":
            keys = ("plan", "search_queries", "repositories", "github_tasks")
            return {k: update.get(k, []) for k in keys}
        case "rag":
            return {"evidence": _evidence_refs(update.get("retrieved_context", []))}
        case "github":
            return {"evidence": _evidence_refs(update.get("github_results", []))}
        case "code_analysis":
            return {"notes": update.get("code_analysis", "")}
        case "analyst":
            analysis = update.get("analysis", {})
            return {"summary": analysis.get("summary", ""), "gaps": analysis.get("gaps", [])}
        case "verifier":
            return {"claims": update.get("verification", [])}
        case "report":
            return {"final_report": update.get("final_report", "")}
    return {}


async def _stream_run(query: str, configurable: dict) -> AsyncIterator[str]:
    """Run the agent workflow and emit one SSE frame per finished agent.

    Event shapes (mirrored in apps/web/src/lib/types.ts):
      {"type": "node", "node": str, "detail": dict, "metrics": dict, "warnings": [str]}
      {"type": "done"}
      {"type": "error", "message": str}
    """
    try:
        require_llm_configured()
        stream = get_graph().astream(
            {"user_query": query}, {"configurable": configurable}, stream_mode="updates"
        )
        async for chunk in stream:
            for node, update in chunk.items():
                update = update or {}
                yield _sse(
                    {
                        "type": "node",
                        "node": node,
                        "detail": _public_detail(node, update),
                        "metrics": (update.get("metrics") or [{}])[0],
                        "warnings": update.get("warnings", []),
                    }
                )
        yield _sse({"type": "done"})
    except LLMNotConfiguredError as exc:
        yield _sse({"type": "error", "message": str(exc)})
    except Exception as exc:  # the stream is already open, so report failure in-band
        logger.exception("Agent run failed")
        yield _sse({"type": "error", "message": describe_error(exc)})


@router.post("/stream")
async def stream_run(request: RunRequest, user: CurrentUser, session: SessionDep):
    sources = list(await session.scalars(select(Source).where(Source.user_id == user.id)))
    # Loaded up front so the stream does not hold a database session open while agents run.
    configurable = {
        "user_id": str(user.id),
        "sources": [{"kind": s.kind, "name": s.name, "status": s.status} for s in sources],
        "github": [
            {"repo": s.name, "token": decrypt_secret(s.encrypted_token)}
            for s in sources
            if s.kind == "github" and s.encrypted_token
        ],
    }
    return StreamingResponse(
        _stream_run(request.query, configurable),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
