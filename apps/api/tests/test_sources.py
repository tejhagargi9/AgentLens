import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentos.api.routes import sources as sources_routes
from agentos.core.security import decrypt_secret
from agentos.mcp.github import GitHubMCPError

UPLOAD = "/api/v1/sources/upload"
GITHUB = "/api/v1/sources/github"
SOURCES = "/api/v1/sources"
TOKEN = "github_pat_" + "a" * 30


def _zip(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _upload(client: TestClient, kind: str, filename: str, content: bytes):
    return client.post(UPLOAD, data={"kind": kind}, files={"file": (filename, content)})


def test_sources_require_sign_in(client: TestClient):
    assert client.get(SOURCES).status_code == 401
    assert _upload(client, "document", "notes.md", b"# hi").status_code == 401
    assert client.post(GITHUB, json={"repository": "a/b", "token": TOKEN}).status_code == 401


def test_upload_document_and_codebase_then_list(signed_in: TestClient):
    document = _upload(signed_in, "document", "notes.md", b"# Notes")
    codebase = _upload(signed_in, "codebase", "app.zip", _zip({"src/main.py": "print('hi')"}))
    assert document.status_code == 201
    assert codebase.status_code == 201
    assert document.json()["size_bytes"] == len(b"# Notes")

    listed = signed_in.get(SOURCES).json()
    assert {(s["kind"], s["name"]) for s in listed} == {
        ("document", "notes.md"),
        ("codebase", "app.zip"),
    }


@pytest.mark.parametrize(
    ("kind", "filename", "content", "message"),
    [
        ("document", "malware.exe", b"MZ", "Documents must be one of"),
        ("document", "fake.pdf", b"not a pdf", "not a valid PDF"),
        ("document", "empty.md", b"", "empty"),
        ("codebase", "code.tar", b"data", "must be uploaded as a .zip"),
        ("codebase", "fake.zip", b"not a zip", "not a valid zip"),
        ("codebase", "slip.zip", _zip({"../../evil.py": "x"}), "unsafe file paths"),
    ],
)
def test_upload_rejects_bad_files(
    signed_in: TestClient, kind: str, filename: str, content: bytes, message: str
):
    response = _upload(signed_in, kind, filename, content)
    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert signed_in.get(SOURCES).json() == []


def test_upload_rejects_oversized_file(signed_in: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sources_routes, "_MB", 4)  # shrinks the 25 MB limit to 100 bytes
    response = _upload(signed_in, "document", "big.txt", b"x" * 101)
    assert response.status_code == 413


def test_users_cannot_see_or_delete_each_others_sources(signed_in: TestClient, client: TestClient):
    source_id = _upload(signed_in, "document", "private.md", b"secret").json()["id"]

    client.cookies.clear()
    client.post(
        "/api/v1/auth/signup", json={"email": "other@example.com", "password": "Str0ng!pass"}
    )
    assert client.get(SOURCES).json() == []
    assert client.delete(f"{SOURCES}/{source_id}").status_code == 404


def test_delete_removes_the_stored_file(signed_in: TestClient):
    source_id = _upload(signed_in, "document", "temp.md", b"temp").json()["id"]
    stored = next(Path(sources_routes.get_settings().storage_dir).rglob(f"{source_id}*"))

    assert signed_in.delete(f"{SOURCES}/{source_id}").status_code == 204
    assert not stored.exists()
    assert signed_in.get(SOURCES).json() == []


def test_connect_github_verifies_then_stores_encrypted_token(
    signed_in: TestClient, monkeypatch: pytest.MonkeyPatch
):
    calls = []

    async def fake_verify(token: str, owner: str, repo: str) -> None:
        calls.append((token, owner, repo))

    monkeypatch.setattr(sources_routes, "verify_repository_access", fake_verify)
    captured = {}
    real_encrypt = sources_routes.encrypt_secret
    monkeypatch.setattr(
        sources_routes,
        "encrypt_secret",
        lambda value: captured.setdefault("encrypted", real_encrypt(value)),
    )

    response = signed_in.post(
        GITHUB, json={"repository": "https://github.com/octocat/Hello-World.git", "token": TOKEN}
    )

    assert response.status_code == 201
    assert response.json()["name"] == "octocat/Hello-World"
    assert "token" not in response.text.replace("encrypted_token", "")
    assert calls == [(TOKEN, "octocat", "Hello-World")]
    assert captured["encrypted"] != TOKEN
    assert decrypt_secret(captured["encrypted"]) == TOKEN

    again = signed_in.post(GITHUB, json={"repository": "octocat/Hello-World", "token": TOKEN})
    assert again.status_code == 409


def test_connect_github_reports_mcp_failure(signed_in: TestClient, monkeypatch: pytest.MonkeyPatch):
    async def failing_verify(token: str, owner: str, repo: str) -> None:
        raise GitHubMCPError("GitHub could not open octocat/private with this token.")

    monkeypatch.setattr(sources_routes, "verify_repository_access", failing_verify)
    response = signed_in.post(GITHUB, json={"repository": "octocat/private", "token": TOKEN})

    assert response.status_code == 400
    assert "could not open" in response.json()["detail"]
    assert signed_in.get(SOURCES).json() == []


@pytest.mark.parametrize("repository", ["just-a-name", "owner/", "/repo", "owner/re po", "a/b/c"])
def test_connect_github_rejects_malformed_repository(signed_in: TestClient, repository: str):
    response = signed_in.post(GITHUB, json={"repository": repository, "token": TOKEN})
    assert response.status_code == 422
