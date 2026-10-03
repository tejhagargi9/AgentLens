from langchain_core.runnables import RunnableConfig

from agentos import llm
from agentos.agents.common import all_evidence, format_evidence, traced
from agentos.agents.state import AgentState

_SYSTEM = """You are the Code Analysis agent of AgentLens. You are given source code and \
repository data gathered by other agents, each item labelled with an id like [S1] or [G2].

Explain what this code shows that is relevant to the user's request: which components exist, \
what each is responsible for, how they call or depend on each other, and how data flows \
between them.

Rules:
- Use only the evidence provided. If something is not shown, say it is not shown.
- Put the supporting id in square brackets after every statement, e.g. [G2].
- Be specific: name files, functions, classes, routes and configuration keys.
- At most 400 words. Do not write a final answer; the Analyst agent does that."""


@traced("code_analysis")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Analyse the source code surfaced by the RAG and GitHub agents."""
    code = [item for item in all_evidence(state) if item["kind"] in ("code", "github")]
    if not code:
        return {"code_analysis": ""}

    reply = await llm.chat(
        [
            ("system", _SYSTEM),
            ("human", f"Request:\n{state['user_query']}\n\nEvidence:\n{format_evidence(code)}"),
        ]
    )
    return {"code_analysis": llm.text_of(reply)}
