from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Break the user's request into tasks for the downstream agents."""
    return {
        "plan": [
            "Retrieve relevant knowledge-base context",
            "Inspect the repository through GitHub MCP",
            "Analyse the relevant source files",
            "Combine, verify and report the findings",
        ]
    }
