"""POST /ask: answers a question from your documents, with citations, streamed live."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.answering import answer_events
from app.config import settings
from app.db import get_session
from app.llm import LLMNotConfiguredError, get_llm
from app.retrieval import retrieve
from app.schemas import AskRequest

router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("")
def ask(request: AskRequest, session: Session = Depends(get_session)) -> StreamingResponse:
    """Streams an answer as Server-Sent Events: sources, then tokens, then done.

    Try it live in a terminal (in /docs the whole stream appears at once at the end):
      curl -N -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \\
        -d '{"question": "What is this document about?"}'
    """
    try:
        llm = get_llm()
    except LLMNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    # Retrieval happens here, before streaming starts, so the database session
    # isn't needed while the answer streams.
    chunks = retrieve(session, request.question, settings.answer_top_k, request.document_ids)
    relevant = [chunk for chunk in chunks if chunk.score >= settings.min_relevance]

    return StreamingResponse(
        answer_events(request.question, relevant, llm),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )