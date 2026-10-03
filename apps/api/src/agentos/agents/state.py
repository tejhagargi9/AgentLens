import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    """Shared workflow state. Each agent reads what it needs and returns a partial update."""

    user_query: str
    plan: list[str]
    # Written by branches that run in parallel, so updates are appended rather than replaced.
    retrieved_context: Annotated[list[dict], operator.add]
    github_results: Annotated[list[dict], operator.add]
    analysis: str
    verification: list[dict]
    final_report: str
