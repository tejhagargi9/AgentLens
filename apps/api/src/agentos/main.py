from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentos import __version__
from agentos.api.router import api_router
from agentos.core.config import get_settings
from agentos.db.session import create_tables
from agentos.rag.ingest import resume_unfinished


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await create_tables()
    await resume_unfinished()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="AgentLens API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # The session cookie is sent cross-origin from the web app.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
