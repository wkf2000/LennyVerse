from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from backend_api.rag_repository import RagChunkHit, RagRetrievalFilters


def test_rag_defaults_are_available(unset_rag_env) -> None:
    from backend_api.config import Settings

    settings = Settings(_env_file=None)
    assert settings.rag_default_k == 8
    assert settings.rag_max_k == 32
    assert settings.rag_retrieval_timeout_seconds == 30
    assert settings.rag_chat_timeout_seconds == 120


class RecordingFakeRagRepository:
    def __init__(self, hits: list[RagChunkHit] | None = None) -> None:
        self.last_call: dict[str, Any] = {}
        self._hits = hits

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: RagRetrievalFilters | None = None,
    ) -> list[RagChunkHit]:
        self.last_call = {
            "query_embedding": list(query_embedding),
            "k": k,
            "filters": filters,
        }
        return list(self._hits or [])


def _dim_vec() -> list[float]:
    return [0.0] * 768


class _FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object | None]] = []

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: object | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return []


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self, *, row_factory: object | None = None) -> _FakeCursor:
        return self._cursor


def test_repository_applies_retrieval_statement_timeout() -> None:
    from backend_api.rag_repository import RagRepository

    fake_cursor = _FakeCursor()
    fake_connection = _FakeConnection(fake_cursor)
    repository = RagRepository("postgresql://unused", timeout_seconds=7)
    repository._connect = lambda: fake_connection  # type: ignore[method-assign]

    repository.search_similar_chunks(query_embedding=_dim_vec(), k=2, filters=None)

    assert len(fake_cursor.executed) == 2
    assert fake_cursor.executed[0][0] == "SET LOCAL statement_timeout = 7000"
    assert "ORDER BY embedding_distance ASC" in fake_cursor.executed[1][0]


def test_search_results_have_stable_ids(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.rag_service import RagService, normalize_cosine_distance_score, stable_chunk_result_id

    hits = [
        RagChunkHit(
            chunk_id="chunk-row-1",
            content_id="podcast::ada-chen-rekhi",
            chunk_index=3,
            chunk_text="excerpt one",
            title="Ada",
            guest="Ada Chen Rekhi",
            published_at=date(2023, 4, 16),
            tags=["growth"],
            content_type="podcast",
            embedding_distance=0.0,
        ),
        RagChunkHit(
            chunk_id="chunk-row-2",
            content_id="newsletter::weekly-12",
            chunk_index=0,
            chunk_text="excerpt two",
            title="Weekly",
            guest=None,
            published_at=None,
            tags=[],
            content_type="newsletter",
            embedding_distance=2.0,
        ),
        RagChunkHit(
            chunk_id="chunk-row-3",
            content_id="podcast::edge",
            chunk_index=1,
            chunk_text="mid",
            title="Mid",
            guest=None,
            published_at=date(2022, 6, 1),
            tags=["b2b"],
            content_type="podcast",
            embedding_distance=1.0,
        ),
    ]
    repo = RecordingFakeRagRepository(hits)
    settings = Settings(_env_file=None)
    service = RagService(
        repository=repo,
        settings=settings,
        embed_query=lambda _q: _dim_vec(),
    )

    response = service.search("pricing", k=8)

    assert response.results[0].id == stable_chunk_result_id("podcast::ada-chen-rekhi", 3)
    assert response.results[0].id == "chunk:podcast::ada-chen-rekhi:3"
    assert response.results[0].score == pytest.approx(normalize_cosine_distance_score(0.0))
    assert response.results[0].score == 1.0
    assert response.results[0].content_id == "podcast::ada-chen-rekhi"
    assert response.results[0].chunk_index == 3

    assert response.results[1].id == "chunk:newsletter::weekly-12:0"
    assert response.results[1].score == pytest.approx(normalize_cosine_distance_score(2.0))
    assert response.results[1].score == 0.0

    assert response.results[2].score == pytest.approx(normalize_cosine_distance_score(1.0))
    assert response.results[2].score == 0.5

    for r in response.results:
        assert 0.0 <= r.score <= 1.0

    assert repo.last_call["k"] == 8


def test_search_applies_filters(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.rag_schemas import RagSearchFilters
    from backend_api.rag_service import RagService

    repo = RecordingFakeRagRepository([])
    settings = Settings(_env_file=None)
    service = RagService(
        repository=repo,
        settings=settings,
        embed_query=lambda _q: _dim_vec(),
    )

    filters = RagSearchFilters(
        tags=["growth", "b2b"],
        date_from="2023-01-01",
        date_to="2023-12-31",
        content_type="podcast",
    )
    service.search("gtm", k=4, filters=filters)

    assert repo.last_call["k"] == 4
    assert repo.last_call["filters"] == RagRetrievalFilters(
        tags=["growth", "b2b"],
        date_from=date(2023, 1, 1),
        date_to=date(2023, 12, 31),
        content_type="podcast",
    )
    assert len(repo.last_call["query_embedding"]) == 768


def test_service_reuses_openai_client_across_search_calls(monkeypatch: pytest.MonkeyPatch, unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.rag_service import RagService

    class _FakeEmbeddings:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, *, model: str, input: str) -> SimpleNamespace:
            self.calls += 1
            return SimpleNamespace(data=[SimpleNamespace(embedding=_dim_vec())])

    class _FakeOpenAI:
        init_calls = 0
        embeddings_api: _FakeEmbeddings | None = None

        def __init__(self, **kwargs: object) -> None:
            type(self).init_calls += 1
            self.embeddings = _FakeEmbeddings()
            type(self).embeddings_api = self.embeddings

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("backend_api.rag_service.OpenAI", _FakeOpenAI)

    repo = RecordingFakeRagRepository([])
    settings = Settings(_env_file=None)
    service = RagService(repository=repo, settings=settings)

    service.search("first")
    service.search("second")

    assert _FakeOpenAI.init_calls == 1
    assert _FakeOpenAI.embeddings_api is not None
    assert _FakeOpenAI.embeddings_api.calls == 2


@pytest.mark.parametrize(
    ("filters", "expected_message"),
    [
        (
            {"date_from": "2024-13-40"},
            "Invalid date_from: '2024-13-40'. Expected format YYYY-MM-DD.",
        ),
        (
            {"date_to": "nope"},
            "Invalid date_to: 'nope'. Expected format YYYY-MM-DD.",
        ),
    ],
)
def test_invalid_filter_dates_raise_predictable_validation_error(
    unset_rag_env,
    filters: dict[str, str],
    expected_message: str,
) -> None:
    from backend_api.config import Settings
    from backend_api.rag_schemas import RagSearchFilters
    from backend_api.rag_service import RagFilterValidationError, RagService

    repo = RecordingFakeRagRepository([])
    settings = Settings(_env_file=None)
    service = RagService(
        repository=repo,
        settings=settings,
        embed_query=lambda _q: _dim_vec(),
    )

    with pytest.raises(RagFilterValidationError, match=expected_message):
        service.search("bad-date", filters=RagSearchFilters(**filters))
