import asyncio
import re
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from fastapi import APIRouter, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from agentos.api.deps import CurrentUser, SessionDep
from agentos.core.config import get_settings
from agentos.core.security import encrypt_secret
from agentos.db.models import Source
from agentos.mcp.github import GitHubMCPError, verify_repository_access
from agentos.rag import store
from agentos.rag.ingest import schedule_ingestion

router = APIRouter()

DOCUMENT_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt", ".rst"}
_MB = 1024 * 1024
# Guards against zip bombs: limits on what an archive may expand to.
_MAX_ZIP_ENTRIES = 50_000
_MAX_ZIP_UNCOMPRESSED_BYTES = 1024 * _MB

# owner/repo, optionally pasted as a github.com URL.
_REPOSITORY_RE = re.compile(
    r"^(?:https?://github\.com/)?"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100}?)"
    r"(?:\.git)?/?$"
)


class SourceResponse(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    size_bytes: int | None
    status: str
    error: str | None
    chunk_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class GitHubConnectRequest(BaseModel):
    repository: str
    token: str = Field(min_length=20, max_length=255, pattern=r"^\S+$")

    @field_validator("repository")
    @classmethod
    def _check_repository(cls, value: str) -> str:
        match = _REPOSITORY_RE.match(value.strip())
        if not match:
            raise ValueError("Enter a repository as owner/name or a github.com URL")
        return f"{match['owner']}/{match['repo']}"


async def _save_upload(file: UploadFile, destination: Path, max_bytes: int) -> int:
    """Stream the upload to disk, stopping as soon as it exceeds `max_bytes`."""
    size = 0
    with destination.open("wb") as out:
        while chunk := await file.read(_MB):
            size += len(chunk)
            if size > max_bytes:
                raise HTTPException(
                    status.HTTP_413_CONTENT_TOO_LARGE,
                    f"File is larger than the {max_bytes // _MB} MB limit",
                )
            out.write(chunk)
    if size == 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "File is empty")
    return size


def _check_document(path: Path) -> None:
    if path.suffix == ".pdf":
        with path.open("rb") as f:
            if f.read(5) != b"%PDF-":
                raise ValueError("File is not a valid PDF")


def _check_codebase_zip(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        raise ValueError("File is not a valid zip archive")
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > _MAX_ZIP_ENTRIES:
            raise ValueError("Archive contains too many files")
        if sum(entry.file_size for entry in entries) > _MAX_ZIP_UNCOMPRESSED_BYTES:
            raise ValueError("Archive is too large when extracted")
        for entry in entries:
            name = PurePosixPath(entry.filename.replace("\\", "/"))
            if name.is_absolute() or ".." in name.parts:
                raise ValueError("Archive contains unsafe file paths")


@router.get("")
async def list_sources(user: CurrentUser, session: SessionDep) -> list[SourceResponse]:
    sources = await session.scalars(
        select(Source).where(Source.user_id == user.id).order_by(Source.created_at.desc())
    )
    return [SourceResponse.model_validate(source) for source in sources]


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_source(
    kind: Annotated[Literal["document", "codebase"], Form()],
    file: UploadFile,
    user: CurrentUser,
    session: SessionDep,
) -> SourceResponse:
    settings = get_settings()
    # Only the base name is kept for display; the file on disk is named by its id.
    name = Path(file.filename or "").name[:255]
    suffix = Path(name).suffix.lower()

    if kind == "document":
        if suffix not in DOCUMENT_EXTENSIONS:
            allowed = ", ".join(sorted(DOCUMENT_EXTENSIONS))
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Documents must be one of: {allowed}"
            )
        max_bytes, check = settings.max_document_mb * _MB, _check_document
    else:
        if suffix != ".zip":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "A codebase must be uploaded as a .zip file"
            )
        max_bytes, check = settings.max_codebase_mb * _MB, _check_codebase_zip

    source_id = uuid.uuid4()
    directory = Path(settings.storage_dir) / str(user.id)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{source_id}{suffix}"

    try:
        size = await _save_upload(file, destination, max_bytes)
        try:
            await asyncio.to_thread(check, destination)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        source = Source(
            id=source_id,
            user_id=user.id,
            kind=kind,
            name=name,
            size_bytes=size,
            storage_path=str(destination),
        )
        session.add(source)
        await session.commit()
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    schedule_ingestion(source.id)
    return SourceResponse.model_validate(source)


@router.post("/github", status_code=status.HTTP_201_CREATED)
async def connect_github(
    body: GitHubConnectRequest, user: CurrentUser, session: SessionDep
) -> SourceResponse:
    already_connected = await session.scalar(
        select(Source).where(
            Source.user_id == user.id, Source.kind == "github", Source.name == body.repository
        )
    )
    if already_connected:
        raise HTTPException(status.HTTP_409_CONFLICT, "This repository is already connected")

    owner, repo = body.repository.split("/")
    try:
        await verify_repository_access(body.token, owner, repo)
    except GitHubMCPError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    source = Source(
        user_id=user.id,
        kind="github",
        name=body.repository,
        encrypted_token=encrypt_secret(body.token),
        status="ready",
    )
    session.add(source)
    await session.commit()
    return SourceResponse.model_validate(source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    source = await session.get(Source, source_id)
    if source is None or source.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    if source.storage_path:
        Path(source.storage_path).unlink(missing_ok=True)
    await session.delete(source)
    await session.commit()
    if source.kind != "github":
        await asyncio.to_thread(store.delete_source, str(source_id))


@router.post("/{source_id}/reindex")
async def reindex_source(
    source_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> SourceResponse:
    """Index an upload again, e.g. after a failure."""
    source = await session.get(Source, source_id)
    if source is None or source.user_id != user.id or source.kind == "github":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Source not found")
    if source.status != "indexing":
        source.status, source.error = "pending", None
        await session.commit()
        schedule_ingestion(source.id)
    return SourceResponse.model_validate(source)
