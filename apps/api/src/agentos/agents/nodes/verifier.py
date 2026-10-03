from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from agentos import llm
from agentos.agents.common import all_evidence, format_evidence, traced
from agentos.agents.state import AgentState

_SYSTEM = """You are the Verifier agent of AgentLens. For each numbered claim, decide whether \
the evidence cited for it actually supports it.

- `supported` is true only if the cited evidence directly shows what the claim states. \
Plausible but unshown, or only partly shown, is not supported.
- Judge strictly from the evidence text. Ignore outside knowledge.
- Give a one-sentence reason. Return exactly one verdict per claim, using its number."""


class Verdict(BaseModel):
    claim: int = Field(description="The claim's number")
    supported: bool
    reason: str = Field(description="One sentence")


class Verdicts(BaseModel):
    verdicts: list[Verdict]


@traced("verifier")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Check each claim in the analysis against the evidence it cites."""
    evidence = {item["id"]: item for item in all_evidence(state)}
    results = []
    for claim in state.get("analysis", {}).get("claims", []):
        known = [i for i in dict.fromkeys(claim["evidence_ids"]) if i in evidence]
        results.append(
            {
                "statement": claim["statement"],
                "evidence_ids": known,
                "status": "needs_review",
                "reason": "The model's verdict was missing for this claim."
                if known
                else "No existing evidence was cited for this claim.",
            }
        )

    # Claims that cite nothing real are settled without asking the model.
    checkable = [(n, r) for n, r in enumerate(results, start=1) if r["evidence_ids"]]
    if not checkable:
        return {"verification": results}

    claims_block = "\n".join(
        f"{n}. {r['statement']} (cites {', '.join(r['evidence_ids'])})" for n, r in checkable
    )
    cited = {i for _, r in checkable for i in r["evidence_ids"]}
    reply = await llm.structured(
        Verdicts,
        [
            ("system", _SYSTEM),
            (
                "human",
                f"Claims:\n{claims_block}\n\n"
                f"Evidence:\n{format_evidence([evidence[i] for i in evidence if i in cited])}",
            ),
        ],
    )
    numbers = {n for n, _ in checkable}
    for verdict in reply.verdicts:
        if verdict.claim in numbers:
            result = results[verdict.claim - 1]
            result["status"] = "verified" if verdict.supported else "needs_review"
            result["reason"] = verdict.reason
    return {"verification": results}
