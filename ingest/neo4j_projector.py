"""Neo4j graph projection for LennyVerse ingestion."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from itertools import combinations
from typing import Any, Iterable, Mapping, TypedDict

from dotenv import load_dotenv
from neo4j import GraphDatabase


class ProjectionPayload(TypedDict):
    documents: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    guests: list[dict[str, Any]]
    tags: list[dict[str, Any]]
    concepts: list[dict[str, Any]]
    frameworks: list[dict[str, Any]]
    document_guests: list[dict[str, Any]]
    document_tags: list[dict[str, Any]]
    chunk_concepts: list[dict[str, Any]]
    chunk_frameworks: list[dict[str, Any]]


_GRAPH_LABELS = ("Document", "Chunk", "Guest", "Tag", "Concept", "Framework")

_CONSTRAINT_STATEMENTS: tuple[str, ...] = (
    "CREATE CONSTRAINT lv_document_id IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lv_chunk_id IF NOT EXISTS FOR (n:Chunk) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lv_guest_id IF NOT EXISTS FOR (n:Guest) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lv_tag_id IF NOT EXISTS FOR (n:Tag) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lv_concept_id IF NOT EXISTS FOR (n:Concept) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT lv_framework_id IF NOT EXISTS FOR (n:Framework) REQUIRE n.id IS UNIQUE",
)


def _projection_batch_size() -> int:
    raw = os.environ.get("NEO4J_PROJECTION_BATCH_SIZE", "500").strip()
    try:
        n = int(raw)
    except ValueError as e:
        raise ValueError(f"Invalid NEO4J_PROJECTION_BATCH_SIZE: {raw!r}") from e
    if n < 1:
        raise ValueError("NEO4J_PROJECTION_BATCH_SIZE must be >= 1")
    return n


def _connect_driver():
    load_dotenv()
    uri = os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "")
    return GraphDatabase.driver(uri, auth=(user, password))


def _ensure_constraints(session: Any) -> None:
    for cypher in _CONSTRAINT_STATEMENTS:
        session.run(cypher)


def _clear_projection_scope(session: Any) -> None:
    session.run(
        """
        MATCH (n)
        WHERE ANY(l IN labels(n) WHERE l IN $labels)
        DETACH DELETE n
        """,
        labels=list(_GRAPH_LABELS),
    )


def _props_for_node(row: Mapping[str, Any], *, skip: frozenset[str]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in skip and v is not None}


def _upsert_labeled_nodes_batched(
    session: Any,
    *,
    label: str,
    rows: list[Mapping[str, Any]],
    batch_size: int,
    skip_keys: frozenset[str],
) -> int:
    if not rows:
        return 0
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        payload = [{"id": str(r["id"]), "props": _props_for_node(r, skip=skip_keys)} for r in batch]
        session.run(
            f"""
            UNWIND $batch AS row
            MERGE (n:{label} {{id: row.id}})
            SET n += row.props
            """,
            batch=payload,
        )
        total += len(batch)
    return total


def _upsert_part_of_batched(
    session: Any,
    *,
    chunk_rows: list[Mapping[str, Any]],
    batch_size: int,
) -> int:
    if not chunk_rows:
        return 0
    total = 0
    for i in range(0, len(chunk_rows), batch_size):
        batch = chunk_rows[i : i + batch_size]
        payload = [
            {"chunk_id": str(r["id"]), "document_id": str(r["document_id"])}
            for r in batch
        ]
        session.run(
            """
            UNWIND $batch AS row
            MATCH (c:Chunk {id: row.chunk_id})
            MATCH (d:Document {id: row.document_id})
            MERGE (c)-[r:PART_OF]->(d)
            """,
            batch=payload,
        )
        total += len(batch)
    return total


def _rel_rows_from_edges(edges: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for edge in edges:
        props = edge.get("properties")
        out.append(
            {
                "start_id": str(edge["start_id"]),
                "end_id": str(edge["end_id"]),
                "properties": dict(props) if isinstance(props, Mapping) else {},
            }
        )
    return out


def _upsert_relationships_batched(
    session: Any,
    *,
    rel_type: str,
    start_label: str,
    end_label: str,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> int:
    if not rows:
        return 0
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        session.run(
            f"""
            UNWIND $batch AS row
            MATCH (a:{start_label} {{id: row.start_id}})
            MATCH (b:{end_label} {{id: row.end_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += coalesce(row.properties, {{}})
            """,
            batch=batch,
        )
        total += len(batch)
    return total


def project_to_neo4j(payload: ProjectionPayload, *, clear_first: bool = False) -> dict[str, int]:
    """Project ingestion payload into Neo4j: constraints, optional clear, batched upserts.

    Loads ``NEO4J_URI``, ``NEO4J_USER``, ``NEO4J_PASSWORD`` from the environment (``.env`` via
    ``load_dotenv``). Batch size defaults to 500; override with ``NEO4J_PROJECTION_BATCH_SIZE``.
    """
    batch_size = _projection_batch_size()
    t0 = time.monotonic()
    stats: dict[str, int] = {}

    chunk_to_document = {str(c["id"]): str(c["document_id"]) for c in payload["chunks"]}
    mentions_edges = build_mentions_concept_edges(payload["chunk_concepts"], chunk_to_document)
    uses_framework_edges = build_uses_framework_edges(payload["chunk_frameworks"], chunk_to_document)
    related_edges = build_related_to_edges(payload["chunk_concepts"], chunk_to_document)
    guest_edges = build_features_guest_edges(payload["document_guests"])
    tag_edges = build_has_tag_edges(payload["document_tags"])

    driver = _connect_driver()
    try:
        with driver.session() as session:
            _ensure_constraints(session)
            if clear_first:
                _clear_projection_scope(session)

            stats["documents"] = _upsert_labeled_nodes_batched(
                session,
                label="Document",
                rows=payload["documents"],
                batch_size=batch_size,
                skip_keys=frozenset({"id", "raw_markdown"}),
            )
            stats["chunks"] = _upsert_labeled_nodes_batched(
                session,
                label="Chunk",
                rows=payload["chunks"],
                batch_size=batch_size,
                skip_keys=frozenset({"id"}),
            )
            stats["guests"] = _upsert_labeled_nodes_batched(
                session,
                label="Guest",
                rows=payload["guests"],
                batch_size=batch_size,
                skip_keys=frozenset({"id"}),
            )
            stats["tags"] = _upsert_labeled_nodes_batched(
                session,
                label="Tag",
                rows=payload["tags"],
                batch_size=batch_size,
                skip_keys=frozenset({"id"}),
            )
            stats["concepts"] = _upsert_labeled_nodes_batched(
                session,
                label="Concept",
                rows=payload["concepts"],
                batch_size=batch_size,
                skip_keys=frozenset({"id"}),
            )
            stats["frameworks"] = _upsert_labeled_nodes_batched(
                session,
                label="Framework",
                rows=payload["frameworks"],
                batch_size=batch_size,
                skip_keys=frozenset({"id"}),
            )

            stats["rels_part_of"] = _upsert_part_of_batched(
                session, chunk_rows=payload["chunks"], batch_size=batch_size
            )
            stats["rels_features_guest"] = _upsert_relationships_batched(
                session,
                rel_type="FEATURES_GUEST",
                start_label="Document",
                end_label="Guest",
                rows=_rel_rows_from_edges(guest_edges),
                batch_size=batch_size,
            )
            stats["rels_has_tag"] = _upsert_relationships_batched(
                session,
                rel_type="HAS_TAG",
                start_label="Document",
                end_label="Tag",
                rows=_rel_rows_from_edges(tag_edges),
                batch_size=batch_size,
            )
            stats["rels_mentions_concept"] = _upsert_relationships_batched(
                session,
                rel_type="MENTIONS_CONCEPT",
                start_label="Document",
                end_label="Concept",
                rows=_rel_rows_from_edges(mentions_edges),
                batch_size=batch_size,
            )
            stats["rels_uses_framework"] = _upsert_relationships_batched(
                session,
                rel_type="USES_FRAMEWORK",
                start_label="Document",
                end_label="Framework",
                rows=_rel_rows_from_edges(uses_framework_edges),
                batch_size=batch_size,
            )
            stats["rels_related_to"] = _upsert_relationships_batched(
                session,
                rel_type="RELATED_TO",
                start_label="Concept",
                end_label="Concept",
                rows=_rel_rows_from_edges(related_edges),
                batch_size=batch_size,
            )
    finally:
        driver.close()

    stats["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    return stats


def _confidence_value(raw: Any) -> float:
    if raw is None:
        return 0.0
    return float(raw)


def _rollup_chunk_entity_edges(
    rows: Iterable[Mapping[str, Any]],
    chunk_to_document: Mapping[str, str],
    *,
    entity_field: str,
    rel_type: str,
) -> list[dict[str, Any]]:
    weights: dict[tuple[str, str], float] = defaultdict(float)
    evidence_chunks: dict[tuple[str, str], set[str]] = defaultdict(set)

    for row in rows:
        chunk_id = str(row["chunk_id"])
        document_id = chunk_to_document.get(chunk_id)
        if document_id is None:
            continue
        entity_id = str(row[entity_field])
        key = (document_id, entity_id)
        weights[key] += _confidence_value(row.get("confidence"))
        evidence_chunks[key].add(chunk_id)

    out: list[dict[str, Any]] = []
    for (document_id, entity_id) in sorted(weights.keys()):
        out.append(
            {
                "rel_type": rel_type,
                "start_id": document_id,
                "end_id": entity_id,
                "properties": {
                    "weight": weights[(document_id, entity_id)],
                    "evidence_count": len(evidence_chunks[(document_id, entity_id)]),
                },
            }
        )
    return out


def build_mentions_concept_edges(
    chunk_concepts: Iterable[Mapping[str, Any]],
    chunk_to_document: Mapping[str, str],
) -> list[dict[str, Any]]:
    return _rollup_chunk_entity_edges(
        chunk_concepts,
        chunk_to_document,
        entity_field="concept_id",
        rel_type="MENTIONS_CONCEPT",
    )


def build_uses_framework_edges(
    chunk_frameworks: Iterable[Mapping[str, Any]],
    chunk_to_document: Mapping[str, str],
) -> list[dict[str, Any]]:
    return _rollup_chunk_entity_edges(
        chunk_frameworks,
        chunk_to_document,
        entity_field="framework_id",
        rel_type="USES_FRAMEWORK",
    )


def build_related_to_edges(
    chunk_concepts: Iterable[Mapping[str, Any]],
    chunk_to_document: Mapping[str, str],
) -> list[dict[str, Any]]:
    document_to_concepts: dict[str, set[str]] = defaultdict(set)
    for row in chunk_concepts:
        chunk_id = str(row["chunk_id"])
        document_id = chunk_to_document.get(chunk_id)
        if document_id is None:
            continue
        document_to_concepts[document_id].add(str(row["concept_id"]))

    pair_to_documents: dict[tuple[str, str], set[str]] = defaultdict(set)
    for document_id, concepts in document_to_concepts.items():
        ordered = sorted(concepts)
        for a, b in combinations(ordered, 2):
            if a == b:
                continue
            lower, higher = (a, b) if a < b else (b, a)
            pair_to_documents[(lower, higher)].add(document_id)

    edges: list[dict[str, Any]] = []
    for (lower_id, higher_id) in sorted(pair_to_documents.keys()):
        edges.append(
            {
                "rel_type": "RELATED_TO",
                "start_id": lower_id,
                "end_id": higher_id,
                "properties": {
                    "weight": len(pair_to_documents[(lower_id, higher_id)]),
                    "method": "cooccurrence_p0",
                },
            }
        )
    return edges


def build_features_guest_edges(
    document_guests: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    edges = [
        {
            "rel_type": "FEATURES_GUEST",
            "start_id": str(row["document_id"]),
            "end_id": str(row["guest_id"]),
            "properties": {},
        }
        for row in document_guests
    ]
    edges.sort(key=lambda e: (e["start_id"], e["end_id"]))
    return edges


def build_has_tag_edges(document_tags: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    edges = [
        {
            "rel_type": "HAS_TAG",
            "start_id": str(row["document_id"]),
            "end_id": str(row["tag_id"]),
            "properties": {},
        }
        for row in document_tags
    ]
    edges.sort(key=lambda e: (e["start_id"], e["end_id"]))
    return edges
