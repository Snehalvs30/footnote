"""Semantic search: find the chunks whose meaning is closest to a question."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.embeddings import get_embedder
from app.models import Chunk, Document, DocumentStatus
from app.schemas import SearchRequest, SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
def search(request: SearchRequest, session: Session = Depends(get_session)) -> list[SearchResult]:
    """Returns the top_k chunks most similar in meaning to the query, best first."""
    query_vector = get_embedder().embed_query(request.query)

    # Cosine distance: 0 = same direction (same meaning), up to 2 = opposite.
    # pgvector computes it in the database: the `<=>` operator in SQL.
    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")

    statement = (
        select(Chunk, Document.filename, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.embedding.is_not(None), Document.status == DocumentStatus.READY)
        .order_by(distance)
        .limit(request.top_k)
    )
    if request.document_ids:
        statement = statement.where(Chunk.document_id.in_(request.document_ids))

    return [
        SearchResult(
            document_id=chunk.document_id,
            filename=filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=round(1 - dist, 4),   # turn distance into a 0..1 similarity
        )
        for chunk, filename, dist in session.execute(statement).all()
    ]