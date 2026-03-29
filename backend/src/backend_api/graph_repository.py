from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(slots=True)
class GraphNodeRecord:
    id: str
    type: str
    label: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class GraphEdgeRecord:
    id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    weight: int
    metadata: dict[str, Any]


@dataclass(slots=True)
class ContentRecord:
    id: str
    title: str
    content_type: str
    published_at: date | None
    guest: str | None
    tags: list[str]
    filename: str


class GraphRepository:
    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def list_nodes(self) -> list[GraphNodeRecord]:
        query = """
            SELECT id, type, label, metadata
            FROM graph_nodes
            ORDER BY label ASC
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            GraphNodeRecord(
                id=row["id"],
                type=row["type"],
                label=row["label"],
                metadata=row.get("metadata") or {},
            )
            for row in rows
        ]

    def list_edges(self) -> list[GraphEdgeRecord]:
        query = """
            SELECT id, source_node_id, target_node_id, relationship_type, weight, metadata
            FROM graph_edges
            ORDER BY relationship_type ASC, source_node_id ASC, target_node_id ASC
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            GraphEdgeRecord(
                id=row["id"],
                source_node_id=row["source_node_id"],
                target_node_id=row["target_node_id"],
                relationship_type=row["relationship_type"],
                weight=int(row.get("weight", 1)),
                metadata=row.get("metadata") or {},
            )
            for row in rows
        ]

    def get_node_by_id(self, node_id: str) -> GraphNodeRecord | None:
        query = """
            SELECT id, type, label, metadata
            FROM graph_nodes
            WHERE id = %(node_id)s
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"node_id": node_id})
                row = cur.fetchone()

        if not row:
            return None

        return GraphNodeRecord(
            id=row["id"],
            type=row["type"],
            label=row["label"],
            metadata=row.get("metadata") or {},
        )

    def list_edges_for_node(self, node_id: str) -> list[GraphEdgeRecord]:
        query = """
            SELECT id, source_node_id, target_node_id, relationship_type, weight, metadata
            FROM graph_edges
            WHERE source_node_id = %(node_id)s OR target_node_id = %(node_id)s
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"node_id": node_id})
                rows = cur.fetchall()

        return [
            GraphEdgeRecord(
                id=row["id"],
                source_node_id=row["source_node_id"],
                target_node_id=row["target_node_id"],
                relationship_type=row["relationship_type"],
                weight=int(row.get("weight", 1)),
                metadata=row.get("metadata") or {},
            )
            for row in rows
        ]

    def list_nodes_by_ids(self, node_ids: list[str]) -> list[GraphNodeRecord]:
        if not node_ids:
            return []

        query = """
            SELECT id, type, label, metadata
            FROM graph_nodes
            WHERE id = ANY(%(node_ids)s)
            ORDER BY label ASC
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"node_ids": node_ids})
                rows = cur.fetchall()

        return [
            GraphNodeRecord(
                id=row["id"],
                type=row["type"],
                label=row["label"],
                metadata=row.get("metadata") or {},
            )
            for row in rows
        ]

    def list_content_by_filenames(self, filenames: list[str]) -> list[ContentRecord]:
        if not filenames:
            return []

        query = """
            SELECT id, title, type, published_at, guest, tags, filename
            FROM content
            WHERE filename = ANY(%(filenames)s)
            ORDER BY published_at DESC NULLS LAST, title ASC
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"filenames": filenames})
                rows = cur.fetchall()

        return [
            ContentRecord(
                id=row["id"],
                title=row["title"],
                content_type=row["type"],
                published_at=row.get("published_at"),
                guest=row.get("guest"),
                tags=list(row.get("tags") or []),
                filename=row["filename"],
            )
            for row in rows
        ]

    def get_content_summary(self, content_id: str) -> str | None:
        query = """
            SELECT summary
            FROM content
            WHERE id = %(content_id)s
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"content_id": content_id})
                row = cur.fetchone()

        if not row:
            return None
        return row.get("summary")

    def list_content_by_ids(self, content_ids: list[str]) -> list[ContentRecord]:
        if not content_ids:
            return []

        query = """
            SELECT id, title, type, published_at, guest, tags, filename
            FROM content
            WHERE id = ANY(%(content_ids)s)
            ORDER BY published_at DESC NULLS LAST, title ASC
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query, {"content_ids": content_ids})
                rows = cur.fetchall()

        return [
            ContentRecord(
                id=row["id"],
                title=row["title"],
                content_type=row["type"],
                published_at=row.get("published_at"),
                guest=row.get("guest"),
                tags=list(row.get("tags") or []),
                filename=row["filename"],
            )
            for row in rows
        ]
