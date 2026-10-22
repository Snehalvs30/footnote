"""Tests for app/chunking.py.

Run with: uv run pytest
"""

import pytest

from app.chunking import TextChunk, chunk_pages, split_text


def test_empty_text_gives_no_chunks():
    assert split_text("") == []


def test_short_text_is_one_chunk():
    assert split_text("Hello, world!") == ["Hello, world!"]


def test_long_text_is_split_into_chunks_within_the_limit():
    chunks = split_text("word " * 1000, max_chars=1000, overlap=200)

    # Test the rule, not the exact output: several chunks, none too long.
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 1000


def test_consecutive_chunks_overlap():
    # Distinct words (word0 word1 ...), so a repeated passage is detectable.
    text = " ".join(f"word{i}" for i in range(1000))
    chunks = split_text(text, max_chars=1000, overlap=200)

    # The end of each chunk reappears in the next one.
    for previous, current in zip(chunks, chunks[1:]):
        assert previous[-50:] in current


def test_chunk_pages_keeps_page_numbers():
    chunks = chunk_pages(["", "Hello", "World"])

    # The empty first page is skipped without shifting the page numbers.
    assert chunks == [
        TextChunk(page_number=2, content="Hello"),
        TextChunk(page_number=3, content="World"),
    ]


def test_overlap_too_large_raises_error():
    with pytest.raises(ValueError, match="overlap"):
        split_text("a" * 1000, max_chars=1000, overlap=600)