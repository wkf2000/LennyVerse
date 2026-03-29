from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg
from psycopg.rows import dict_row


@dataclass(slots=True)
class TrendRow:
    quarter: str
    topic: str
    count: int


@dataclass(slots=True)
class SummaryRow:
    total_content: int
    total_podcasts: int
    total_newsletters: int
    min_date: date | None
    max_date: date | None


@dataclass(slots=True)
class HeatmapRow:
    id: str
    title: str
    type: str
    published_at: date
    year: int
    week: int


@dataclass(slots=True)
class BreakdownRow:
    quarter: str
    type: str
    count: int
    avg_word_count: int


@dataclass(slots=True)
class GuestRow:
    guest: str
    count: int


class StatsRepository:
    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url

    def _connect(self) -> psycopg.Connection:
        if not self._db_url:
            raise ValueError("db_url is required")
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def fetch_topic_trends(self) -> list[TrendRow]:
        query = """
            SELECT
                EXTRACT(YEAR FROM c.published_at)::int
                    || '-Q' || EXTRACT(QUARTER FROM c.published_at)::int AS quarter_label,
                LOWER(TRIM(t.tag)) AS topic,
                COUNT(*)::int AS cnt
            FROM content c, unnest(c.tags) AS t(tag)
            WHERE c.published_at IS NOT NULL
              AND t.tag IS NOT NULL
              AND TRIM(t.tag) <> ''
            GROUP BY EXTRACT(YEAR FROM c.published_at),
                     EXTRACT(QUARTER FROM c.published_at),
                     LOWER(TRIM(t.tag))
            ORDER BY EXTRACT(YEAR FROM c.published_at),
                     EXTRACT(QUARTER FROM c.published_at),
                     LOWER(TRIM(t.tag))
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            TrendRow(
                quarter=row["quarter_label"],
                topic=row["topic"],
                count=row["cnt"],
            )
            for row in rows
        ]

    def fetch_summary(self) -> SummaryRow:
        query = """
            SELECT
                COUNT(*)::int AS total_content,
                COUNT(*) FILTER (WHERE type = 'podcast')::int AS total_podcasts,
                COUNT(*) FILTER (WHERE type = 'newsletter')::int AS total_newsletters,
                MIN(published_at) AS min_date,
                MAX(published_at) AS max_date
            FROM content
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                row = cur.fetchone()

        if not row:
            return SummaryRow(
                total_content=0,
                total_podcasts=0,
                total_newsletters=0,
                min_date=None,
                max_date=None,
            )

        return SummaryRow(
            total_content=row["total_content"],
            total_podcasts=row["total_podcasts"],
            total_newsletters=row["total_newsletters"],
            min_date=row.get("min_date"),
            max_date=row.get("max_date"),
        )

    def fetch_heatmap_data(self) -> list[HeatmapRow]:
        query = """
            SELECT
                id, title, type, published_at,
                EXTRACT(ISOYEAR FROM published_at)::int AS year,
                EXTRACT(WEEK FROM published_at)::int AS week
            FROM content
            WHERE published_at IS NOT NULL
            ORDER BY published_at
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return [
            HeatmapRow(
                id=row["id"],
                title=row["title"],
                type=row["type"],
                published_at=row["published_at"],
                year=row["year"],
                week=row["week"],
            )
            for row in rows
        ]

    def fetch_content_breakdown(self) -> list[BreakdownRow]:
        query = """
            SELECT
                EXTRACT(YEAR FROM published_at)::int
                    || '-Q' || EXTRACT(QUARTER FROM published_at)::int AS quarter,
                type,
                COUNT(*)::int AS count,
                COALESCE(AVG(word_count)::int, 0) AS avg_word_count
            FROM content
            WHERE published_at IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM published_at),
                     EXTRACT(QUARTER FROM published_at),
                     type
            ORDER BY EXTRACT(YEAR FROM published_at),
                     EXTRACT(QUARTER FROM published_at),
                     type
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()
        return [
            BreakdownRow(
                quarter=row["quarter"],
                type=row["type"],
                count=row["count"],
                avg_word_count=row["avg_word_count"],
            )
            for row in rows
        ]

    def fetch_top_guests(self, limit: int = 20) -> list[GuestRow]:
        query = """
            SELECT guest, COUNT(*)::int AS count
            FROM content
            WHERE guest IS NOT NULL AND TRIM(guest) <> ''
            GROUP BY guest
            ORDER BY count DESC
            LIMIT %s
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, (limit,))
                rows = cur.fetchall()
        return [GuestRow(guest=row["guest"], count=row["count"]) for row in rows]
