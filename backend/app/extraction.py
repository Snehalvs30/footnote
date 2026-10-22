"""Turns uploaded file bytes into text, one string per page."""

from io import BytesIO

from pypdf import PdfReader


class ExtractionError(Exception):
    """The file couldn't be turned into text. The message is shown to the user."""


def extract_pages(data: bytes, kind: str) -> list[str]:
    """Returns the text of each page. Plain-text files count as a single page."""
    if kind == "pdf":
        return _extract_pdf(data)
    try:
        return [data.decode("utf-8")]
    except UnicodeDecodeError as exc:
        raise ExtractionError("Text files must be UTF-8 encoded") from exc


def _extract_pdf(data: bytes) -> list[str]:
    # A leading underscore means "internal to this module", like a Java private method.
    try:
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ExtractionError("Password-protected PDFs aren't supported")
        return [page.extract_text() or "" for page in reader.pages]
    except ExtractionError:
        raise
    except Exception as exc:  # pypdf raises many different errors for malformed files
        raise ExtractionError("This file couldn't be read as a PDF") from exc