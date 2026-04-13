from __future__ import annotations

import json
from datetime import date
from typing import Any

from backend_api.rag_repository import RagChunkHit, RagRepository


def test_generate_config_defaults(unset_rag_env) -> None:
    from backend_api.config import Settings

    settings = Settings(_env_file=None)
    assert settings.generate_max_weeks == 16
    assert settings.generate_retrieval_k_per_reading == 5
    assert settings.generate_outline_k == 30
    assert settings.generate_timeout_seconds == 120


class _FakeCursorWithResults:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.executed: list[tuple[str, object | None]] = []
        self._rows = rows

    def __enter__(self) -> _FakeCursorWithResults:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, sql: str, params: object | None = None) -> None:
        self.executed.append((sql, params))

    def fetchall(self) -> list[dict[str, Any]]:
        return list(self._rows)


class _FakeConnection:
    def __init__(self, cursor: _FakeCursorWithResults) -> None:
        self._cursor = cursor

    def __enter__(self) -> _FakeConnection:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def cursor(self, *, row_factory: object | None = None) -> _FakeCursorWithResults:
        return self._cursor


def test_repository_fetch_chunks_by_content_ids_builds_correct_sql() -> None:
    fake_cursor = _FakeCursorWithResults(
        [
            {
                "chunk_id": "ch-1",
                "content_id": "newsletter::plg",
                "chunk_index": 0,
                "chunk_text": "PLG is...",
                "title": "PLG Guide",
                "guest": None,
                "published_at": None,
                "tags": [],
                "content_type": "newsletter",
            },
            {
                "chunk_id": "ch-2",
                "content_id": "newsletter::plg",
                "chunk_index": 1,
                "chunk_text": "Self-serve...",
                "title": "PLG Guide",
                "guest": None,
                "published_at": None,
                "tags": [],
                "content_type": "newsletter",
            },
        ]
    )
    fake_connection = _FakeConnection(fake_cursor)
    repository = RagRepository("postgresql://unused", timeout_seconds=10)
    repository._connect = lambda: fake_connection  # type: ignore[method-assign]

    hits = repository.fetch_chunks_by_content_ids(
        content_ids=["newsletter::plg"],
        max_chunks_per_content=5,
    )

    assert len(hits) == 2
    assert hits[0].content_id == "newsletter::plg"
    assert hits[0].chunk_index == 0
    assert hits[1].chunk_index == 1

    sql_executed = fake_cursor.executed[-1][0]
    assert "content_id" in sql_executed
    assert "ORDER BY" in sql_executed
    assert "chunk_index" in sql_executed


def _make_hits() -> list[RagChunkHit]:
    return [
        RagChunkHit(
            chunk_id="ch-1",
            content_id="newsletter::plg-guide",
            chunk_index=0,
            chunk_text="Product-led growth is a model where the product drives acquisition.",
            title="The Ultimate Guide to PLG",
            guest=None,
            published_at=date(2023, 6, 15),
            tags=["growth", "plg"],
            content_type="newsletter",
            embedding_distance=0.1,
        ),
        RagChunkHit(
            chunk_id="ch-2",
            content_id="podcast::elena-verna",
            chunk_index=0,
            chunk_text="Elena discusses self-serve funnels and activation metrics.",
            title="Elena Verna on Growth",
            guest="Elena Verna",
            published_at=date(2023, 8, 1),
            tags=["growth"],
            content_type="podcast",
            embedding_distance=0.3,
        ),
    ]


class RecordingFakeRepo:
    def __init__(self, hits: list[RagChunkHit]) -> None:
        self._hits = hits
        self.search_calls: list[dict[str, Any]] = []

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: object | None = None,
    ) -> list[RagChunkHit]:
        self.search_calls.append({"k": k})
        return self._hits


class FakeRepoWithChunkFetch:
    def __init__(self, chunks: list[RagChunkHit]) -> None:
        self._chunks = chunks

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: object | None = None,
    ) -> list[RagChunkHit]:
        return self._chunks

    def fetch_chunks_by_content_ids(
        self, content_ids: list[str], max_chunks_per_content: int = 5
    ) -> list[RagChunkHit]:
        matched = [c for c in self._chunks if c.content_id in content_ids]
        grouped: dict[str, list[RagChunkHit]] = {}
        for hit in matched:
            grouped.setdefault(hit.content_id, []).append(hit)
        flattened: list[RagChunkHit] = []
        for hits in grouped.values():
            hits.sort(key=lambda item: item.chunk_index)
            flattened.extend(hits[:max_chunks_per_content])
        return flattened


def _fake_llm_outline_response(weeks_requested: int) -> str:
    weeks = []
    for i in range(1, weeks_requested + 1):
        weeks.append(
            {
                "week_number": i,
                "theme": f"Week {i} theme",
                "description": f"Description for week {i}",
                "readings": [
                    {
                        "content_id": "newsletter::plg-guide",
                        "title": "The Ultimate Guide to PLG",
                        "content_type": "newsletter",
                        "relevance_summary": "Core PLG framework",
                    }
                ],
            }
        )
    return json.dumps({"weeks": weeks})


def test_outline_generation_calls_search_and_returns_structured_response(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_service import GenerateService

    repo = RecordingFakeRepo(_make_hits())
    settings = Settings(_env_file=None)

    llm_called = {"count": 0}

    def fake_llm_call(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        llm_called["count"] += 1
        return _fake_llm_outline_response(4)

    service = GenerateService(
        repository=repo,  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=fake_llm_call,
    )

    response = service.generate_outline(topic="Product-Led Growth", num_weeks=4, difficulty="intermediate")

    assert response.topic == "Product-Led Growth"
    assert response.num_weeks == 4
    assert response.difficulty == "intermediate"
    assert len(response.weeks) == 4
    assert response.weeks[0].week_number == 1
    assert len(response.weeks[0].readings) >= 1
    assert repo.search_calls[0]["k"] == settings.generate_outline_k
    assert llm_called["count"] == 1
    assert isinstance(response.low_coverage, bool)


def test_langgraph_generation_produces_syllabus(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_schemas import ReadingRef, WeekOutline
    from backend_api.generate_service import GenerateService

    outline = [
        WeekOutline(
            week_number=1,
            theme="PLG Basics",
            description="Foundations",
            readings=[
                ReadingRef(
                    content_id="newsletter::plg-guide",
                    title="PLG Guide",
                    content_type="newsletter",
                    relevance_summary="Core framework",
                )
            ],
        ),
    ]
    repo = FakeRepoWithChunkFetch(
        [
            RagChunkHit(
                chunk_id="ch-1",
                content_id="newsletter::plg-guide",
                chunk_index=0,
                chunk_text="PLG is a business strategy...",
                title="PLG Guide",
                guest=None,
                published_at=date(2023, 6, 15),
                tags=["plg"],
                content_type="newsletter",
                embedding_distance=0.0,
            )
        ]
    )
    settings = Settings(_env_file=None)

    llm_call_log: list[str] = []

    def fake_llm(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        system = messages[0]["content"]
        llm_call_log.append(system)
        if "course material" in system.lower() or "week 1" in system.lower():
            return json.dumps(
                {
                    "learning_objectives": ["Define PLG"],
                    "narrative_summary": "PLG is... [cite:chunk:newsletter::plg-guide:0]",
                    "readings": [
                        {
                            "content_id": "newsletter::plg-guide",
                            "title": "PLG Guide",
                            "content_type": "newsletter",
                            "key_concepts": ["Self-serve"],
                            "notable_quotes": [],
                            "discussion_hooks": [],
                        }
                    ],
                    "key_takeaways": ["PLG works when..."],
                }
            )
        return json.dumps({})

    service = GenerateService(
        repository=repo,  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=fake_llm,
    )
    events = list(
        service.iter_generate_sse_events(
            topic="PLG",
            num_weeks=1,
            difficulty="intro",
            approved_outline=outline,
        )
    )

    step_logs = [event for event in events if event[0] == "step_log"]
    results = [event for event in events if event[0] == "result"]
    dones = [event for event in events if event[0] == "done"]

    assert len(step_logs) >= 2
    assert len(results) == 1
    assert len(dones) == 1
    assert results[0][1]["syllabus"]["weeks"][0]["status"] == "complete"
    assert len(llm_call_log) >= 1


def test_langgraph_continues_on_single_week_failure(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_schemas import ReadingRef, WeekOutline
    from backend_api.generate_service import GenerateService

    outline = [
        WeekOutline(
            week_number=1,
            theme="Week 1",
            description="Desc",
            readings=[
                ReadingRef(
                    content_id="newsletter::a",
                    title="A",
                    content_type="newsletter",
                    relevance_summary="R",
                )
            ],
        ),
        WeekOutline(
            week_number=2,
            theme="Week 2",
            description="Desc",
            readings=[
                ReadingRef(
                    content_id="newsletter::b",
                    title="B",
                    content_type="newsletter",
                    relevance_summary="R",
                )
            ],
        ),
    ]
    repo = FakeRepoWithChunkFetch(
        [
            RagChunkHit(
                chunk_id="ch-1",
                content_id="newsletter::a",
                chunk_index=0,
                chunk_text="Text A",
                title="A",
                guest=None,
                published_at=None,
                tags=[],
                content_type="newsletter",
                embedding_distance=0.0,
            ),
            RagChunkHit(
                chunk_id="ch-2",
                content_id="newsletter::b",
                chunk_index=0,
                chunk_text="Text B",
                title="B",
                guest=None,
                published_at=None,
                tags=[],
                content_type="newsletter",
                embedding_distance=0.0,
            ),
        ]
    )
    settings = Settings(_env_file=None)

    call_count = {"n": 0}

    def failing_week_1_llm(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        call_count["n"] += 1
        system = messages[0]["content"].lower()
        if "phase 1" in system:
            raise RuntimeError("LLM failed for phase 1")
        if "phase 2" in system or "playbook" in system:
            return json.dumps(
                {
                    "learning_objectives": ["Obj"],
                    "narrative_summary": "Summary",
                    "readings": [
                        {
                            "content_id": "newsletter::b",
                            "title": "B",
                            "content_type": "newsletter",
                            "key_concepts": [],
                            "notable_quotes": [],
                            "discussion_hooks": [],
                        }
                    ],
                    "key_takeaways": ["Takeaway"],
                }
            )
        return json.dumps({})

    service = GenerateService(
        repository=repo,  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=failing_week_1_llm,
    )
    events = list(
        service.iter_generate_sse_events(
            topic="Test",
            num_weeks=2,
            difficulty="intro",
            approved_outline=outline,
        )
    )

    step_logs = [event for event in events if event[0] == "step_log"]
    error_steps = [entry for entry in step_logs if entry[1].get("status") == "error"]
    results = [event for event in events if event[0] == "result"]

    assert len(error_steps) >= 1
    assert len(results) == 1
    statuses = [week["status"] for week in results[0][1]["syllabus"]["weeks"]]
    assert "incomplete" in statuses
    assert "complete" in statuses


def test_langgraph_recovers_when_week_readings_are_strings(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_schemas import ReadingRef, WeekOutline
    from backend_api.generate_service import GenerateService

    outline = [
        WeekOutline(
            week_number=1,
            theme="Pricing Foundations",
            description="Desc",
            readings=[
                ReadingRef(
                    content_id="newsletter::pricing-101",
                    title="Pricing 101",
                    content_type="newsletter",
                    relevance_summary="Core",
                )
            ],
        )
    ]
    repo = FakeRepoWithChunkFetch(
        [
            RagChunkHit(
                chunk_id="ch-1",
                content_id="newsletter::pricing-101",
                chunk_index=0,
                chunk_text="Pricing text",
                title="Pricing 101",
                guest=None,
                published_at=None,
                tags=[],
                content_type="newsletter",
                embedding_distance=0.0,
            )
        ]
    )
    settings = Settings(_env_file=None)

    def malformed_payload_llm(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        del model, response_format
        system = messages[0]["content"].lower()
        if "course material for week" in system:
            return json.dumps(
                {
                    "learning_objectives": "Understand pricing basics",
                    "narrative_summary": "Pricing ties to value [cite:chunk:newsletter::pricing-101:0]",
                    "readings": ["Pricing 101", "Value metrics"],
                    "key_takeaways": "Test willingness to pay",
                }
            )
        return json.dumps({})

    service = GenerateService(
        repository=repo,  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=malformed_payload_llm,
    )
    events = list(
        service.iter_generate_sse_events(
            topic="Pricing",
            num_weeks=1,
            difficulty="intro",
            approved_outline=outline,
        )
    )

    results = [event for event in events if event[0] == "result"]
    assert len(results) == 1
    payload = results[0][1]
    assert payload["syllabus"]["weeks"][0]["status"] == "complete"


def test_generate_week_coerces_null_or_blank_reading_fields(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_schemas import ReadingRef, WeekOutline
    from backend_api.generate_service import GenerateService

    week = WeekOutline(
        week_number=1,
        theme="Pricing Foundations",
        description="Desc",
        readings=[
            ReadingRef(
                content_id="newsletter::pricing-101",
                title="Pricing 101",
                content_type="newsletter",
                relevance_summary="Core",
            )
        ],
    )
    settings = Settings(_env_file=None)

    def malformed_week_llm(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        del messages, model, response_format
        return json.dumps(
            {
                "learning_objectives": ["Understand pricing basics"],
                "narrative_summary": None,
                "readings": [
                    {
                        "content_id": None,
                        "title": " ",
                        "content_type": "",
                        "key_concepts": ["A"],
                        "notable_quotes": [],
                        "discussion_hooks": [],
                    }
                ],
                "key_takeaways": ["Takeaway"],
            }
        )

    service = GenerateService(
        repository=FakeRepoWithChunkFetch([]),  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=malformed_week_llm,
    )

    generated = service._generate_week(week=week, deep_chunks={}, difficulty="intro")

    assert generated.status == "complete"
    assert generated.narrative_summary == ""
    assert len(generated.readings) == 1
    assert generated.readings[0].content_id == "newsletter::pricing-101"
    assert generated.readings[0].title == "Pricing 101"
    assert generated.readings[0].content_type == "newsletter"


def test_generate_week_handles_non_object_json_payload(unset_rag_env) -> None:
    from backend_api.config import Settings
    from backend_api.generate_schemas import ReadingRef, WeekOutline
    from backend_api.generate_service import GenerateService

    week = WeekOutline(
        week_number=1,
        theme="PLG Basics",
        description="Desc",
        readings=[
            ReadingRef(
                content_id="newsletter::plg-guide",
                title="PLG Guide",
                content_type="newsletter",
                relevance_summary="Core",
            )
        ],
    )
    settings = Settings(_env_file=None)

    def list_payload_llm(messages: list[dict[str, str]], model: str, response_format: object = None) -> str:
        del messages, model, response_format
        return json.dumps(["unexpected", "shape"])

    service = GenerateService(
        repository=FakeRepoWithChunkFetch([]),  # type: ignore[arg-type]
        settings=settings,
        embed_query=lambda _q: [0.0] * 768,
        llm_json_call=list_payload_llm,
    )

    generated = service._generate_week(week=week, deep_chunks={}, difficulty="intro")

    assert generated.status == "complete"
    assert generated.learning_objectives == []
    assert generated.key_takeaways == []
    assert generated.narrative_summary == ""
    assert len(generated.readings) == 1
    assert generated.readings[0].content_id == "newsletter::plg-guide"
