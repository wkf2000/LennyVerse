from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from data_pipeline.models import ChunkRecord, GraphEdge, GraphNode, ParsedDocument


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


class Database:
    def __init__(self, db_url: str) -> None:
        self._db_url = db_url

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def execute_sql_file(self, path: Path) -> None:
        sql = path.read_text(encoding="utf-8")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def upsert_contents(self, docs: Iterable[ParsedDocument]) -> None:
        query = """
            INSERT INTO content (
                id, type, title, published_at, tags, guest, word_count, filename,
                subtitle, description, raw_metadata
            ) VALUES (
                %(id)s, %(type)s, %(title)s, %(published_at)s, %(tags)s, %(guest)s, %(word_count)s, %(filename)s,
                %(subtitle)s, %(description)s, %(raw_metadata)s
            )
            ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                title = EXCLUDED.title,
                published_at = EXCLUDED.published_at,
                tags = EXCLUDED.tags,
                guest = EXCLUDED.guest,
                word_count = EXCLUDED.word_count,
                filename = EXCLUDED.filename,
                subtitle = EXCLUDED.subtitle,
                description = EXCLUDED.description,
                raw_metadata = EXCLUDED.raw_metadata,
                updated_at = now();
        """
        payload = [
            {
                "id": doc.id,
                "type": doc.type,
                "title": doc.title,
                "published_at": doc.date,
                "tags": doc.tags,
                "guest": doc.guest,
                "word_count": doc.word_count,
                "filename": doc.filename,
                "subtitle": doc.subtitle,
                "description": doc.description,
                "raw_metadata": Json(doc.raw_metadata),
            }
            for doc in docs
        ]

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, payload)
            conn.commit()

    def upsert_chunks(self, chunks: Iterable[ChunkRecord]) -> None:
        query = """
            INSERT INTO chunks (
                id, content_id, chunk_index, text, section_header, embedding
            ) VALUES (
                %(id)s, %(content_id)s, %(chunk_index)s, %(text)s, %(section_header)s, %(embedding)s::vector
            )
            ON CONFLICT (id) DO UPDATE SET
                content_id = EXCLUDED.content_id,
                chunk_index = EXCLUDED.chunk_index,
                text = EXCLUDED.text,
                section_header = EXCLUDED.section_header,
                embedding = EXCLUDED.embedding,
                updated_at = now();
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                for chunk in chunks:
                    if not chunk.embedding:
                        continue
                    cur.execute(
                        query,
                        {
                            "id": chunk.id,
                            "content_id": chunk.content_id,
                            "chunk_index": chunk.chunk_index,
                            "text": chunk.text,
                            "section_header": chunk.section_header,
                            "embedding": _vector_literal(chunk.embedding),
                        },
                    )
            conn.commit()

    def upsert_graph_nodes(self, nodes: Iterable[GraphNode]) -> None:
        query = """
            INSERT INTO graph_nodes (id, type, label, metadata)
            VALUES (%(id)s, %(type)s, %(label)s, %(metadata)s)
            ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                label = EXCLUDED.label,
                metadata = EXCLUDED.metadata,
                updated_at = now();
        """
        payload = [
            {"id": node.id, "type": node.type, "label": node.label, "metadata": Json(node.metadata)}
            for node in nodes
        ]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, payload)
            conn.commit()

    def upsert_graph_edges(self, edges: Iterable[GraphEdge]) -> None:
        query = """
            INSERT INTO graph_edges (
                id, source_node_id, target_node_id, relationship_type, weight, metadata
            ) VALUES (
                %(id)s, %(source_node_id)s, %(target_node_id)s, %(relationship_type)s, %(weight)s, %(metadata)s
            )
            ON CONFLICT (id) DO UPDATE SET
                source_node_id = EXCLUDED.source_node_id,
                target_node_id = EXCLUDED.target_node_id,
                relationship_type = EXCLUDED.relationship_type,
                weight = EXCLUDED.weight,
                metadata = EXCLUDED.metadata,
                updated_at = now();
        """
        payload = [
            {
                "id": edge.id,
                "source_node_id": edge.source_node_id,
                "target_node_id": edge.target_node_id,
                "relationship_type": edge.relationship_type,
                "weight": edge.weight,
                "metadata": Json(edge.metadata),
            }
            for edge in edges
        ]
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(query, payload)
            conn.commit()

    def table_counts(self) -> dict[str, int]:
        query = """
            SELECT
                (SELECT count(*) FROM content) AS content_count,
                (SELECT count(*) FROM chunks) AS chunk_count,
                (SELECT count(*) FROM graph_nodes) AS graph_node_count,
                (SELECT count(*) FROM graph_edges) AS graph_edge_count
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                row = cur.fetchone() or {}
        return {k: int(v) for k, v in row.items()}

    def sample_similarity(self, query_embedding: list[float], limit: int = 3) -> list[dict]:
        sql = """
            SELECT c.title, c.filename, ch.chunk_index, left(ch.text, 180) AS excerpt
            FROM chunks ch
            JOIN content c ON c.id = ch.content_id
            ORDER BY ch.embedding <=> %(embedding)s::vector
            LIMIT %(limit)s
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    sql,
                    {
                        "embedding": _vector_literal(query_embedding),
                        "limit": limit,
                    },
                )
                rows = cur.fetchall()
        return [json.loads(json.dumps(row, default=str)) for row in rows]

    def fetch_unsummarized_content(self, force: bool = False) -> list[dict]:
        if force:
            sql = "SELECT id, filename, title FROM content ORDER BY id"
        else:
            sql = "SELECT id, filename, title FROM content WHERE summary IS NULL ORDER BY id"
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchall()

    def update_summary(self, content_id: str, summary: str) -> None:
        sql = "UPDATE content SET summary = %(summary)s, updated_at = now() WHERE id = %(id)s"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"summary": summary, "id": content_id})
            conn.commit()
