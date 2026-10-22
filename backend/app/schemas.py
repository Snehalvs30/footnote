"""API request/response shapes (Pydantic models).

Like the Java records you returned from Ledgerline's controllers: the API never
exposes database models directly, so the tables can change without breaking clients.
Field(...) adds validation, like Bean Validation annotations (@Size, @Min...).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str
    page_count: int | None
    chunk_count: int
    error: str | None
    created_at: datetime


class ChunkOut(BaseModel):
    chunk_index: int
    page_number: int
    content: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    # Optional: search only these documents. Omit to search all of them.
    document_ids: list[uuid.UUID] | None = None


class SearchResult(BaseModel):
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    content: str
    # 1.0 = identical meaning, 0 = unrelated. Useful for spotting weak matches.
    score: float


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # Optional: answer only from these documents. Omit to use all of them.
    document_ids: list[uuid.UUID] | None = None