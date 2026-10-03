import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agentos.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Stored lowercased, so the unique constraint is case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Source(Base):
    """Something a user has given AgentLens to analyse.

    kind = "document" | "codebase": an uploaded file at `storage_path`.
    kind = "github": a repository (`name` is "owner/repo") reached through the
    GitHub MCP server using `encrypted_token`.
    """

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int | None] = mapped_column(default=None)
    storage_path: Mapped[str | None] = mapped_column(String(500), default=None)
    encrypted_token: Mapped[str | None] = mapped_column(Text, default=None)
    # Indexing state for uploads: pending -> indexing -> ready | failed.
    # GitHub sources are read live through MCP, so they are always "ready".
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    error: Mapped[str | None] = mapped_column(String(500), default=None)
    chunk_count: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
