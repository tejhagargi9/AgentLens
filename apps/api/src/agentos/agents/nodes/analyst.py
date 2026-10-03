from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from agentos import llm
from agentos.agents.common import all_evidence, format_evidence, traced
from agentos.agents.state import AgentState

_SYSTEM = """You are the Analyst agent of AgentLens. Combine the evidence gathered by the \
other agents into findings that answer the user's request.

Rules:
- Every claim must be one specific, checkable statement, supported by the evidence ids you \
list for it. A separate Verifier agent will check each claim against exactly those items.
- Use only the evidence and the code analysis notes. Never rely on outside knowledge about \
the project.
- Prefer several precise claims over a few broad ones. Name files, functions and routes.
- Put anything the request asked for that the evidence does not show into `gaps`."""


class Claim(BaseModel):
    statement: str = Field(description="One specific, checkable finding")
    evidence_ids: list[str] = Field(description='Ids of supporting evidence, e.g. ["S1", "G2"]')


class Analysis(BaseModel):
    summary: str = Field(description="2-4 sentence direct answer to the request")
    claims: list[Claim] = Field(description="3-12 findings")
    gaps: list[str] = Field(description="What could not be determined from the evidence")


@traced("analyst")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Combine retrieved context and repository findings into cited claims."""
    evidence = all_evidence(state)
    if not evidence:
        return {"analysis": {"summary": "", "claims": [], "gaps": []}}

    plan = "\n".join(f"- {task}" for task in state.get("plan", []))
    analysis = await llm.structured(
        Analysis,
        [
            ("system", _SYSTEM),
            (
                "human",
                f"Request:\n{state['user_query']}\n\nPlan:\n{plan}\n\n"
                f"Code analysis notes:\n{state.get('code_analysis') or '(none)'}\n\n"
                f"Evidence:\n{format_evidence(evidence)}",
            ),
        ],
    )
    return {"analysis": analysis.model_dump()}
