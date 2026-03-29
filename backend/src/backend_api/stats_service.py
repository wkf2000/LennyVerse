from __future__ import annotations

import time
from collections import defaultdict

from backend_api.stats_repository import StatsRepository
from backend_api.stats_schemas import (
    DateRange,
    StatsSummary,
    TopicCount,
    TopicTrendItem,
    TopicTrendsResponse,
)

_CACHE_TTL_SECONDS = 300

_cache: TopicTrendsResponse | None = None
_cache_timestamp: float = 0.0


def clear_stats_cache() -> None:
    global _cache, _cache_timestamp
    _cache = None
    _cache_timestamp = 0.0


class StatsService:
    def __init__(self, repository: StatsRepository) -> None:
        self._repository = repository

    def get_topic_trends(self) -> TopicTrendsResponse:
        global _cache, _cache_timestamp

        now = time.monotonic()
        if _cache is not None and (now - _cache_timestamp) < _CACHE_TTL_SECONDS:
            return _cache
        trend_rows = self._repository.fetch_topic_trends()
        summary_row = self._repository.fetch_summary()

        trends = [
            TopicTrendItem(quarter=row.quarter, topic=row.topic, count=row.count)
            for row in trend_rows
        ]

        topic_totals: dict[str, int] = defaultdict(int)
        for row in trend_rows:
            topic_totals[row.topic] += row.count

        top_topics = sorted(
            [TopicCount(topic=t, count=c) for t, c in topic_totals.items()],
            key=lambda x: (-x.count, x.topic),
        )

        date_range = DateRange(
            start=str(summary_row.min_date) if summary_row.min_date else "",
            end=str(summary_row.max_date) if summary_row.max_date else "",
        )

        summary = StatsSummary(
            total_content=summary_row.total_content,
            total_podcasts=summary_row.total_podcasts,
            total_newsletters=summary_row.total_newsletters,
            date_range=date_range,
            top_topics=top_topics,
        )

        result = TopicTrendsResponse(trends=trends, summary=summary)
        _cache = result
        _cache_timestamp = now
        return result
