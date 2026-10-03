from langchain_core.runnables import RunnableConfig

from agentos.agents.common import traced
from agentos.agents.state import AgentState
from agentos.rag.retrieval import retrieve


@traced("rag")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Retrieve evidence from the user's indexed documents and codebases."""
    configurable = config["configurable"]
    has_indexed_uploads = any(
        s["kind"] != "github" and s["status"] == "ready" for s in configurable["sources"]
    )
    if not has_indexed_uploads:
        return {"retrieved_context": []}

    question = state["user_query"]
    queries = list(dict.fromkeys([question, *state.get("search_queries", [])]))
    chunks = await retrieve(configurable["user_id"], question, queries)
    return {
        "retrieved_context": [{"id": f"S{i}", **chunk} for i, chunk in enumerate(chunks, start=1)]
    }
