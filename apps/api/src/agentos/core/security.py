import base64
import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet

from agentos.core.config import get_settings

SESSION_COOKIE = "agentlens_session"
_JWT_ALGORITHM = "HS256"

# Mirrored in apps/web/src/lib/validation.ts; change both together.
PASSWORD_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("at least 8 characters", re.compile(r".{8,}", re.DOTALL)),
    ("a lowercase letter", re.compile(r"[a-z]")),
    ("an uppercase letter", re.compile(r"[A-Z]")),
    ("a number", re.compile(r"\d")),
    ("a special character", re.compile(r"[^A-Za-z0-9]")),
]

_hasher = PasswordHasher()
# Verified against when the email is unknown, so login takes the same time either way.
_DUMMY_HASH = _hasher.hash("agentlens-dummy-password")


def password_problems(password: str) -> list[str]:
    """Return the rules `password` fails; empty when it is acceptable."""
    return [label for label, pattern in PASSWORD_RULES if not pattern.search(password)]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def create_session_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    return jwt.encode({"sub": str(user_id), "exp": expires}, settings.secret_key, _JWT_ALGORITHM)


def read_session_token(token: str) -> uuid.UUID | None:
    """Return the user id for a valid, unexpired token, else None."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[_JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


def _fernet() -> Fernet:
    digest = hashlib.sha256(get_settings().secret_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()
