"""API request/response shapes (Pydantic models).

Like the Java records you returned from Ledgerline's controllers: the API never
exposes database models directly, so the tables can change without breaking clients.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


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