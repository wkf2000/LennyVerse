from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.generate_schemas import OutlineResponse, ReadingRef, WeekOutline
from backend_api.main import app


class _FakeGenerateService:
    def generate_outline(self, topic: str, num_weeks: int, difficulty: str) -> OutlineResponse:
        return OutlineResponse(
            topic=topic,
            num_weeks=num_weeks,
            difficulty=difficulty,
            weeks=[
                WeekOutline(
                    week_number=1,
                    theme="Test Theme",
                    description="Test desc",
                    readings=[
                        ReadingRef(
                            content_id="newsletter::test",
                            title="Test",
                            content_type="newsletter",
                            relevance_summary="Relevant",
                        )
                    ],
                )
            ],
            corpus_coverage="Found 10 relevant pieces",
            low_coverage=False,
        )

    def iter_generate_sse_events(
        self,
        topic: str,
        num_weeks: int,
        difficulty: str,
        approved_outline: list[WeekOutline],
    ):
        del num_weeks, approved_outline
        yield ("step_log", {"node": "retrieve_deep_context", "status": "done", "message": "Done"})
        yield (
            "result",
            {
                "syllabus": {"topic": topic, "difficulty": difficulty, "weeks": []},
                "quiz": {"title": "Quiz", "total_questions": 0, "multiple_choice": [], "short_answer": []},
            },
        )
        yield ("done", {"total_duration_ms": 100, "weeks_generated": 0, "quiz_questions": 0})


def _override_generate_service() -> _FakeGenerateService:
    return _FakeGenerateService()


def test_outline_endpoint_returns_structured_json() -> None:
    from backend_api.main import get_generate_service

    app.dependency_overrides[get_generate_service] = _override_generate_service
    client = TestClient(app)
    try:
        response = client.post(
            "/api/generate/outline",
            json={"topic": "PLG", "num_weeks": 4, "difficulty": "intro"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["topic"] == "PLG"
        assert len(payload["weeks"]) == 1
        assert payload["low_coverage"] is False
    finally:
        app.dependency_overrides.clear()


def test_outline_endpoint_rejects_empty_topic() -> None:
    from backend_api.main import get_generate_service

    app.dependency_overrides[get_generate_service] = _override_generate_service
    client = TestClient(app)
    try:
        response = client.post(
            "/api/generate/outline",
            json={"topic": "  ", "num_weeks": 4},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_execute_endpoint_returns_sse_stream() -> None:
    from backend_api.main import get_generate_service

    app.dependency_overrides[get_generate_service] = _override_generate_service
    client = TestClient(app)
    try:
        body = {
            "topic": "PLG",
            "num_weeks": 1,
            "difficulty": "intro",
            "approved_outline": [
                {
                    "week_number": 1,
                    "theme": "PLG",
                    "description": "Basics",
                    "readings": [
                        {
                            "content_id": "newsletter::plg",
                            "title": "PLG",
                            "content_type": "newsletter",
                            "relevance_summary": "Core",
                        }
                    ],
                }
            ],
        }
        response = client.post("/api/generate/execute", json=body)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "event: step_log" in response.text
        assert "event: result" in response.text
        assert "event: done" in response.text
    finally:
        app.dependency_overrides.clear()


def test_full_outline_then_execute_flow() -> None:
    from backend_api.main import get_generate_service

    app.dependency_overrides[get_generate_service] = _override_generate_service
    client = TestClient(app)
    try:
        outline_response = client.post("/api/generate/outline", json={"topic": "PLG"})
        assert outline_response.status_code == 200
        outline = outline_response.json()

        execute_body = {
            "topic": outline["topic"],
            "num_weeks": outline["num_weeks"],
            "difficulty": outline["difficulty"],
            "approved_outline": outline["weeks"],
        }
        execute_response = client.post("/api/generate/execute", json=execute_body)
        assert execute_response.status_code == 200
        assert "event: done" in execute_response.text
    finally:
        app.dependency_overrides.clear()
