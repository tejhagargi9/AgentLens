from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Analyse the source files surfaced by the GitHub agent."""
    return {"github_results": []}
