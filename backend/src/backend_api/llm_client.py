from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Protocol, runtime_checkable

import httpx
from openai import APITimeoutError, OpenAI

from backend_api.config import Settings


def build_embedding_client(settings: Settings) -> OpenAI:
    base = (settings.ollama_embed_base_url or "").strip()
    if not base:
        msg = "OLLAMA_EMBED_BASE_URL is required for embedding queries when no embed_query override is provided."
        raise ValueError(msg)
    return OpenAI(
        api_key=settings.embedding_api_key,
        base_url=base.rstrip("/"),
    )


def default_embed_query(settings: Settings, client: OpenAI | None = None) -> Callable[[str], list[float]]:
    if client is None:
        client = build_embedding_client(settings)

    def embed(text: str) -> list[float]:
        response = client.embeddings.create(model=settings.embedding_model, input=text)
        return list(response.data[0].embedding)

    return embed


@runtime_checkable
class ChatCompletionStreamer(Protocol):
    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        """Yield text deltas from the chat completion stream."""
        ...


class LlmStreamTimeoutError(Exception):
    """Raised when generation exceeds its wall-clock budget (including from streamer impl)."""

    def __init__(self, *, partial_text: str) -> None:
        super().__init__("generation timed out")
        self.partial_text = partial_text


def summarize_openai_usage(usage: Any) -> dict[str, int | None]:
    if usage is None:
        return {"input_tokens": None, "output_tokens": None, "total_tokens": None}
    return {
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


class OpenAiCompatibleChatStreamer:
    """OpenAI-compatible chat completions with streaming."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            msg = "OPENAI_API_KEY is required for chat generation."
            raise ValueError(msg)
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base or None,
        )
        self.last_stream_usage: dict[str, int | None] | None = None

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        self.last_stream_usage = None
        budget = max(1.0, float(timeout_seconds))
        scoped = self._client.with_options(
            timeout=httpx.Timeout(connect=10.0, read=budget, write=30.0, pool=10.0),
        )
        try:
            stream = scoped.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    self.last_stream_usage = summarize_openai_usage(usage)

                choice = chunk.choices[0] if chunk.choices else None
                if choice and choice.delta and choice.delta.content:
                    yield choice.delta.content
        except (APITimeoutError, httpx.TimeoutException, TimeoutError) as exc:
            raise LlmStreamTimeoutError(partial_text="") from exc
