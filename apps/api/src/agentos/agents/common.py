import time
from collections.abc import Awaitable, Callable
from functools import wraps

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.runnables import RunnableConfig

from agentos.agents.state import AgentState

Node = Callable[[AgentState, RunnableConfig], Awaitable[AgentState]]

_EVIDENCE_CHARS = 3000  # per item, when shown to a model


def traced(name: str) -> Callable[[Node], Node]:
    """Record how long an agent took and how many tokens it used into `metrics`."""

    def decorator(node: Node) -> Node:
        @wraps(node)
        async def wrapper(state: AgentState, config: RunnableConfig) -> AgentState:
            started = time.perf_counter()
            with get_usage_metadata_callback() as usage:
                update = await node(state, config)
            totals = usage.usage_metadata.values()
            metric = {
                "agent": name,
                "seconds": round(time.perf_counter() - started, 2),
                "input_tokens": sum(u.get("input_tokens", 0) for u in totals),
                "output_tokens": sum(u.get("output_tokens", 0) for u in totals),
            }
            return {**update, "metrics": [metric]}

        return wrapper

    return decorator


def all_evidence(state: AgentState) -> list[dict]:
    return [*state.get("retrieved_context", []), *state.get("github_results", [])]


def format_evidence(items: list[dict]) -> str:
    """Evidence as a prompt block, each item headed by the id that must be cited."""
    if not items:
        return "(no evidence)"
    return "\n\n".join(
        f"[{item['id']}] {item['source']} — {item['location']}\n{item['text'][:_EVIDENCE_CHARS]}"
        for item in items
    )
