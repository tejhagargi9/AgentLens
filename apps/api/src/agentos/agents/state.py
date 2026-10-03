import operator
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    """Shared workflow state. Each agent reads what it needs and returns a partial update.

    Evidence items (in `retrieved_context` and `github_results`) have the shape
    {id, kind: "document" | "code" | "github", source, location, text}. Their ids
    ("S1", "G2", ...) are what claims and the final report cite.

    Per-run inputs that must not be streamed to the browser (user id, GitHub tokens) travel
    in the run's `config["configurable"]`, not in this state.
    """

    user_query: str
    # Planner
    plan: list[str]
    search_queries: list[str]
    repositories: list[str]  # connected repos the request concerns
    github_tasks: list[str]
    # Evidence gathering (the two branches run in parallel and write different keys)
    retrieved_context: list[dict]
    github_results: list[dict]
    # Reasoning
    code_analysis: str
    analysis: dict  # {summary, claims: [{statement, evidence_ids}], gaps: [str]}
    verification: list[dict]  # [{statement, evidence_ids, status, reason}]
    final_report: str
    # Appended to by every agent
    metrics: Annotated[list[dict], operator.add]
    warnings: Annotated[list[str], operator.add]
