"""One module per agent. Each exposes `async def run(state) -> partial AgentState`.

All nodes are currently stubs that return placeholder data so the workflow and
its streaming contract can be exercised end to end before any LLM is wired in.
"""
