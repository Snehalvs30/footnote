"""Application settings, read from environment variables (or a .env file).

Like Spring's application.yaml + @ConfigurationProperties: each field below can be
overridden by an environment variable with the FOOTNOTE_ prefix, e.g.
FOOTNOTE_DATABASE_URL=postgresql+psycopg://...
Secrets (API keys) go in backend/.env, which Git ignores. Never commit them.
"""

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="FOOTNOTE_")

    # "postgresql+psycopg" = PostgreSQL, using the psycopg (version 3) driver.
    database_url: str = "postgresql+psycopg://footnote:footnote@localhost:5433/footnote"

    # Uploads larger than this are rejected with 413.
    max_upload_mb: int = 10

    # Local embedding model: free, no API key, ~70 MB downloaded once.
    # Produces 384 numbers per text, matching EMBEDDING_DIMENSIONS in models.py.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    # A fixed folder, so the model is downloaded once (not on every restart).
    embedding_cache_dir: str = "~/.cache/footnote/fastembed"

    # ---- Answer generation (Day 4) ----
    # "anthropic" and "openai" are paid APIs; "ollama" runs a free model on your own Mac.
    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    # Leave empty to use the provider's default in llm.py.
    llm_model: str | None = None
    # Where Ollama listens. It speaks the same API format as OpenAI.
    ollama_base_url: str = "http://localhost:11434/v1"
    # SecretStr hides the value in logs and error messages ("**********").
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    max_answer_tokens: int = 1024
    # How many passages to send to the LLM per question.
    answer_top_k: int = 6
    # Passages scoring below this are treated as irrelevant. If none pass, we answer
    # "not found" without calling the LLM. We'll tune this with the evaluation set.
    min_relevance: float = 0.5

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


# One shared instance, imported wherever settings are needed.
settings = Settings()