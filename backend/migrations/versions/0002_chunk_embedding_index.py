"""Vector index on chunk embeddings.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23

Without an index, every search compares the question with every chunk (exact,
but slower as data grows). HNSW is an approximate nearest-neighbour index: it
finds the closest vectors in milliseconds even across millions of chunks, at
the cost of very occasionally missing a match.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # vector_cosine_ops: the index is built for cosine distance, which is what we search with.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_embedding_hnsw", table_name="chunks")