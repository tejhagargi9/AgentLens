from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Combine retrieved context and repository findings into an analysis."""
    return {"analysis": "Stub: no analysis yet."}
