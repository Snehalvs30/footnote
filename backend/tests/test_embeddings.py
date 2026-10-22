"""Tests for app/embeddings.py.

The first run is a few seconds slower while the embedding model loads.
"""

from app.embeddings import get_embedder
from app.models import EMBEDDING_DIMENSIONS


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """1.0 = same meaning, 0 = unrelated."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    return dot / (norm_a * norm_b)


def test_embedding_has_the_expected_number_of_dimensions():
    assert len(get_embedder().embed_query("Hello")) == EMBEDDING_DIMENSIONS


def test_similar_sentences_are_closer_than_unrelated_ones():
    embedder = get_embedder()
    password = embedder.embed_query("How do I reset my password?")
    recover = embedder.embed_query("Steps to recover account access")
    weather = embedder.embed_query("The weather is sunny today.")

    # Tests a relationship, not exact numbers, so it survives small model changes.
    assert cosine_similarity(password, recover) > cosine_similarity(password, weather)