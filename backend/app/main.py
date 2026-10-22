"""Footnote API entry point.

Run locally:  uv run fastapi dev app/main.py
API docs:     http://127.0.0.1:8000/docs

Every API route lives under /api. In production the same app also serves the
built React frontend from "/", so the browser talks to a single origin.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.embeddings import get_embedder
from app.routers import ask, auth, documents, search


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once at startup (before `yield`) and once at shutdown (after it).

    Loading the embedding model here means the first upload or search isn't slow.
    """
    get_embedder()
    yield


app = FastAPI(
    title="Footnote API",
    description="Ask questions about your documents and get answers with citations.",
    version="0.1.0",
    lifespan=lifespan,
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(documents.router)
api.include_router(search.router)
api.include_router(ask.router)


@api.get("/health", tags=["health"])
def health(session: Session = Depends(get_session)) -> dict[str, str | None]:
    """Checks the API can reach PostgreSQL, and that pgvector is available.

    The load balancer calls this to decide whether the container is healthy.
    """
    session.execute(text("SELECT 1"))
    pgvector_version = session.execute(
        text("SELECT default_version FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    return {"status": "ok", "database": "connected", "pgvector": pgvector_version}


app.include_router(api)

# Registered last, so /api/... routes always match first.
if settings.static_dir:
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")