from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Inspect the connected repository through GitHub MCP tools (agentos.mcp)."""
    return {"github_results": []}
