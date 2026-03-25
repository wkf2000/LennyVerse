from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Sequence

import psycopg
from psycopg.rows import dict_row

# pgvector cosine distance on `chunks.embedding` (Task 4 can reuse this expression and binds).
RAG_SIMILARITY_ORDER_EXPR = "ch.embedding <=> %(query_vec)s::vector"

# Core SELECT + join for semantic retrieval; append `WHERE ... ORDER BY ... LIMIT` (see `build_similarity_search_sql`).
RAG_SIMILARITY_SEARCH_BASE_SQL = """
    SELECT
        ch.id AS chunk_id,
        ch.content_id,
        ch.chunk_index,
        ch.text AS chunk_text,
        c.title,
        c.guest,
        c.published_at,
        c.tags,
        c.type AS content_type,
        ({order_expr}) AS embedding_distance
    FROM chunks ch
    INNER JOIN content c ON c.id = ch.content_id
""".format(order_expr=RAG_SIMILARITY_ORDER_EXPR)


def format_vector_literal(values: Sequence[float]) -> str:
    """Serialize embedding for Postgres `::vector` casts (matches data-pipeline convention)."""
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


@dataclass(slots=True)
class RagRetrievalFilters:
    """Optional predicates applied against joined `content` rows."""

    tags: list[str] | None = None
    date_from: date | None = None
    date_to: date | None = None
    content_type: str | None = None


@dataclass(slots=True)
class RagChunkHit:
    chunk_id: str
    content_id: str
    chunk_index: int
    chunk_text: str
    title: str
    guest: str | None
    published_at: date | None
    tags: list[str]
    content_type: str
    embedding_distance: float


class RagRepository:
    """Postgres + pgvector retrieval over `chunks` joined to `content`."""

    def __init__(self, db_url: str, *, timeout_seconds: int = 30) -> None:
        self._db_url = db_url
        self._timeout_seconds = max(1, int(timeout_seconds))

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._db_url, prepare_threshold=None)

    @staticmethod
    def build_similarity_search_sql(filters: RagRetrievalFilters | None) -> tuple[str, dict[str, Any]]:
        """
        Build the full retrieval statement and filter parameters.

        The query vector is always bound as `query_vec`; limit as `k`.
        """
        where_parts = ["ch.embedding IS NOT NULL"]
        extra_params: dict[str, Any] = {}

        f = filters
        if f and f.tags:
            where_parts.append("c.tags && %(filter_tags)s::text[]")
            extra_params["filter_tags"] = f.tags
        if f and f.date_from is not None:
            where_parts.append("c.published_at >= %(date_from)s::date")
            extra_params["date_from"] = f.date_from
        if f and f.date_to is not None:
            where_parts.append("c.published_at <= %(date_to)s::date")
            extra_params["date_to"] = f.date_to
        if f and f.content_type is not None:
            where_parts.append("c.type = %(content_type)s")
            extra_params["content_type"] = f.content_type

        where_sql = " AND ".join(where_parts)
        sql = f"""
            {RAG_SIMILARITY_SEARCH_BASE_SQL.strip()}
            WHERE {where_sql}
            ORDER BY embedding_distance ASC
            LIMIT %(k)s
        """
        return sql.strip(), extra_params

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        k: int,
        filters: RagRetrievalFilters | None = None,
    ) -> list[RagChunkHit]:
        sql, filter_params = self.build_similarity_search_sql(filters)
        params: dict[str, Any] = {
            "query_vec": format_vector_literal(query_embedding),
            "k": k,
            **filter_params,
        }
        timeout_ms = self._timeout_seconds * 1000
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                # Scope timeout to the current transaction/query path only.
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [_row_to_hit(row) for row in rows]

    def fetch_chunks_by_content_ids(
        self,
        content_ids: list[str],
        max_chunks_per_content: int = 5,
    ) -> list[RagChunkHit]:
        if not content_ids:
            return []

        sql = """
            SELECT
                ranked.id AS chunk_id,
                ranked.content_id,
                ranked.chunk_index,
                ranked.text AS chunk_text,
                c.title,
                c.guest,
                c.published_at,
                c.tags,
                c.type AS content_type
            FROM (
                SELECT
                    ch.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY ch.content_id
                        ORDER BY ch.chunk_index ASC
                    ) AS row_num
                FROM chunks ch
                WHERE ch.content_id = ANY(%(content_ids)s)
            ) AS ranked
            INNER JOIN content c ON c.id = ranked.content_id
            WHERE ranked.row_num <= %(max_per)s
            ORDER BY ranked.content_id ASC, ranked.chunk_index ASC
        """
        params = {"content_ids": content_ids, "max_per": max(1, int(max_chunks_per_content))}
        timeout_ms = self._timeout_seconds * 1000
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
                cur.execute(sql, params)
                rows = cur.fetchall()

        return [_row_to_hit_no_distance(row) for row in rows]


def _row_to_hit(row: dict[str, Any]) -> RagChunkHit:
    return RagChunkHit(
        chunk_id=row["chunk_id"],
        content_id=row["content_id"],
        chunk_index=int(row["chunk_index"]),
        chunk_text=row["chunk_text"],
        title=row["title"],
        guest=row.get("guest"),
        published_at=row.get("published_at"),
        tags=list(row.get("tags") or []),
        content_type=row["content_type"],
        embedding_distance=float(row["embedding_distance"]),
    )


def _row_to_hit_no_distance(row: dict[str, Any]) -> RagChunkHit:
    return RagChunkHit(
        chunk_id=row["chunk_id"],
        content_id=row["content_id"],
        chunk_index=int(row["chunk_index"]),
        chunk_text=row["chunk_text"],
        title=row["title"],
        guest=row.get("guest"),
        published_at=row.get("published_at"),
        tags=list(row.get("tags") or []),
        content_type=row["content_type"],
        embedding_distance=0.0,
    )
