"""End-to-end runs of the agent workflow with the LLM and the GitHub MCP server faked.

Indexing, Qdrant hybrid search, the graph wiring, verification rules and report assembly are
all real; only model calls and network access are replaced.
"""

import io
import json
import time
import zipfile
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from sqlalchemy import create_engine, inspect, text

from agentos import llm
from agentos.agents.nodes import github as github_node
from agentos.agents.nodes.analyst import Analysis, Claim
from agentos.agents.nodes.planner import Plan
from agentos.agents.nodes.verifier import Verdict, Verdicts
from agentos.api.routes import sources as sources_routes
from agentos.core.config import get_settings
from agentos.db.session import _add_missing_columns
from agentos.rag.chunking import chunk_source
from tests.conftest import VALID_PASSWORD

SOURCES = "/api/v1/sources"
GITHUB_TOKEN = "github_pat_" + "s3cret" * 6
QUOTA_ERROR = (
    "429 RESOURCE_EXHAUSTED. Quota exceeded for metric: free_tier_requests, limit: 20, "
    "model: gemini-3.6-flash\nPlease retry in 13h46m56.285162307s."
)
AUTH_DOC = b"""# Authentication

Login is handled by the login handler, which issues a JWT session token.
Refresh tokens rotate on every use.
"""


class FakeLLM:
    """Scripted model: records every call and answers by which agent is asking."""

    def __init__(self, analysis: Analysis):
        self.analysis = analysis
        self.repositories = ["octocat/app"]
        self.fail_tool_loop_after: int | None = None  # tool-loop turns before the model errors
        self.calls: list[str] = []

    async def structured(self, schema, messages):
        self.calls.append(schema.__name__)
        if schema is Plan:
            return Plan(
                tasks=["Find how login works"],
                search_queries=["login handler JWT session token"],
                repositories=self.repositories,
                github_tasks=["Find the auth module"],
            )
        if schema is Analysis:
            return self.analysis
        if schema is Verdicts:
            prompt = messages[-1][1]
            numbers = [int(line.split(".")[0]) for line in prompt.split("\n\n")[0].splitlines()[1:]]
            return Verdicts(
                verdicts=[
                    Verdict(claim=n, supported="rotate" not in line, reason="Checked.")
                    for n, line in zip(numbers, prompt.splitlines()[1:], strict=False)
                ]
            )
        raise AssertionError(f"unexpected schema {schema}")

    async def chat(self, messages, tools=None):
        if tools:
            turns_so_far = sum(getattr(m, "type", None) == "ai" for m in messages)
            if turns_so_far == self.fail_tool_loop_after:
                raise RuntimeError(QUOTA_ERROR)
            self.calls.append("github_tool_loop")
            already_called = any(getattr(m, "type", None) == "tool" for m in messages)
            if already_called:
                return AIMessage("Enough evidence gathered.")
            return AIMessage(
                "",
                tool_calls=[
                    {
                        "name": "get_file_contents",
                        "args": {"owner": "octocat", "repo": "app", "path": "src/auth.py"},
                        "id": "call-1",
                    }
                ],
            )
        system = messages[0][1]
        if "Code Analysis agent" in system:
            self.calls.append("code_analysis")
            return AIMessage("auth.py defines login() [G1].")
        self.calls.append("report")
        return AIMessage("## Summary\n\nLogin issues a JWT [S1].")


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLM:
    fake = FakeLLM(
        Analysis(
            summary="Login issues a JWT.",
            claims=[
                Claim(statement="The login handler issues a JWT.", evidence_ids=["S1"]),
                Claim(statement="Refresh tokens rotate hourly.", evidence_ids=["S1"]),
                Claim(statement="Passwords are hashed with bcrypt.", evidence_ids=["S99"]),
            ],
            gaps=["Where tokens are stored"],
        )
    )
    monkeypatch.setattr(llm, "structured", fake.structured)
    monkeypatch.setattr(llm, "chat", fake.chat)
    return fake


def _run(client: TestClient, query: str = "How does login work?") -> dict[str, dict]:
    """Run the workflow; return each agent's event keyed by node, plus "_end" and "_raw"."""
    response = client.post("/api/v1/runs/stream", json={"query": query})
    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    by_node = {e["node"]: e for e in events if e["type"] == "node"}
    return {**by_node, "_end": events[-1], "_raw": response.text, "_order": list(by_node)}


def _upload_and_index(client: TestClient, kind: str, filename: str, content: bytes) -> dict:
    created = client.post(
        f"{SOURCES}/upload", data={"kind": kind}, files={"file": (filename, content)}
    )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    for _ in range(100):
        source = next(s for s in client.get(SOURCES).json() if s["id"] == created.json()["id"])
        if source["status"] in ("ready", "failed"):
            return source
        time.sleep(0.05)
    raise AssertionError("indexing did not finish")


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_full_run_over_an_indexed_document(signed_in: TestClient, fake_llm: FakeLLM):
    source = _upload_and_index(signed_in, "document", "auth.md", AUTH_DOC)
    assert source["status"] == "ready"
    assert source["chunk_count"] >= 1

    run = _run(signed_in)

    assert run["_end"] == {"type": "done"}
    assert run["_order"][0] == "planner"
    assert set(run["_order"][1:3]) == {"rag", "github"}
    assert run["_order"][3:] == ["code_analysis", "analyst", "verifier", "report"]

    evidence = run["rag"]["detail"]["evidence"]
    assert evidence[0] == {
        "id": "S1",
        "kind": "document",
        "source": "auth.md",
        "location": "lines 1-4",
    }
    assert "rotate on every use" not in run["_raw"]  # evidence text is not streamed

    claims = {c["statement"]: c for c in run["verifier"]["detail"]["claims"]}
    assert claims["The login handler issues a JWT."]["status"] == "verified"
    assert claims["Refresh tokens rotate hourly."]["status"] == "needs_review"
    # A claim citing evidence that does not exist is rejected without asking the model.
    assert claims["Passwords are hashed with bcrypt."] == {
        "statement": "Passwords are hashed with bcrypt.",
        "evidence_ids": [],
        "status": "needs_review",
        "reason": "No existing evidence was cited for this claim.",
    }

    report = run["report"]["detail"]["final_report"]
    assert report.startswith("## Summary")
    assert "- **[S1]** auth.md — `lines 1-4`" in report
    assert "- Claims: 1 verified, 2 need review" in report
    assert "| Planner Agent |" in report and "| Verifier Agent |" in report
    assert run["planner"]["metrics"]["agent"] == "planner"


def test_codebase_is_indexed_with_paths_and_lines(signed_in: TestClient, fake_llm: FakeLLM):
    archive = _zip(
        {
            "app/src/auth.py": "import jwt\n\n\ndef login(user):\n    return jwt.encode(user)\n",
            "app/node_modules/lib/index.js": "function login() {}",
            "app/logo.png": "not really an image",
        }
    )
    source = _upload_and_index(signed_in, "codebase", "app.zip", archive)
    assert (source["status"], source["chunk_count"]) == ("ready", 1)

    run = _run(signed_in, "Where is the login function defined?")

    assert run["rag"]["detail"]["evidence"] == [
        {"id": "S1", "kind": "code", "source": "app.zip", "location": "app/src/auth.py:1-5"}
    ]
    assert "code_analysis" in fake_llm.calls


def test_retrieval_never_crosses_users(signed_in: TestClient, client, fake_llm: FakeLLM):
    _upload_and_index(signed_in, "document", "auth.md", AUTH_DOC)

    client.cookies.clear()
    client.post(
        "/api/v1/auth/signup", json={"email": "intruder@example.com", "password": VALID_PASSWORD}
    )
    run = _run(client)

    assert run["rag"]["detail"]["evidence"] == []
    assert "You have not added any sources yet" in run["report"]["detail"]["final_report"]
    # With nothing to analyse, only the planner called the model.
    assert fake_llm.calls == ["Plan"]


def test_deleting_a_source_removes_it_from_search(signed_in: TestClient, fake_llm: FakeLLM):
    source = _upload_and_index(signed_in, "document", "auth.md", AUTH_DOC)
    assert _run(signed_in)["rag"]["detail"]["evidence"]

    assert signed_in.delete(f"{SOURCES}/{source['id']}").status_code == 204
    assert _run(signed_in)["rag"]["detail"]["evidence"] == []


def test_unreadable_upload_is_marked_failed(signed_in: TestClient):
    source = _upload_and_index(signed_in, "codebase", "empty.zip", _zip({"logo.png": "x"}))
    assert source["status"] == "failed"
    assert "No readable text" in source["error"]


@pytest.fixture
def fake_github(monkeypatch: pytest.MonkeyPatch) -> list:
    """Replaces the GitHub MCP server; returns the list of tool calls it received."""
    calls: list = []

    async def fake_verify(token, owner, repo):
        return None

    @asynccontextmanager
    async def fake_session(token):
        calls.append(("session", token))
        yield object()

    async def fake_tools(session):
        return [{"type": "function", "function": {"name": "get_file_contents", "parameters": {}}}]

    async def fake_call(session, name, arguments):
        calls.append((name, arguments))
        return "def login(user):\n    return issue_jwt(user)"

    monkeypatch.setattr(sources_routes, "verify_repository_access", fake_verify)
    monkeypatch.setattr(github_node, "github_session", fake_session)
    monkeypatch.setattr(github_node, "read_only_tools", fake_tools)
    monkeypatch.setattr(github_node, "call_tool", fake_call)
    return calls


def test_github_agent_gathers_evidence_through_mcp(
    signed_in: TestClient, fake_llm: FakeLLM, fake_github: list
):
    fake_llm.analysis = Analysis(
        summary="login() issues a JWT.",
        claims=[Claim(statement="login() calls issue_jwt.", evidence_ids=["G1"])],
        gaps=[],
    )
    connected = signed_in.post(
        f"{SOURCES}/github", json={"repository": "octocat/app", "token": GITHUB_TOKEN}
    )
    assert connected.json()["status"] == "ready"

    run = _run(signed_in)

    assert fake_github == [
        ("session", GITHUB_TOKEN),
        ("get_file_contents", {"owner": "octocat", "repo": "app", "path": "src/auth.py"}),
    ]
    assert run["github"]["detail"]["evidence"] == [
        {"id": "G1", "kind": "github", "source": "octocat/app", "location": "src/auth.py"}
    ]
    assert run["verifier"]["detail"]["claims"][0]["status"] == "verified"
    assert "- **[G1]** octocat/app — `src/auth.py`" in run["report"]["detail"]["final_report"]
    assert GITHUB_TOKEN not in run["_raw"]


def test_unreachable_repository_becomes_a_warning_not_a_failure(
    signed_in: TestClient, fake_llm: FakeLLM, fake_github: list, monkeypatch: pytest.MonkeyPatch
):
    @asynccontextmanager
    async def broken_session(token):
        raise ConnectionError("MCP server unavailable")
        yield

    monkeypatch.setattr(github_node, "github_session", broken_session)
    signed_in.post(f"{SOURCES}/github", json={"repository": "octocat/app", "token": GITHUB_TOKEN})

    run = _run(signed_in)

    assert run["_end"] == {"type": "done"}
    assert run["github"]["warnings"] == [
        "GitHub agent stopped early on octocat/app: MCP server unavailable"
    ]
    report = run["report"]["detail"]["final_report"]
    assert "No evidence could be gathered because an agent did not finish" in report
    assert "MCP server unavailable" in report


def test_evidence_gathered_before_a_model_failure_is_kept(
    signed_in: TestClient, fake_llm: FakeLLM, fake_github: list
):
    """Hitting the provider's quota mid-investigation must not discard files already read."""
    fake_llm.analysis = Analysis(
        summary="login() issues a JWT.",
        claims=[Claim(statement="login() calls issue_jwt.", evidence_ids=["G1"])],
        gaps=[],
    )
    fake_llm.fail_tool_loop_after = 1  # first turn reads a file, second turn hits the quota
    signed_in.post(f"{SOURCES}/github", json={"repository": "octocat/app", "token": GITHUB_TOKEN})

    run = _run(signed_in)

    assert [e["location"] for e in run["github"]["detail"]["evidence"]] == ["src/auth.py"]
    assert run["github"]["warnings"] == [
        "GitHub agent stopped early on octocat/app: The LLM provider's quota or rate limit "
        "was exceeded (20 requests allowed for gemini-3.6-flash); retry in 13h46m56s."
    ]
    assert run["verifier"]["detail"]["claims"][0]["status"] == "verified"
    assert run["_end"] == {"type": "done"}


def test_only_repositories_the_planner_names_are_inspected(
    signed_in: TestClient, fake_llm: FakeLLM, fake_github: list
):
    for repository in ("octocat/app", "octocat/unrelated"):
        signed_in.post(f"{SOURCES}/github", json={"repository": repository, "token": GITHUB_TOKEN})

    run = _run(signed_in)

    assert run["planner"]["detail"]["repositories"] == ["octocat/app"]
    assert len([call for call in fake_github if call[0] == "session"]) == 1
    assert {e["source"] for e in run["github"]["detail"]["evidence"]} == {"octocat/app"}


def test_model_failure_outside_an_agent_loop_is_reported_readably(
    signed_in: TestClient, monkeypatch: pytest.MonkeyPatch
):
    async def exhausted(schema, messages):
        raise ExceptionGroup("unhandled errors in a TaskGroup", [RuntimeError(QUOTA_ERROR)])

    monkeypatch.setattr(llm, "structured", exhausted)
    run = _run(signed_in)

    assert run["_end"] == {
        "type": "error",
        "message": "The LLM provider's quota or rate limit was exceeded "
        "(20 requests allowed for gemini-3.6-flash); retry in 13h46m56s.",
    }


def test_run_without_llm_key_reports_a_clear_error(
    signed_in: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(get_settings(), "llm_api_key", "")
    run = _run(signed_in)
    assert run["_end"]["type"] == "error"
    assert "AGENTOS_LLM_API_KEY" in run["_end"]["message"]


def test_chunking_skips_dependencies_and_binary_files(tmp_path):
    archive = tmp_path / "code.zip"
    archive.write_bytes(
        _zip(
            {
                "src/a.py": "x = 1\n" * 400,
                ".git/config": "[core]",
                "package-lock.json": "{}",
                "bin/tool.exe": "MZ",
            }
        )
    )
    chunks = chunk_source("codebase", archive)

    assert {c.path for c in chunks} == {"src/a.py"}
    assert len(chunks) > 1
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 400
    assert all(c.language == "python" for c in chunks)


def test_existing_database_gains_new_columns(tmp_path):
    """A database created before `status` existed is upgraded in place, keeping its rows."""
    engine = create_engine(f"sqlite:///{tmp_path}/old.db")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users (id CHAR(32) PRIMARY KEY, email VARCHAR, "
                "password_hash VARCHAR, created_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE sources (id CHAR(32) PRIMARY KEY, user_id CHAR(32), kind VARCHAR, "
                "name VARCHAR, size_bytes INTEGER, storage_path VARCHAR, encrypted_token TEXT, "
                "created_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO sources (id, kind, name) VALUES "
                "('1', 'github', 'o/r'), ('2', 'document', 'a.md')"
            )
        )
        _add_missing_columns(connection)
        _add_missing_columns(connection)  # safe to run on every startup

    with engine.connect() as connection:
        columns = {c["name"] for c in inspect(connection).get_columns("sources")}
        rows = dict(connection.execute(text("SELECT name, status FROM sources")).all())
    assert {"status", "error", "chunk_count"} <= columns
    assert rows == {"o/r": "ready", "a.md": "pending"}
