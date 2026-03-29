from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.main import app, get_stats_service
from backend_api.stats_schemas import (
    DateRange, StatsSummary, TopicCount, TopicTrendItem, TopicTrendsResponse,
    HeatmapItem, HeatmapResponse,
    ContentBreakdownItem, ContentBreakdownResponse,
    GuestCount, TopGuestsResponse,
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

    def get_heatmap_data(self) -> HeatmapResponse:
        return HeatmapResponse(
            items=[
                HeatmapItem(year=2023, week=11, type="podcast", title="Ep 1", published_at="2023-03-15"),
                HeatmapItem(year=2023, week=12, type="newsletter", title="NL 1", published_at="2023-03-20"),
            ]
        )

    def get_content_breakdown(self) -> ContentBreakdownResponse:
        return ContentBreakdownResponse(
            breakdown=[
                ContentBreakdownItem(quarter="2023-Q1", type="podcast", count=10, avg_word_count=5000),
                ContentBreakdownItem(quarter="2023-Q1", type="newsletter", count=15, avg_word_count=2000),
            ]
        )

    def get_top_guests(self) -> TopGuestsResponse:
        return TopGuestsResponse(
            guests=[
                GuestCount(guest="Shreyas Doshi", count=10),
                GuestCount(guest="Elena Verna", count=8),
            ]
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


def test_stats_heatmap_returns_200() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/heatmap")
        assert response.status_code == 200
        payload = response.json()
        assert "items" in payload
        assert len(payload["items"]) == 2
        assert payload["items"][0]["year"] == 2023
        assert payload["items"][0]["type"] == "podcast"
    finally:
        app.dependency_overrides.clear()


def test_stats_content_breakdown_returns_200() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/content-breakdown")
        assert response.status_code == 200
        payload = response.json()
        assert "breakdown" in payload
        assert len(payload["breakdown"]) == 2
        assert payload["breakdown"][0]["quarter"] == "2023-Q1"
    finally:
        app.dependency_overrides.clear()


def test_stats_top_guests_returns_200() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/top-guests")
        assert response.status_code == 200
        payload = response.json()
        assert "guests" in payload
        assert len(payload["guests"]) == 2
        assert payload["guests"][0]["guest"] == "Shreyas Doshi"
    finally:
        app.dependency_overrides.clear()
