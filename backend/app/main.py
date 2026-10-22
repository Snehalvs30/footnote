"""Footnote API entry point.

Run locally:  uv run fastapi dev app/main.py
API docs:     http://127.0.0.1:8000/docs
"""

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_session
from app.routers import documents

app = FastAPI(
    title="Footnote API",
    description="Ask questions about your documents and get answers with citations.",
    version="0.1.0",
)

app.include_router(documents.router)


@app.get("/health", tags=["health"])
def health(session: Session = Depends(get_session)) -> dict[str, str | None]:
    """Checks the API can reach PostgreSQL, and that pgvector is available.

    `Depends(get_session)` is FastAPI's dependency injection: like @Autowired,
    but per request. FastAPI calls get_session() and passes the result in.
    """
    session.execute(text("SELECT 1"))
    pgvector_version = session.execute(
        text("SELECT default_version FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    return {"status": "ok", "database": "connected", "pgvector": pgvector_version}