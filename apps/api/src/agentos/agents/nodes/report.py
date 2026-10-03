from langchain_core.runnables import RunnableConfig

from agentos import llm
from agentos.agents.common import all_evidence, traced
from agentos.agents.state import AgentState

_AGENT_LABELS = {
    "planner": "Planner Agent",
    "rag": "RAG Agent",
    "github": "GitHub Agent (MCP)",
    "code_analysis": "Code Analysis Agent",
    "analyst": "Analyst Agent",
    "verifier": "Verifier Agent",
}

_SYSTEM = """You are the Report agent of AgentLens. Write the final technical report in \
GitHub-flavoured Markdown from the verified findings you are given.

Use these sections, in this order, and omit a section only if there is nothing to put in it:
## Summary
## Architecture
## Key Components
## Findings
## Potential Issues
## Recommendations

Rules:
- State as fact only what the VERIFIED findings say, and keep their citation ids in square \
brackets exactly as given, e.g. [S1][G2].
- Findings marked NEEDS REVIEW may appear only under a "## Unverified" section, each with the \
reason it could not be verified.
- List anything in GAPS under "## Not Determined". Never fill a gap with a guess.
- Recommendations must follow from the findings; mark them as suggestions.
- Do not add a sources list or an execution summary; those are appended automatically.
- Start directly with "## Summary". No preamble."""


def _no_evidence_report(state: AgentState, sources: list[dict]) -> str:
    uploads = [s for s in sources if s["kind"] != "github"]
    lines = ["## No evidence found", ""]
    if not sources:
        lines.append(
            "You have not added any sources yet. Upload documents or a codebase, or connect a "
            "GitHub repository, then ask again."
        )
    elif state.get("warnings"):
        lines.append("No evidence could be gathered because an agent did not finish:")
    else:
        lines.append(
            "None of your sources returned anything relevant to this question, so there is "
            "nothing to base a verified answer on."
        )
        still_indexing = [s["name"] for s in uploads if s["status"] in ("pending", "indexing")]
        failed = [s["name"] for s in uploads if s["status"] == "failed"]
        if still_indexing:
            lines.append(f"\nStill being indexed: {', '.join(still_indexing)}. Try again shortly.")
        if failed:
            lines.append(f"\nFailed to index: {', '.join(failed)}.")
    for warning in state.get("warnings", []):
        lines.append(f"\n- {warning}")
    return "\n".join(lines)


def _source_references(state: AgentState) -> str:
    cited = {i for claim in state.get("verification", []) for i in claim["evidence_ids"]}
    rows = [
        f"- **[{item['id']}]** {item['source']} — `{item['location']}`"
        for item in all_evidence(state)
        if item["id"] in cited
    ]
    return "## Source References\n\n" + ("\n".join(rows) or "_No sources were cited._")


def _execution_summary(state: AgentState) -> str:
    verification = state.get("verification", [])
    verified = sum(claim["status"] == "verified" for claim in verification)
    rows = [
        f"| {_AGENT_LABELS.get(m['agent'], m['agent'])} | {m['seconds']}s "
        f"| {m['input_tokens']} | {m['output_tokens']} |"
        for m in state.get("metrics", [])
    ]
    lines = [
        "## Agent Execution Summary",
        "",
        f"- Evidence gathered: {len(state.get('retrieved_context', []))} knowledge-base "
        f"chunks, {len(state.get('github_results', []))} GitHub tool results",
        f"- Claims: {verified} verified, {len(verification) - verified} need review",
        *(f"- Warning: {warning}" for warning in state.get("warnings", [])),
        "",
        "| Agent | Time | Input tokens | Output tokens |",
        "|---|---|---|---|",
        *rows,
    ]
    return "\n".join(lines)


def _findings_block(state: AgentState) -> str:
    lines = []
    for claim in state.get("verification", []):
        ids = "".join(f"[{i}]" for i in claim["evidence_ids"])
        if claim["status"] == "verified":
            lines.append(f"VERIFIED: {claim['statement']} {ids}")
        else:
            lines.append(f"NEEDS REVIEW: {claim['statement']} {ids} (reason: {claim['reason']})")
    return "\n".join(lines) or "(none)"


@traced("report")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Write the final structured report with source references."""
    if not all_evidence(state):
        return {"final_report": _no_evidence_report(state, config["configurable"]["sources"])}

    analysis = state.get("analysis", {})
    gaps = "\n".join(f"- {gap}" for gap in analysis.get("gaps", [])) or "(none)"
    reply = await llm.chat(
        [
            ("system", _SYSTEM),
            (
                "human",
                f"Request:\n{state['user_query']}\n\n"
                f"Analyst summary:\n{analysis.get('summary', '')}\n\n"
                f"FINDINGS:\n{_findings_block(state)}\n\n"
                f"GAPS:\n{gaps}\n\n"
                f"Code analysis notes (context only, cite findings not these):\n"
                f"{state.get('code_analysis') or '(none)'}",
            ),
        ]
    )
    body = llm.text_of(reply).strip()
    report = "\n\n".join([body, _source_references(state), _execution_summary(state)])
    return {"final_report": report}
