from fastapi import APIRouter, Depends

from agentos.api.deps import get_current_user
from agentos.api.routes import auth, health, runs, sources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Everything below requires a signed-in user.
signed_in = [Depends(get_current_user)]
api_router.include_router(runs.router, prefix="/runs", tags=["runs"], dependencies=signed_in)
api_router.include_router(
    sources.router, prefix="/sources", tags=["sources"], dependencies=signed_in
)
