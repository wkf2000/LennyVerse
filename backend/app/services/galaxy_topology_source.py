from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Any

from dotenv import load_dotenv
from neo4j import GraphDatabase

from backend.app.services.galaxy_build_service import SourceEdge, SourceNode


@dataclass(frozen=True)
class EntityMembership:
    document_id: str
    entity_id: str
    weight: float


class Neo4jTopologySource:
    def __init__(self, *, uri: str | None = None, user: str | None = None, password: str | None = None) -> None:
        load_dotenv()
        self._uri = uri or os.environ.get("NEO4J_URI", "bolt://127.0.0.1:7687")
        self._user = user or os.environ.get("NEO4J_USER", "neo4j")
        self._password = password if password is not None else os.environ.get("NEO4J_PASSWORD", "")
        self._max_edges = int(os.environ.get("GALAXY_MAX_EDGES", "6000"))

    def fetch_nodes(self) -> list[SourceNode]:
        with self._driver().session() as session:
            records = session.run(
                """
                MATCH (d:Document)
                OPTIONAL MATCH (d)-[:HAS_TAG]->(t:Tag)
                OPTIONAL MATCH (d)-[:FEATURES_GUEST]->(g:Guest)
                WITH d,
                     [name IN collect(DISTINCT t.name) WHERE name IS NOT NULL] AS tags,
                     [name IN collect(DISTINCT g.name) WHERE name IS NOT NULL] AS guest_names
                RETURN d.id AS id,
                       coalesce(d.title, d.id) AS title,
                       coalesce(d.source_type, 'unknown') AS source_type,
                       d.published_at AS published_at,
                       tags,
                       guest_names
                ORDER BY id
                """
            )
            return [
                SourceNode(
                    id=str(row["id"]),
                    title=str(row["title"]),
                    source_type=str(row["source_type"]),
                    published_at=_parse_optional_datetime(row["published_at"]),
                    tags=tuple(sorted(str(tag) for tag in row["tags"])),
                    guest_names=tuple(sorted(str(guest) for guest in row["guest_names"])),
                )
                for row in records
                if row["id"] is not None
            ]

    def fetch_edges(self) -> list[SourceEdge]:
        memberships = self._fetch_memberships()
        pair_weights: dict[tuple[str, str], float] = defaultdict(float)

        entity_to_docs: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for membership in memberships:
            entity_to_docs[membership.entity_id].append((membership.document_id, membership.weight))

        for docs in entity_to_docs.values():
            docs_sorted = sorted(docs, key=lambda item: item[0])
            for (doc_a, weight_a), (doc_b, weight_b) in combinations(docs_sorted, 2):
                if doc_a == doc_b:
                    continue
                source, target = (doc_a, doc_b) if doc_a < doc_b else (doc_b, doc_a)
                pair_weights[(source, target)] += weight_a + weight_b

        edges = [
            SourceEdge(source=source, target=target, weight=weight)
            for (source, target), weight in sorted(pair_weights.items(), key=lambda row: row[0])
        ]
        edges.sort(key=lambda edge: edge.weight, reverse=True)
        return edges[: self._max_edges]

    def _fetch_memberships(self) -> list[EntityMembership]:
        with self._driver().session() as session:
            rows = session.run(
                """
                MATCH (d:Document)-[r:MENTIONS_CONCEPT|USES_FRAMEWORK]->(e)
                RETURN d.id AS document_id, e.id AS entity_id, coalesce(r.weight, 1.0) AS weight
                ORDER BY document_id, entity_id
                """
            )
            return [
                EntityMembership(
                    document_id=str(row["document_id"]),
                    entity_id=str(row["entity_id"]),
                    weight=float(row["weight"]),
                )
                for row in rows
                if row["document_id"] is not None and row["entity_id"] is not None
            ]

    def _driver(self):
        return GraphDatabase.driver(self._uri, auth=(self._user, self._password))


def _parse_optional_datetime(raw: Any) -> datetime | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
