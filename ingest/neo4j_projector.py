"""Neo4j graph projection for LennyVerse ingestion."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Any, Iterable, Mapping


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
