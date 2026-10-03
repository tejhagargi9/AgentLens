from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Retrieve evidence from the knowledge base (agentos.rag)."""
    return {"retrieved_context": []}
