from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-only-secret-change-me-before-deploying"


class Settings(BaseSettings):
    """Runtime configuration, read from AGENTOS_* env vars or apps/api/.env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGENTOS_", extra="ignore")

    environment: str = "development"
    cors_origins: list[str] = ["http://localhost:3000"]

    # SQLite keeps local development zero-setup; point this at Postgres for anything shared.
    database_url: str = "sqlite+aiosqlite:///./agentos.db"
    redis_url: str = "redis://localhost:6379/0"

    # LLM, as "<provider>:<model>" understood by LangChain's init_chat_model.
    llm_model: str = "google_genai:gemini-3.6-flash"
    llm_api_key: str = ""

    # Vector database. With no URL, Qdrant runs embedded and stores data in `qdrant_path`
    # (single process only). Set a URL for a Qdrant server or Qdrant Cloud.
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_path: str = "storage/qdrant"
    qdrant_collection: str = "agentlens_chunks"

    # Retrieval models run locally through fastembed (downloaded on first use).
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    sparse_model: str = "Qdrant/bm25"
    reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    model_cache_dir: str = "~/.cache/agentlens/models"
    retrieval_candidates: int = 24  # fetched per search, and reranked in total
    retrieval_top_k: int = 8  # chunks handed to the agents

    # Send indexing jobs to a Celery worker instead of running them inside the API.
    # Needs Redis and a Qdrant server (embedded Qdrant cannot be shared between processes).
    use_celery: bool = False

    # Per repository in one run. A turn is one model call, which may request several tools;
    # turns are what count against the LLM provider's request quota.
    github_max_turns: int = 3
    github_max_tool_calls: int = 10

    # Signs session tokens and derives the key that encrypts stored GitHub tokens.
    secret_key: str = DEV_SECRET_KEY
    session_ttl_hours: int = 24 * 7

    storage_dir: str = "storage"
    max_document_mb: int = 25
    max_codebase_mb: int = 100

    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"

    @model_validator(mode="after")
    def _require_real_secret_outside_dev(self) -> "Settings":
        # A blank value (e.g. an unfilled line copied from .env.example) means "not set".
        self.secret_key = self.secret_key or DEV_SECRET_KEY
        if self.environment != "development" and self.secret_key == DEV_SECRET_KEY:
            raise ValueError("AGENTOS_SECRET_KEY must be set outside development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
