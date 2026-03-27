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
