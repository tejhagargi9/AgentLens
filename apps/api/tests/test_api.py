from fastapi.testclient import TestClient


def test_health(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_run_stream_requires_sign_in(client: TestClient):
    response = client.post("/api/v1/runs/stream", json={"query": "How does auth work?"})
    assert response.status_code == 401


def test_run_stream_rejects_empty_query(signed_in: TestClient):
    response = signed_in.post("/api/v1/runs/stream", json={"query": ""})
    assert response.status_code == 422
