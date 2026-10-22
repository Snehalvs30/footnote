"""Tests for app/answering.py, using fake LLMs: free, instant, and the same every run."""

import uuid

from app.answering import NOT_FOUND, answer_events, build_prompt
from app.retrieval import RetrievedChunk


class FakeLLM:
    """Pretends to be an LLM: always streams the same two pieces of text."""

    def stream(self, system, prompt):
        yield "Hello "
        yield "world [1]"


class ExplodingLLM:
    """Fails if anyone calls it. Used to prove the LLM is (or isn't) called."""

    def stream(self, system, prompt):
        raise RuntimeError("The LLM should not have been called")
        yield  # never reached; makes this a generator like a real stream


def make_chunk(content: str = "Some passage", page_number: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=uuid.uuid4(),
        filename="test.pdf",
        page_number=page_number,
        chunk_index=0,
        content=content,
        score=0.9,
    )


def test_events_come_in_order_sources_tokens_done():
    events = list(answer_events("question", [make_chunk()], FakeLLM()))

    assert events[0].startswith("event: sources")
    assert events[-1].startswith("event: done")
    # Everything in between is answer text.
    assert all(event.startswith("event: token") for event in events[1:-1])
    assert "world [1]" in "".join(events)


def test_no_chunks_answers_not_found_without_calling_the_llm():
    # ExplodingLLM would raise if called, so this passes only if the LLM is skipped.
    events = list(answer_events("question", [], ExplodingLLM()))

    assert NOT_FOUND in "".join(events)
    assert events[-1].startswith("event: done")


def test_llm_failure_ends_with_an_error_event():
    events = list(answer_events("question", [make_chunk()], ExplodingLLM()))

    assert events[0].startswith("event: sources")  # sources were still sent
    assert events[-1].startswith("event: error")


def test_prompt_numbers_each_source_with_its_page():
    prompt = build_prompt(
        "What is it?",
        [make_chunk("First passage", page_number=2), make_chunk("Second passage", page_number=5)],
    )

    assert "[1] test.pdf, page 2\nFirst passage" in prompt
    assert "[2] test.pdf, page 5\nSecond passage" in prompt
    assert prompt.endswith("Question: What is it?")