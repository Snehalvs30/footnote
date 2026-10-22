"""Talks to the LLM that writes answers.

LLMClient is a Protocol: like a Java interface, but any class with a matching
`stream` method fits, without declaring `implements`. That lets the app switch
providers with one setting, and lets tests use a fake LLM that costs nothing.
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Protocol

from app.config import settings

# Fast and inexpensive: a good fit for answering from provided passages.
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-5-5"
# Small enough to run on a laptop (~2 GB), good enough for development.
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"


class LLMClient(Protocol):
    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """Yields the answer in small pieces of text as the model writes it."""
        ...


class LLMNotConfiguredError(Exception):
    """No API key (or model) is set. The message says what to set."""


class AnthropicLLM:
    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import anthropic  # imported here, so you only need the SDK for the provider you use

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            # temperature=settings.llm_temperature,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            yield from stream.text_stream


class OpenAILLM:
    """Works with OpenAI, and with anything that speaks OpenAI's API format (like Ollama).

    base_url=None means OpenAI's own servers.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int, base_url: str | None = None) -> None:
        import openai

        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._max_tokens = max_tokens

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        response = self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=self._max_tokens,
            stream=True,
            temperature=settings.llm_temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


@lru_cache(maxsize=1)
def get_llm() -> LLMClient:
    """Builds the configured client once. Raises LLMNotConfiguredError if a setting is missing."""
    if settings.llm_provider == "ollama":
        # Ollama ignores the API key, but the OpenAI client requires a non-empty one.
        return OpenAILLM(
            api_key="ollama",
            model=settings.llm_model or DEFAULT_OLLAMA_MODEL,
            max_tokens=settings.max_answer_tokens,
            base_url=settings.ollama_base_url,
        )

    if settings.llm_provider == "anthropic":
        if settings.anthropic_api_key is None:
            raise LLMNotConfiguredError("Set FOOTNOTE_ANTHROPIC_API_KEY in backend/.env")
        return AnthropicLLM(
            settings.anthropic_api_key.get_secret_value(),
            settings.llm_model or DEFAULT_ANTHROPIC_MODEL,
            settings.max_answer_tokens,
        )

    if settings.openai_api_key is None:
        raise LLMNotConfiguredError("Set FOOTNOTE_OPENAI_API_KEY in backend/.env")
    if settings.llm_model is None:
        raise LLMNotConfiguredError("Set FOOTNOTE_LLM_MODEL to an OpenAI model name in backend/.env")
    return OpenAILLM(
        settings.openai_api_key.get_secret_value(), settings.llm_model, settings.max_answer_tokens
    )