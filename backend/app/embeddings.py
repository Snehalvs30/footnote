"""Turns text into embeddings: lists of 384 numbers that capture its meaning.

Texts with similar meanings get similar numbers, even with different words:
"How do I reset my password?" lands close to "Steps to recover account access".
That's what makes search by meaning possible.
"""

from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding

from app.config import settings
from app.models import EMBEDDING_DIMENSIONS


class Embedder:
    def __init__(self, model_name: str, cache_dir: str) -> None:
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Embeds document chunks. Batches the work internally, so pass them all at once."""
        vectors = [vector.tolist() for vector in self._model.passage_embed(texts)]
        for vector in vectors:
            _check_dimensions(vector)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embeds a search question.

        Some models (like BGE) are trained to treat questions and passages slightly
        differently, so queries and passages use separate methods.
        """
        vector = next(iter(self._model.query_embed(text))).tolist()
        _check_dimensions(vector)
        return vector


def _check_dimensions(vector: list[float]) -> None:
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Embedding model returned {len(vector)} numbers, but the database column "
            f"holds {EMBEDDING_DIMENSIONS}. Did FOOTNOTE_EMBEDDING_MODEL change?"
        )


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Loads the model once and reuses it (loading takes seconds; embedding takes milliseconds).

    @lru_cache remembers the return value, so every later call gets the same
    Embedder: a simple singleton, like a Spring @Bean.
    """
    cache_dir = str(Path(settings.embedding_cache_dir).expanduser())
    return Embedder(settings.embedding_model, cache_dir)