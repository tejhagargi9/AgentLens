import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agentos.agents.graph import get_graph

router = APIRouter()


class RunRequest(BaseModel):
    query: str = Field(min_length=1)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _stream_run(query: str) -> AsyncIterator[str]:
    """Run the agent workflow and emit one SSE frame per finished node.

    Event shapes (mirrored in apps/web/src/lib/types.ts):
      {"type": "node", "node": str, "update": dict}
      {"type": "done"}
      {"type": "error", "message": str}
    """
    try:
        async for chunk in get_graph().astream({"user_query": query}, stream_mode="updates"):
            for node, update in chunk.items():
                yield _sse({"type": "node", "node": node, "update": update or {}})
        yield _sse({"type": "done"})
    except Exception as exc:  # the stream is already open, so report failure in-band
        yield _sse({"type": "error", "message": str(exc)})


@router.post("/stream")
async def stream_run(request: RunRequest) -> StreamingResponse:
    return StreamingResponse(
        _stream_run(request.query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
