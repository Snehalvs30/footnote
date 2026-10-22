"""Turns an uploaded file into a stored, searchable document.

Shared by the upload endpoint and the evaluation script, so both go through
exactly the same extract -> chunk -> embed -> store pipeline.
"""

import uuid

from sqlalchemy.orm import Session

from app.chunking import chunk_pages
from app.embeddings import get_embedder
from app.extraction import ExtractionError, extract_pages
from app.models import Chunk, Document, DocumentStatus


def ingest(
    session: Session,
    owner_id: uuid.UUID,
    filename: str,
    content_type: str,
    data: bytes,
    kind: str,
) -> Document:
    """Extracts, chunks and embeds a file, and commits it.

    Never raises for a bad file: the document is saved with status "failed" and
    an error message, so the user can see what went wrong.
    """
    document = Document(
        owner_id=owner_id,
        filename=filename,
        content_type=content_type,
        status=DocumentStatus.PROCESSING,
    )
    session.add(document)

    try:
        pages = extract_pages(data, kind)
        text_chunks = chunk_pages(pages)
        if not text_chunks:
            raise ExtractionError("No text found. Scanned PDFs (images of text) aren't supported yet.")
        # One call for all chunks: the model batches them, which is much faster.
        vectors = get_embedder().embed_passages([c.content for c in text_chunks])
        document.page_count = len(pages)
        document.chunks = [
            Chunk(chunk_index=i, page_number=c.page_number, content=c.content, embedding=vector)
            for i, (c, vector) in enumerate(zip(text_chunks, vectors, strict=True))
        ]
        document.status = DocumentStatus.READY
    except ExtractionError as exc:
        document.status = DocumentStatus.FAILED
        document.error = str(exc)

    session.commit()
    return document