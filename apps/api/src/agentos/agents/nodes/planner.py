from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from agentos import llm
from agentos.agents.common import traced
from agentos.agents.state import AgentState

_SYSTEM = """You are the Planner agent of AgentLens, a system that answers technical questions \
about codebases and documentation using evidence gathered by other agents.

Break the user's request into a short plan and decide what each evidence-gathering agent \
should look for:
- The RAG agent runs hybrid (semantic + keyword) search over the user's uploaded documents \
and codebases. Write search queries that name the concepts, identifiers and file types likely \
to appear in relevant text.
- The GitHub agent explores connected repositories with read-only tools (list directories, \
read files, search code, read commits, issues and pull requests). Write concrete things for \
it to find.

Only plan work for sources that exist. Do not answer the question."""


class Plan(BaseModel):
    tasks: list[str] = Field(description="2-6 short steps that together answer the request")
    search_queries: list[str] = Field(
        description="1-4 knowledge-base search queries; empty if there are no uploaded sources"
    )
    repositories: list[str] = Field(
        description="Exact names (owner/repo) of the connected GitHub repositories this request "
        "is about. Leave out repositories it does not concern; empty if none apply."
    )
    github_tasks: list[str] = Field(
        description="1-4 things to find in those repositories; empty if none apply"
    )


def _describe_sources(sources: list[dict]) -> str:
    if not sources:
        return "(none)"
    return "\n".join(f"- {s['kind']}: {s['name']} ({s['status']})" for s in sources)


@traced("planner")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Break the user's request into tasks for the downstream agents."""
    sources = config["configurable"]["sources"]
    plan = await llm.structured(
        Plan,
        [
            ("system", _SYSTEM),
            (
                "human",
                f"Available sources:\n{_describe_sources(sources)}\n\n"
                f"Request:\n{state['user_query']}",
            ),
        ],
    )
    return {
        "plan": plan.tasks,
        "search_queries": plan.search_queries[:4],
        "repositories": plan.repositories,
        "github_tasks": plan.github_tasks[:4],
    }
