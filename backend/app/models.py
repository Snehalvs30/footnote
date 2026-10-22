"""Database tables, as SQLAlchemy models (like JPA @Entity classes).

`Mapped[...]` type hints tell SQLAlchemy each column's Python type, and whether
it can be NULL: `Mapped[int | None]` is nullable, `Mapped[int]` is NOT NULL.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# The embedding model (BAAI/bge-small-en-v1.5) produces 384 numbers per text.
EMBEDDING_DIMENSIONS = 384


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Parent class for all models. Alembic reads Base.metadata to know the tables."""


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Stored lowercase, so "Alice@x.com" and "alice@x.com" are the same account.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    # Never the password itself: an Argon2 hash, which can't be reversed.
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )


class DocumentStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PROCESSING)
    page_count: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(1000))
    # Set in Python (not only by the database), so the value is available right after commit.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )

    # One document has many chunks. Deleting a document deletes its chunks too.
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Chunk.chunk_index"
    )


class Chunk(Base):
    """A passage of a document: the unit we search over and cite."""

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int]          # 0, 1, 2... order within the document
    page_number: Mapped[int]          # 1-based, for citations like "page 4"
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS))

    document: Mapped[Document] = relationship(back_populates="chunks")