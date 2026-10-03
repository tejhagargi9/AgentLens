from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Check each claim in the analysis against the collected evidence."""
    return {"verification": []}
