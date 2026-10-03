import json

from fastapi.testclient import TestClient

from agentos.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_stream_emits_every_agent_then_done():
    response = client.post("/api/v1/runs/stream", json={"query": "How does auth work?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    nodes = [e["node"] for e in events if e["type"] == "node"]

    assert set(nodes) == {
        "planner",
        "rag",
        "github",
        "code_analysis",
        "analyst",
        "verifier",
        "report",
    }
    assert nodes[0] == "planner"
    assert nodes[-3:] == ["analyst", "verifier", "report"]
    assert events[-1] == {"type": "done"}
    assert "How does auth work?" in events[-2]["update"]["final_report"]


def test_run_stream_rejects_empty_query():
    response = client.post("/api/v1/runs/stream", json={"query": ""})
    assert response.status_code == 422
