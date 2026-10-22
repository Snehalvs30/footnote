"""Semantic search: find the chunks whose meaning is closest to a question."""

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.retrieval import retrieve
from app.schemas import SearchRequest, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
def search(request: SearchRequest, session: Session = Depends(get_session)) -> list[SearchResult]:
    """Returns the top_k chunks most similar in meaning to the query, best first."""
    chunks = retrieve(session, request.query, request.top_k, request.document_ids)
    # asdict() turns a dataclass into a dict; ** spreads it into keyword arguments.
    return [SearchResult(**asdict(chunk)) for chunk in chunks]