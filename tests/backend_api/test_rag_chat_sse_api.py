from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from backend_api.config import Settings, get_settings
from backend_api.main import app, get_llm_client, get_rag_service
from backend_api.llm_client import LlmStreamTimeoutError, OpenAiCompatibleChatStreamer
from backend_api.rag_repository import RagChunkHit
from backend_api.rag_service import RagRetrievalTimeoutError, RagService


def _parse_sse(raw: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_name: str | None = None
        data_obj: dict[str, Any] | None = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                data_obj = json.loads(line.removeprefix("data:").strip())
        if event_name is not None and data_obj is not None:
            events.append((event_name, data_obj))
    return events


def _dim_vec() -> list[float]:
    return [0.0] * 768


class _FakeRepo:
    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: object | None = None,
    ) -> list[RagChunkHit]:
        return [
            RagChunkHit(
                chunk_id="c1",
                content_id="podcast::a",
                chunk_index=0,
                chunk_text="hello world " * 20,
                title="Episode A",
                guest=None,
                published_at=date(2024, 1, 1),
                tags=["growth"],
                content_type="podcast",
                embedding_distance=0.1,
            ),
        ]


class _EmptyRepo:
    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: object | None = None,
    ) -> list[RagChunkHit]:
        return []


class _OkLlm:
    last_stream_usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        yield "Answer "
        yield "text."


class _ErrorLlm:
    last_stream_usage = None

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        raise RuntimeError("generation failed")


class _TimeoutAfterFirstDeltaLlm:
    """Simulates a stalled stream: first token, then wall-clock budget exceeded."""

    last_stream_usage = None

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        yield "partial-"
        raise LlmStreamTimeoutError(partial_text="partial-")


class _RecordingLlm:
    last_messages: list[dict[str, Any]] | None = None
    last_stream_usage = {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        type(self).last_messages = list(messages)
        yield "ok"


class _CitationLlm:
    last_stream_usage = {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        del messages, model, timeout_seconds
        yield "Here is evidence [cite:chunk:podcast::a:0] from the source."


class _LowDensityCitationLlm:
    """Three factual sentences, one citation — fails ceil(3/2)=2 required markers."""

    last_stream_usage = {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3}

    def stream_text_deltas(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        timeout_seconds: float,
    ) -> Iterator[str]:
        del messages, model, timeout_seconds
        yield (
            "Revenue drives durable growth. Retention compounds over time. "
            "Teams ship faster outcomes [cite:chunk:podcast::a:0]."
        )


def _chat_settings(**overrides: Any) -> Settings:
    data = {
        "_env_file": None,
        "OPENAI_API_KEY": "test-key",
        "SUPABASE_DB_URL": "postgresql://unused",
        "rag_chat_timeout_seconds": 120,
    }
    data.update(overrides)
    return Settings(**data)


@pytest.fixture(autouse=True)
def _clear_overrides() -> Any:
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_chat_stream_emits_done_event() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _OkLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})

    assert response.status_code == 200
    events = _parse_sse(response.text)
    names = [name for name, _ in events]
    assert names.count("done") == 1
    assert names[-1] == "done"


def test_chat_done_event_contains_required_fields() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _OkLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})
    events = _parse_sse(response.text)
    done_events = [payload for name, payload in events if name == "done"]
    assert len(done_events) == 1
    payload = done_events[0]
    assert "latency_ms" in payload and isinstance(payload["latency_ms"], int)
    assert payload["source_count"] == 1
    assert payload["partial"] is False
    usage = payload["token_usage"]
    assert set(usage.keys()) >= {"input_tokens", "output_tokens", "total_tokens"}


def test_chat_error_event_contains_required_fields() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _ErrorLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})
    events = _parse_sse(response.text)

    err = next((p for n, p in events if n == "error"), None)
    assert err is not None
    assert err["code"] == "generation_error"
    assert "message" in err and err["message"]
    assert err["retryable"] is False

    done = next((p for n, p in events if n == "done"), None)
    assert done is not None
    assert done["partial"] is True


def test_retrieval_timeout_returns_retryable_error_state() -> None:
    class _TimeoutRag(RagService):
        def search(
            self,
            query: str,
            *,
            k: int | None = None,
            filters: object | None = None,
        ) -> object:
            raise RagRetrievalTimeoutError("Retrieval timed out.")

    settings = _chat_settings()
    service = _TimeoutRag(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _OkLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})
    events = _parse_sse(response.text)

    err = next((p for n, p in events if n == "error"), None)
    assert err is not None
    assert err["code"] == "retrieval_timeout"
    assert err["retryable"] is True

    done = next((p for n, p in events if n == "done"), None)
    assert done is not None
    assert done["partial"] is True
    assert [n for n, _ in events].count("done") == 1


def test_generation_timeout_preserves_partial_and_done() -> None:
    settings = _chat_settings(rag_chat_timeout_seconds=1)
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _TimeoutAfterFirstDeltaLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})
    events = _parse_sse(response.text)

    deltas = [p["text_delta"] for n, p in events if n == "answer_delta"]
    assert "".join(deltas).startswith("partial-")

    err = next((p for n, p in events if n == "error"), None)
    assert err is not None
    assert err["code"] == "generation_timeout"
    assert err["retryable"] is True

    done = next((p for n, p in events if n == "done"), None)
    assert done is not None
    assert done["partial"] is True
    assert [n for n, _ in events].count("done") == 1


@pytest.mark.parametrize(
    ("payload", "expected_status", "detail_check"),
    [
        (
            {"query": "ok", "filters": {"date_from": "not-a-date"}},
            422,
            lambda d: "Invalid date_from" in str(d.get("detail", "")),
        ),
        (
            {"query": ""},
            422,
            lambda d: d.get("detail") == "query must not be empty or whitespace only",
        ),
        (
            {"query": "   "},
            422,
            lambda d: d.get("detail") == "query must not be empty or whitespace only",
        ),
    ],
)
def test_prestream_failure_returns_non_2xx_json(
    payload: dict[str, object],
    expected_status: int,
    detail_check: Callable[[dict[str, Any]], bool],
) -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _OkLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json=payload)
    assert response.status_code == expected_status
    body = response.json()
    assert detail_check(body)
    assert response.headers.get("content-type", "").startswith("application/json")


def test_chat_history_is_capped() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _RecordingLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    history: list[dict[str, str]] = []
    for i in range(6):
        history.append({"role": "user", "content": f"u{i}"})
        history.append({"role": "assistant", "content": f"a{i}"})

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "final", "history": history})
    assert response.status_code == 200
    assert _RecordingLlm.last_messages is not None
    messages = _RecordingLlm.last_messages
    # system + up to 8 history turns + final user prompt
    sandwiched = messages[1:-1]
    assert len(sandwiched) == 8
    assert sandwiched[0]["content"] == "u2"
    assert sandwiched[-1]["content"] == "a5"


def test_chat_stream_emits_citation_event_with_source_ref_id() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _CitationLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})

    assert response.status_code == 200
    events = _parse_sse(response.text)
    citation_events = [payload for name, payload in events if name == "citation_used"]
    assert citation_events
    assert citation_events[0]["source_ref"]["id"] == "chunk:podcast::a:0"


def test_chat_empty_retrieval_returns_source_count_zero() -> None:
    settings = _chat_settings()
    service = RagService(_EmptyRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _OkLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "zzzz-no-archive-matches-zzzz"})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    done = next(p for n, p in events if n == "done")
    assert done["source_count"] == 0
    assert done["partial"] is False
    answer_text = "".join(p["text_delta"] for n, p in events if n == "answer_delta")
    assert "archive" in answer_text.lower()
    assert "evidence" in answer_text.lower() or "find" in answer_text.lower()
    assert not any(n == "citation_used" for n, _ in events)


def test_chat_marks_uncited_segments_when_density_is_low() -> None:
    settings = _chat_settings()
    service = RagService(_FakeRepo(), settings, embed_query=lambda _q: _dim_vec())
    app.dependency_overrides[get_rag_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: _LowDensityCitationLlm()
    app.dependency_overrides[get_settings] = lambda: settings

    client = TestClient(app)
    response = client.post("/api/chat", json={"query": "hello"})
    assert response.status_code == 200
    events = _parse_sse(response.text)
    combined = "".join(p["text_delta"] for n, p in events if n == "answer_delta")
    assert "[Grounding disclaimer]" in combined
    assert "[Uncited portions]" in combined
    assert "Revenue drives durable growth" in combined
    assert "Retention compounds over time" in combined


def test_openai_api_base_is_passed_through_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class _FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            seen.update(kwargs)

    monkeypatch.setattr("backend_api.llm_client.OpenAI", _FakeOpenAI)

    settings = _chat_settings(OPENAI_API_BASE="https://openai-compatible.example/v1")
    streamer = OpenAiCompatibleChatStreamer(settings)

    assert streamer is not None
    assert seen["api_key"] == "test-key"
    assert seen["base_url"] == "https://openai-compatible.example/v1"


def test_openai_timeout_is_translated_to_llm_stream_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class _ExplodingStream:
        def __iter__(self) -> Iterator[Any]:
            raise httpx.ReadTimeout("timed out")
            yield  # pragma: no cover

    class _FakeCompletions:
        def create(self, **kwargs: Any) -> Iterator[Any]:
            del kwargs
            return _ExplodingStream()

    class _FakeChat:
        def __init__(self) -> None:
            self.completions = _FakeCompletions()

    class _FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            del kwargs
            self.chat = _FakeChat()

        def with_options(self, **kwargs: Any) -> "_FakeOpenAI":
            del kwargs
            return self

    monkeypatch.setattr("backend_api.llm_client.OpenAI", _FakeOpenAI)

    settings = _chat_settings()
    streamer = OpenAiCompatibleChatStreamer(settings)

    with pytest.raises(LlmStreamTimeoutError):
        list(
            streamer.stream_text_deltas(
                messages=[{"role": "user", "content": "hello"}],
                model="gpt-4o-mini",
                timeout_seconds=1.0,
            )
        )
