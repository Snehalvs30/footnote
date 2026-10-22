"""Splits page text into overlapping chunks: the passages we'll search and cite.

Why chunks? An LLM can't read a whole book per question, and search works better
on focused passages. Why overlap? So a sentence cut at a chunk boundary still
appears whole in the next chunk.

Chunks never cross page boundaries, so every chunk has one exact page number
to cite.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """frozen=True makes it immutable, like a Java record."""

    page_number: int
    content: str


def chunk_pages(pages: list[str], max_chars: int = 1000, overlap: int = 200) -> list[TextChunk]:
    """Chunks each page separately. pages[0] is page 1."""
    chunks: list[TextChunk] = []
    for page_number, page_text in enumerate(pages, start=1):
        for piece in split_text(page_text, max_chars, overlap):
            chunks.append(TextChunk(page_number=page_number, content=piece))
    return chunks


def split_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Splits text into pieces of at most max_chars, each overlapping the previous one.

    Prefers to cut at a paragraph break, then a sentence end, then a space, so
    chunks don't end mid-word unless there's no other choice.
    """
    if overlap >= max_chars // 2:
        raise ValueError("overlap must be less than half of max_chars")

    text = normalize(text)
    if not text:
        return []

    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            # Look for a natural break in the second half of the window.
            for separator in ("\n\n", ". ", " "):
                cut = text.rfind(separator, start + max_chars // 2, end)
                if cut != -1:
                    end = cut + len(separator)
                    break
        piece = text[start:end].strip()
        if piece:
            pieces.append(piece)
        if end >= len(text):
            break
        start = end - overlap  # step back to create the overlap
    return pieces


def normalize(text: str) -> str:
    """Tidies whitespace that PDF extraction leaves behind."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)        # runs of spaces/tabs -> one space
    text = re.sub(r"\n{3,}", "\n\n", text)     # 3+ newlines -> one paragraph break
    return text.strip()