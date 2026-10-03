"""Turn an uploaded document or codebase archive into chunks with source metadata."""

import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from pypdf import PdfReader

_CHUNK_SIZE = 1500
_CHUNK_OVERLAP = 150
_MAX_FILE_BYTES = 1024 * 1024  # larger files are almost always generated or data
_MAX_CHUNKS_PER_SOURCE = 20_000

_LANGUAGES: dict[str, tuple[str, Language | None]] = {
    ".py": ("python", Language.PYTHON),
    ".js": ("javascript", Language.JS),
    ".jsx": ("javascript", Language.JS),
    ".mjs": ("javascript", Language.JS),
    ".ts": ("typescript", Language.TS),
    ".tsx": ("typescript", Language.TS),
    ".java": ("java", Language.JAVA),
    ".kt": ("kotlin", Language.KOTLIN),
    ".go": ("go", Language.GO),
    ".rs": ("rust", Language.RUST),
    ".rb": ("ruby", Language.RUBY),
    ".php": ("php", Language.PHP),
    ".cs": ("csharp", Language.CSHARP),
    ".c": ("c", Language.C),
    ".h": ("c", Language.C),
    ".cpp": ("cpp", Language.CPP),
    ".hpp": ("cpp", Language.CPP),
    ".swift": ("swift", Language.SWIFT),
    ".scala": ("scala", Language.SCALA),
    ".md": ("markdown", Language.MARKDOWN),
    ".markdown": ("markdown", Language.MARKDOWN),
    ".rst": ("rst", Language.RST),
    ".html": ("html", Language.HTML),
    ".sol": ("solidity", Language.SOL),
    ".txt": ("text", None),
    ".json": ("json", None),
    ".yaml": ("yaml", None),
    ".yml": ("yaml", None),
    ".toml": ("toml", None),
    ".ini": ("ini", None),
    ".cfg": ("ini", None),
    ".sql": ("sql", None),
    ".sh": ("shell", None),
    ".css": ("css", None),
    ".scss": ("css", None),
    ".vue": ("vue", None),
    ".svelte": ("svelte", None),
    ".graphql": ("graphql", None),
    ".proto": ("protobuf", None),
    ".tf": ("terraform", None),
    ".gradle": ("gradle", None),
    ".xml": ("xml", None),
}
_NAMED_FILES = {"dockerfile": "dockerfile", "makefile": "makefile"}
_SKIPPED_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "out",
    ".next",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
}
_SKIPPED_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "uv.lock",
    "poetry.lock",
    "cargo.lock",
    "composer.lock",
    "gemfile.lock",
}


@dataclass
class Chunk:
    text: str
    path: str  # file path inside the source ("" for a single uploaded document)
    language: str
    start_line: int
    end_line: int
    page: int | None = None


def _language_of(path: PurePosixPath) -> tuple[str, Language | None] | None:
    name = path.name.lower()
    if name in _NAMED_FILES:
        return _NAMED_FILES[name], None
    return _LANGUAGES.get(path.suffix.lower())


def _splitter(language: Language | None) -> RecursiveCharacterTextSplitter:
    options = {"chunk_size": _CHUNK_SIZE, "chunk_overlap": _CHUNK_OVERLAP, "add_start_index": True}
    if language is None:
        return RecursiveCharacterTextSplitter(**options)
    return RecursiveCharacterTextSplitter.from_language(language, **options)


def _split(
    text: str, path: str, language: tuple[str, Language | None], page: int | None = None
) -> Iterator[Chunk]:
    name, splitter_language = language
    for document in _splitter(splitter_language).create_documents([text]):
        if not document.page_content.strip():
            continue
        start_line = text.count("\n", 0, document.metadata["start_index"]) + 1
        yield Chunk(
            text=document.page_content,
            path=path,
            language=name,
            start_line=start_line,
            end_line=start_line + document.page_content.count("\n"),
            page=page,
        )


def _document_chunks(path: Path) -> Iterator[Chunk]:
    if path.suffix.lower() == ".pdf":
        for number, page in enumerate(PdfReader(path).pages, start=1):
            yield from _split(page.extract_text() or "", "", ("pdf", None), page=number)
    else:
        language = _language_of(PurePosixPath(path.name)) or ("text", None)
        yield from _split(path.read_text(encoding="utf-8", errors="replace"), "", language)


def _codebase_chunks(path: Path) -> Iterator[Chunk]:
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            file_path = PurePosixPath(entry.filename.replace("\\", "/"))
            if entry.is_dir() or entry.file_size > _MAX_FILE_BYTES:
                continue
            if _SKIPPED_DIRS.intersection(file_path.parts) or file_path.name.lower() in (
                _SKIPPED_FILES
            ):
                continue
            language = _language_of(file_path)
            if language is None:
                continue
            try:
                text = archive.read(entry).decode("utf-8")
            except UnicodeDecodeError:
                continue  # binary file with a text-like extension
            yield from _split(text, str(file_path), language)


def chunk_source(kind: str, path: Path) -> list[Chunk]:
    """Chunks for an uploaded source. `kind` is "document" or "codebase"."""
    chunks = _codebase_chunks(path) if kind == "codebase" else _document_chunks(path)
    result = []
    for chunk in chunks:
        result.append(chunk)
        if len(result) >= _MAX_CHUNKS_PER_SOURCE:
            break
    return result
