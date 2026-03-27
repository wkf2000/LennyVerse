from __future__ import annotations

from backend_api.stats_repository import StatsRepository, TrendRow, SummaryRow


class FakeStatsRepository(StatsRepository):
    """In-memory fake for unit testing the service layer."""

    def __init__(
        self,
        trend_rows: list[TrendRow] | None = None,
        summary_row: SummaryRow | None = None,
    ) -> None:
        self._trend_rows = trend_rows or []
        self._summary_row = summary_row or SummaryRow(
            total_content=0,
            total_podcasts=0,
            total_newsletters=0,
            min_date=None,
            max_date=None,
        )

    def fetch_topic_trends(self) -> list[TrendRow]:
        return self._trend_rows

    def fetch_summary(self) -> SummaryRow:
        return self._summary_row


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
