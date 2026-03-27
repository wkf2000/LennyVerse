from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.main import app, get_stats_service
from backend_api.stats_schemas import (
    DateRange,
    StatsSummary,
    TopicCount,
    TopicTrendItem,
    TopicTrendsResponse,
)


class _FakeStatsService:
    def get_topic_trends(self) -> TopicTrendsResponse:
        return TopicTrendsResponse(
            trends=[
                TopicTrendItem(quarter="2023-Q1", topic="ai", count=5),
                TopicTrendItem(quarter="2023-Q1", topic="growth", count=3),
            ],
            summary=StatsSummary(
                total_content=100,
                total_podcasts=50,
                total_newsletters=50,
                date_range=DateRange(start="2019-01-15", end="2025-12-31"),
                top_topics=[
                    TopicCount(topic="ai", count=5),
                    TopicCount(topic="growth", count=3),
                ],
            ),
        )


def test_stats_topic_trends_returns_200() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/topic-trends")
        assert response.status_code == 200
        payload = response.json()
        assert "trends" in payload
        assert "summary" in payload
        assert len(payload["trends"]) == 2
        assert payload["summary"]["total_content"] == 100
        assert payload["summary"]["total_podcasts"] == 50
        assert len(payload["summary"]["top_topics"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_stats_topic_trends_trend_shape() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/topic-trends")
        trend = response.json()["trends"][0]
        assert "quarter" in trend
        assert "topic" in trend
        assert "count" in trend
    finally:
        app.dependency_overrides.clear()
