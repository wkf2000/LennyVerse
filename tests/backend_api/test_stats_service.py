from __future__ import annotations

from unittest.mock import patch

import pytest

from backend_api.stats_repository import StatsRepository, TrendRow, SummaryRow, HeatmapRow, BreakdownRow, GuestRow


class FakeStatsRepository(StatsRepository):
    """In-memory fake for unit testing the service layer."""

    def __init__(
        self,
        trend_rows: list[TrendRow] | None = None,
        summary_row: SummaryRow | None = None,
        heatmap_rows: list[HeatmapRow] | None = None,
        breakdown_rows: list[BreakdownRow] | None = None,
        guest_rows: list[GuestRow] | None = None,
    ) -> None:
        self._trend_rows = trend_rows or []
        self._summary_row = summary_row or SummaryRow(
            total_content=0,
            total_podcasts=0,
            total_newsletters=0,
            min_date=None,
            max_date=None,
        )
        self._heatmap_rows = heatmap_rows or []
        self._breakdown_rows = breakdown_rows or []
        self._guest_rows = guest_rows or []

    def fetch_topic_trends(self) -> list[TrendRow]:
        return self._trend_rows

    def fetch_summary(self) -> SummaryRow:
        return self._summary_row

    def fetch_heatmap_data(self) -> list[HeatmapRow]:
        return self._heatmap_rows

    def fetch_content_breakdown(self) -> list[BreakdownRow]:
        return self._breakdown_rows

    def fetch_top_guests(self, limit: int = 20) -> list[GuestRow]:
        return self._guest_rows


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    from backend_api.stats_service import clear_stats_cache
    clear_stats_cache()


def test_fake_repository_returns_empty_trends() -> None:
    repo = FakeStatsRepository()
    assert repo.fetch_topic_trends() == []


def test_fake_repository_returns_summary() -> None:
    repo = FakeStatsRepository()
    summary = repo.fetch_summary()
    assert summary.total_content == 0


from datetime import date

from backend_api.stats_service import StatsService
from backend_api.stats_schemas import TopicTrendsResponse


def test_service_returns_topic_trends_response() -> None:
    repo = FakeStatsRepository(
        trend_rows=[
            TrendRow(quarter="2023-Q1", topic="ai", count=5),
            TrendRow(quarter="2023-Q1", topic="growth", count=3),
            TrendRow(quarter="2023-Q2", topic="ai", count=8),
        ],
        summary_row=SummaryRow(
            total_content=638,
            total_podcasts=289,
            total_newsletters=349,
            min_date=date(2019, 1, 15),
            max_date=date(2026, 2, 28),
        ),
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    assert isinstance(result, TopicTrendsResponse)
    assert len(result.trends) == 3
    assert result.trends[0].quarter == "2023-Q1"
    assert result.summary.total_content == 638
    assert result.summary.total_podcasts == 289
    assert result.summary.total_newsletters == 349
    assert result.summary.date_range.start == "2019-01-15"
    assert result.summary.date_range.end == "2026-02-28"
    assert len(result.summary.top_topics) > 0


def test_service_handles_none_dates() -> None:
    repo = FakeStatsRepository(
        summary_row=SummaryRow(
            total_content=0,
            total_podcasts=0,
            total_newsletters=0,
            min_date=None,
            max_date=None,
        ),
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    assert result.summary.date_range.start == ""
    assert result.summary.date_range.end == ""


def test_service_caches_result() -> None:
    repo = FakeStatsRepository(
        trend_rows=[TrendRow(quarter="2023-Q1", topic="ai", count=5)],
        summary_row=SummaryRow(
            total_content=10, total_podcasts=5, total_newsletters=5,
            min_date=None, max_date=None,
        ),
    )
    service = StatsService(repo)
    first = service.get_topic_trends()
    assert first.summary.total_content == 10

    repo2 = FakeStatsRepository(
        trend_rows=[TrendRow(quarter="2023-Q1", topic="ai", count=99)],
        summary_row=SummaryRow(
            total_content=999, total_podcasts=500, total_newsletters=499,
            min_date=None, max_date=None,
        ),
    )
    service2 = StatsService(repo2)
    second = service2.get_topic_trends()
    assert second.summary.total_content == 10  # still cached


def test_service_cache_expires() -> None:
    from backend_api import stats_service

    repo = FakeStatsRepository(
        trend_rows=[TrendRow(quarter="2023-Q1", topic="ai", count=5)],
        summary_row=SummaryRow(
            total_content=10, total_podcasts=5, total_newsletters=5,
            min_date=None, max_date=None,
        ),
    )
    service = StatsService(repo)
    service.get_topic_trends()

    stats_service._cache_timestamp -= stats_service._CACHE_TTL_SECONDS + 1

    repo2 = FakeStatsRepository(
        trend_rows=[TrendRow(quarter="2023-Q1", topic="ai", count=99)],
        summary_row=SummaryRow(
            total_content=999, total_podcasts=500, total_newsletters=499,
            min_date=None, max_date=None,
        ),
    )
    service2 = StatsService(repo2)
    result = service2.get_topic_trends()
    assert result.summary.total_content == 999  # fresh data


from backend_api.stats_schemas import HeatmapResponse, ContentBreakdownResponse, TopGuestsResponse


def test_service_returns_heatmap_data() -> None:
    repo = FakeStatsRepository(
        heatmap_rows=[
            HeatmapRow(id="1", title="Episode 1", type="podcast", published_at=date(2023, 3, 15), year=2023, week=11),
            HeatmapRow(id="2", title="Newsletter 1", type="newsletter", published_at=date(2023, 3, 20), year=2023, week=12),
        ],
    )
    service = StatsService(repo)
    result = service.get_heatmap_data()
    assert isinstance(result, HeatmapResponse)
    assert len(result.items) == 2
    assert result.items[0].year == 2023
    assert result.items[0].week == 11
    assert result.items[0].type == "podcast"
    assert result.items[0].title == "Episode 1"


def test_service_heatmap_empty() -> None:
    repo = FakeStatsRepository()
    service = StatsService(repo)
    result = service.get_heatmap_data()
    assert result.items == []


def test_service_returns_content_breakdown() -> None:
    repo = FakeStatsRepository(
        breakdown_rows=[
            BreakdownRow(quarter="2023-Q1", type="podcast", count=10, avg_word_count=5000),
            BreakdownRow(quarter="2023-Q1", type="newsletter", count=15, avg_word_count=2000),
        ],
    )
    service = StatsService(repo)
    result = service.get_content_breakdown()
    assert isinstance(result, ContentBreakdownResponse)
    assert len(result.breakdown) == 2
    assert result.breakdown[0].quarter == "2023-Q1"
    assert result.breakdown[0].type == "podcast"
    assert result.breakdown[0].avg_word_count == 5000


def test_service_breakdown_empty() -> None:
    repo = FakeStatsRepository()
    service = StatsService(repo)
    result = service.get_content_breakdown()
    assert result.breakdown == []


def test_service_returns_top_guests() -> None:
    repo = FakeStatsRepository(
        guest_rows=[
            GuestRow(guest="Lenny Rachitsky", count=50),
            GuestRow(guest="Shreyas Doshi", count=10),
        ],
    )
    service = StatsService(repo)
    result = service.get_top_guests()
    assert isinstance(result, TopGuestsResponse)
    assert len(result.guests) == 2
    assert result.guests[0].guest == "Lenny Rachitsky"
    assert result.guests[0].count == 50


def test_service_guests_empty() -> None:
    repo = FakeStatsRepository()
    service = StatsService(repo)
    result = service.get_top_guests()
    assert result.guests == []


def test_service_computes_top_topics_sorted() -> None:
    repo = FakeStatsRepository(
        trend_rows=[
            TrendRow(quarter="2023-Q1", topic="ai", count=5),
            TrendRow(quarter="2023-Q2", topic="ai", count=8),
            TrendRow(quarter="2023-Q1", topic="growth", count=3),
            TrendRow(quarter="2023-Q1", topic="b2b", count=1),
        ],
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    topics = result.summary.top_topics
    assert topics[0].topic == "ai"
    assert topics[0].count == 13
    assert topics[1].topic == "growth"
    assert topics[1].count == 3
    assert topics[2].topic == "b2b"
    assert topics[2].count == 1
