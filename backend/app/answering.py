"""Turns retrieved passages into a cited answer, streamed as Server-Sent Events.

The stream is a sequence of events the frontend reads as they arrive:
  sources  the numbered passages the answer may cite (sent first, so the UI can
           show them while the answer is still being written)
  token    a small piece of answer text
  done     the answer is complete
  error    something went wrong mid-answer
"""

import json
import logging
from collections.abc import Iterator

from app.llm import LLMClient
from app.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

NOT_FOUND = "I couldn't find this in your documents."

SYSTEM_PROMPT = f"""You answer questions using ONLY the numbered sources provided.

Rules:
- End every factual sentence with the number of the source it came from, like [1] or [2][3].
- If the sources don't contain the answer, reply exactly: "{NOT_FOUND}"
- Never use outside knowledge, and never cite a source number that wasn't provided.
- Be concise: a few sentences, or a short list when the question asks for several items."""


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Numbers each passage [1], [2]... so the model can cite them."""
    sources = "\n\n".join(
        f"[{number}] {chunk.filename}, page {chunk.page_number}\n{chunk.content}"
        for number, chunk in enumerate(chunks, start=1)
    )
    return f"Sources:\n\n{sources}\n\nQuestion: {question}"


def sse(event: str, data: object) -> str:
    """Formats one Server-Sent Event. JSON keeps newlines in the text from breaking the format."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def answer_events(question: str, chunks: list[RetrievedChunk], llm: LLMClient) -> Iterator[str]:
    """Yields the SSE stream for one question. A generator: each `yield` sends one event."""
    yield sse(
        "sources",
        [
            {
                "number": number,
                "document_id": str(chunk.document_id),
                "filename": chunk.filename,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "score": chunk.score,
                "excerpt": chunk.content[:300],
            }
            for number, chunk in enumerate(chunks, start=1)
        ],
    )

    # Nothing relevant was found: say so without calling the LLM. Cheaper, and
    # there's no chance of the model inventing an answer from nothing.
    if not chunks:
        yield sse("token", {"text": NOT_FOUND})
        yield sse("done", {})
        return

    try:
        for text in llm.stream(SYSTEM_PROMPT, build_prompt(question, chunks)):
            yield sse("token", {"text": text})
    except Exception:  # any provider failure (network, rate limit...) must end the stream cleanly
        logger.exception("Answer generation failed")
        yield sse("error", {"message": "The answer couldn't be generated. Please try again."})
        return

    yield sse("done", {})