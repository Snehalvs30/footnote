"""Document endpoints: upload, list, view, inspect chunks, delete.

An APIRouter groups related endpoints, like a Spring @RestController class.
Every endpoint requires a signed-in user and only ever touches that user's documents.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chunking import chunk_pages
from app.config import settings
from app.db import get_session
from app.embeddings import get_embedder
from app.extraction import ExtractionError, extract_pages
from app.models import Chunk, Document, DocumentStatus, User
from app.schemas import ChunkOut, DocumentOut
from app.security import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".txt": "text", ".md": "text"}


@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    """Uploads a PDF, .txt or .md file, extracts its text, splits it into chunks,
    and computes an embedding for each chunk so it can be searched.

    Returns 201 even if the file couldn't be processed: the document is saved with
    status "failed" and an error message, so the user can see what went wrong.
    """
    kind = _file_kind(file.filename)
    if kind is None:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only .pdf, .txt and .md files are supported")

    # Read one byte more than the limit: if we get it, the file is too big.
    limit = settings.max_upload_bytes
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, f"Files must be at most {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The file is empty")

    document = Document(
        owner_id=user.id,
        filename=file.filename or "untitled",
        content_type=file.content_type or "application/octet-stream",
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
    return _to_out(document, len(document.chunks))


@router.get("")
def list_documents(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DocumentOut]:
    """Your documents, newest first, with their chunk counts."""
    chunk_counts = (
        select(Chunk.document_id, func.count().label("n")).group_by(Chunk.document_id).subquery()
    )
    rows = session.execute(
        select(Document, func.coalesce(chunk_counts.c.n, 0))
        .outerjoin(chunk_counts, chunk_counts.c.document_id == Document.id)
        .where(Document.owner_id == user.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_to_out(document, count) for document, count in rows]


@router.get("/{document_id}")
def get_document(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentOut:
    document = _get_or_404(session, document_id, user)
    count = session.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id))
    return _to_out(document, count or 0)


@router.get("/{document_id}/chunks")
def list_chunks(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChunkOut]:
    """Shows how a document was split. Handy for checking the chunking works well."""
    document = _get_or_404(session, document_id, user)
    return [
        ChunkOut(chunk_index=c.chunk_index, page_number=c.page_number, content=c.content)
        for c in document.chunks
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Response:
    document = _get_or_404(session, document_id, user)
    session.delete(document)  # its chunks are deleted too (cascade)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- helpers ----------------------------------------------------------------

def _file_kind(filename: str | None) -> str | None:
    """'pdf' or 'text' based on the file extension, or None if unsupported."""
    if not filename or "." not in filename:
        return None
    extension = filename[filename.rindex("."):].lower()
    return SUPPORTED_EXTENSIONS.get(extension)


def _get_or_404(session: Session, document_id: uuid.UUID, user: User) -> Document:
    """Someone else's document gets the same 404 as a missing one, so its existence isn't revealed."""
    document = session.get(Document, document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return document


def _to_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        status=document.status,
        page_count=document.page_count,
        chunk_count=chunk_count,
        error=document.error,
        created_at=document.created_at,
    )