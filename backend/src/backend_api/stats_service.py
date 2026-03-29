from __future__ import annotations

import time
from collections import defaultdict

from backend_api.stats_repository import StatsRepository
from backend_api.stats_schemas import (
    ContentBreakdownItem,
    ContentBreakdownResponse,
    DateRange,
    GuestCount,
    HeatmapItem,
    HeatmapResponse,
    StatsSummary,
    TopGuestsResponse,
    TopicCount,
    TopicTrendItem,
    TopicTrendsResponse,
)

_CACHE_TTL_SECONDS = 300

_cache: TopicTrendsResponse | None = None
_cache_timestamp: float = 0.0

_heatmap_cache: HeatmapResponse | None = None
_heatmap_cache_timestamp: float = 0.0
_breakdown_cache: ContentBreakdownResponse | None = None
_breakdown_cache_timestamp: float = 0.0
_guests_cache: TopGuestsResponse | None = None
_guests_cache_timestamp: float = 0.0


def clear_stats_cache() -> None:
    global _cache, _cache_timestamp
    global _heatmap_cache, _heatmap_cache_timestamp
    global _breakdown_cache, _breakdown_cache_timestamp
    global _guests_cache, _guests_cache_timestamp
    _cache = None
    _cache_timestamp = 0.0
    _heatmap_cache = None
    _heatmap_cache_timestamp = 0.0
    _breakdown_cache = None
    _breakdown_cache_timestamp = 0.0
    _guests_cache = None
    _guests_cache_timestamp = 0.0


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

    def get_heatmap_data(self) -> HeatmapResponse:
        global _heatmap_cache, _heatmap_cache_timestamp

        now = time.monotonic()
        if _heatmap_cache is not None and (now - _heatmap_cache_timestamp) < _CACHE_TTL_SECONDS:
            return _heatmap_cache

        rows = self._repository.fetch_heatmap_data()
        items = [
            HeatmapItem(
                year=row.year,
                week=row.week,
                type=row.type,
                title=row.title,
                published_at=str(row.published_at),
            )
            for row in rows
        ]
        result = HeatmapResponse(items=items)
        _heatmap_cache = result
        _heatmap_cache_timestamp = now
        return result

    def get_content_breakdown(self) -> ContentBreakdownResponse:
        global _breakdown_cache, _breakdown_cache_timestamp

        now = time.monotonic()
        if _breakdown_cache is not None and (now - _breakdown_cache_timestamp) < _CACHE_TTL_SECONDS:
            return _breakdown_cache

        rows = self._repository.fetch_content_breakdown()
        breakdown = [
            ContentBreakdownItem(
                quarter=row.quarter,
                type=row.type,
                count=row.count,
                avg_word_count=row.avg_word_count,
            )
            for row in rows
        ]
        result = ContentBreakdownResponse(breakdown=breakdown)
        _breakdown_cache = result
        _breakdown_cache_timestamp = now
        return result

    def get_top_guests(self) -> TopGuestsResponse:
        global _guests_cache, _guests_cache_timestamp

        now = time.monotonic()
        if _guests_cache is not None and (now - _guests_cache_timestamp) < _CACHE_TTL_SECONDS:
            return _guests_cache

        rows = self._repository.fetch_top_guests()
        guests = [
            GuestCount(guest=row.guest, count=row.count)
            for row in rows
        ]
        result = TopGuestsResponse(guests=guests)
        _guests_cache = result
        _guests_cache_timestamp = now
        return result
