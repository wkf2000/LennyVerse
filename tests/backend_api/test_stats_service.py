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
