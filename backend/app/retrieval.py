"""Finds the chunks most similar in meaning to a question.

Shared by POST /search (returns the passages) and POST /ask (answers from them).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings import get_embedder
from app.models import Chunk, Document, DocumentStatus


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    content: str
    score: float  # 1.0 = identical meaning, 0 = unrelated


def retrieve(
    session: Session,
    query: str,
    top_k: int,
    owner_id: uuid.UUID,
    document_ids: list[uuid.UUID] | None = None,
) -> list[RetrievedChunk]:
    """The top_k chunks closest in meaning to the query, best first.

    Only searches documents belonging to owner_id: one user's question can never
    surface another user's passages.
    """
    query_vector = get_embedder().embed_query(query)

    # Cosine distance: 0 = same direction (same meaning), up to 2 = opposite.
    # pgvector computes it in the database: the `<=>` operator in SQL.
    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")

    statement = (
        select(Chunk, Document.filename, distance)
        .join(Document, Chunk.document_id == Document.id)
        .where(
            Document.owner_id == owner_id,
            Chunk.embedding.is_not(None),
            Document.status == DocumentStatus.READY,
        )
        .order_by(distance)
        .limit(top_k)
    )
    if document_ids:
        statement = statement.where(Chunk.document_id.in_(document_ids))

    return [
        RetrievedChunk(
            document_id=chunk.document_id,
            filename=filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            score=round(1 - dist, 4),  # turn distance into a 0..1 similarity
        )
        for chunk, filename, dist in session.execute(statement).all()
    ]