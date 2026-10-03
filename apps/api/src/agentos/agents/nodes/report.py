from agentos.agents.state import AgentState


async def run(state: AgentState) -> AgentState:
    """Write the final structured report with source references."""
    return {
        "final_report": (
            f"Stub report for: {state['user_query']}\n\n"
            "The agent pipeline ran end to end, but no LLM, retrieval or MCP tools "
            "are wired in yet."
        )
    }
