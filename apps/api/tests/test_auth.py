import pytest
from fastapi.testclient import TestClient

from agentos.core.security import SESSION_COOKIE, password_problems
from tests.conftest import VALID_PASSWORD

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("Sh0rt!a", "at least 8 characters"),
        ("NOLOWER1!", "a lowercase letter"),
        ("noupper1!", "an uppercase letter"),
        ("NoNumber!", "a number"),
        ("NoSpecial1", "a special character"),
    ],
)
def test_password_rules(password: str, problem: str):
    assert password_problems(password) == [problem]
    assert password_problems(VALID_PASSWORD) == []


def test_signup_signs_the_user_in(client: TestClient):
    response = client.post(SIGNUP, json={"email": "new@example.com", "password": VALID_PASSWORD})
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get(ME).json()["email"] == "new@example.com"


def test_signup_rejects_weak_password(client: TestClient):
    response = client.post(SIGNUP, json={"email": "weak@example.com", "password": "password"})
    assert response.status_code == 422
    message = response.json()["detail"][0]["msg"]
    assert "an uppercase letter" in message
    assert "a number" in message
    assert "a special character" in message


@pytest.mark.parametrize(
    "email", ["not-an-email", "missing@tld", "@example.com", "a b@example.com"]
)
def test_signup_rejects_invalid_email(client: TestClient, email: str):
    response = client.post(SIGNUP, json={"email": email, "password": VALID_PASSWORD})
    assert response.status_code == 422


def test_email_must_be_unique_ignoring_case(client: TestClient):
    first = client.post(SIGNUP, json={"email": "dupe@example.com", "password": VALID_PASSWORD})
    assert first.status_code == 201
    second = client.post(SIGNUP, json={"email": "Dupe@Example.com", "password": VALID_PASSWORD})
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"]


def test_login_and_logout(client: TestClient):
    client.post(SIGNUP, json={"email": "login@example.com", "password": VALID_PASSWORD})
    client.cookies.clear()
    assert client.get(ME).status_code == 401

    response = client.post(LOGIN, json={"email": "LOGIN@example.com", "password": VALID_PASSWORD})
    assert response.status_code == 200
    assert client.get(ME).status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get(ME).status_code == 401


def test_login_failures_are_indistinguishable(client: TestClient):
    client.post(SIGNUP, json={"email": "known@example.com", "password": VALID_PASSWORD})
    client.cookies.clear()

    wrong_password = client.post(
        LOGIN, json={"email": "known@example.com", "password": "Wr0ng!pass"}
    )
    unknown_email = client.post(
        LOGIN, json={"email": "nobody@example.com", "password": "Wr0ng!pass"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_tampered_session_cookie_is_rejected(client: TestClient):
    client.cookies.set(SESSION_COOKIE, "not.a.token")
    assert client.get(ME).status_code == 401
