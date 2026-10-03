import asyncio
import json

from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig

from agentos import llm
from agentos.agents.common import traced
from agentos.agents.state import AgentState
from agentos.core.config import get_settings
from agentos.mcp.github import call_tool, github_session, read_only_tools

_MAX_REPOSITORIES = 3
_TOOL_RESULT_CHARS = 12_000  # what the model sees of each tool result
_EVIDENCE_CHARS = 6_000  # what is kept of each result as evidence

_SYSTEM = """You are the GitHub agent of AgentLens. Use the read-only GitHub tools to collect \
evidence from the repository {repo} that will help answer the user's request.

- Always pass owner="{owner}" and repo="{name}".
- You have {turns} turns and {budget} tool calls in total. Every turn is expensive, so call \
several tools in the same turn: list a few directories together, read 3-4 files together.
- Turn 1: list the repository root and read README.md together. Then read the specific \
files, search results, commits, issues or pull requests that matter most.
- Read real file contents rather than guessing from file names.
- Do not answer the request. When you have enough evidence, reply with one line saying so."""


def _location(tool: str, arguments: dict) -> str:
    """A short, human-readable reference for where a tool result came from."""
    if tool == "get_file_contents":
        path = arguments.get("path") or "/"
        return f"{path}@{arguments['ref']}" if arguments.get("ref") else path
    details = {k: v for k, v in arguments.items() if k not in ("owner", "repo")}
    return f"{tool}({json.dumps(details, sort_keys=True)})" if details else tool


async def _investigate(
    repo: str, token: str, question: str, tasks: list[str]
) -> tuple[list[dict], str | None]:
    """Run a tool-calling loop against one repository.

    Returns the tool results gathered and, if the loop was cut short by a failure, why.
    Evidence collected before a failure is kept.
    """
    settings = get_settings()
    owner, name = repo.split("/")
    budget = settings.github_max_tool_calls
    task_list = "\n".join(f"- {task}" for task in tasks) or "- Find what is relevant"
    messages: list = [
        (
            "system",
            _SYSTEM.format(
                repo=repo, owner=owner, name=name, budget=budget, turns=settings.github_max_turns
            ),
        ),
        ("human", f"Request:\n{question}\n\nLook for:\n{task_list}"),
    ]
    evidence: dict[str, dict] = {}
    calls_made = 0

    try:
        async with github_session(token) as session:
            tools = await read_only_tools(session)
            for _ in range(settings.github_max_turns):
                reply = await llm.chat(messages, tools)
                messages.append(reply)
                if not reply.tool_calls:
                    break
                for call in reply.tool_calls[: budget - calls_made]:
                    calls_made += 1
                    try:
                        output = await call_tool(session, call["name"], call["args"])
                    except Exception as exc:  # let the model see the failure and move on
                        output = f"Error: {llm.describe_error(exc)}"
                    messages.append(
                        ToolMessage(output[:_TOOL_RESULT_CHARS], tool_call_id=call["id"])
                    )
                    if output and not output.startswith("Error:"):
                        location = _location(call["name"], call["args"])
                        evidence[location] = {
                            "kind": "github",
                            "source": repo,
                            "location": location,
                            "text": output[:_EVIDENCE_CHARS],
                        }
                if calls_made >= budget:
                    break
    except Exception as exc:
        return list(evidence.values()), llm.describe_error(exc)
    return list(evidence.values()), None


def _select(connections: list[dict], state: AgentState, config: RunnableConfig) -> list[dict]:
    """The connected repositories the planner said this request concerns."""
    wanted = {name.lower() for name in state.get("repositories", [])}
    selected = [c for c in connections if c["repo"].lower() in wanted]
    if not selected:
        # The planner named none. Fall back to every repository only when there is nothing
        # else to search, so a question is never left with no evidence source at all.
        has_uploads = any(
            s["kind"] != "github" and s["status"] == "ready"
            for s in config["configurable"]["sources"]
        )
        selected = [] if has_uploads else connections
    return selected[:_MAX_REPOSITORIES]


@traced("github")
async def run(state: AgentState, config: RunnableConfig) -> AgentState:
    """Inspect the relevant connected repositories through GitHub MCP tools."""
    connections = _select(config["configurable"]["github"], state, config)
    if not connections:
        return {"github_results": []}

    results = await asyncio.gather(
        *(
            _investigate(c["repo"], c["token"], state["user_query"], state.get("github_tasks", []))
            for c in connections
        )
    )

    evidence, warnings = [], []
    for connection, (items, error) in zip(connections, results, strict=True):
        evidence.extend(items)
        if error:
            # One failing repository should not sink the whole run.
            warnings.append(f"GitHub agent stopped early on {connection['repo']}: {error}")
    return {
        "github_results": [{"id": f"G{i}", **item} for i, item in enumerate(evidence, start=1)],
        "warnings": warnings,
    }
