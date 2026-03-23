from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from slugify import slugify

from data_pipeline.models import GraphEdge, GraphNode


def _content_node_id(filename: str, title: str) -> str:
    stem = Path(filename).stem if filename else title
    return f"content::{slugify(stem)}"


def _guest_node_id(guest: str) -> str:
    return f"guest::{slugify(guest)}"


def _topic_node_id(tag: str) -> str:
    return f"topic::{slugify(tag)}"


def _edge_id(source: str, target: str, relationship: str) -> str:
    return f"{relationship}::{source}::{target}"


def _iter_index_records(index_payload: dict[str, Any]) -> list[dict[str, Any]]:
    podcasts = index_payload.get("podcasts", [])
    newsletters = index_payload.get("newsletters", [])
    for row in podcasts:
        row["type"] = "podcast"
    for row in newsletters:
        row["type"] = "newsletter"
    return [*podcasts, *newsletters]


def build_graph_from_index(index_path: Path) -> tuple[list[GraphNode], list[GraphEdge]]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    records = _iter_index_records(payload)

    nodes: dict[str, GraphNode] = {}
    edge_counter: Counter[tuple[str, str, str]] = Counter()

    for row in records:
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        filename = str(row.get("filename") or "")
        tags = [str(tag).strip() for tag in row.get("tags", []) if str(tag).strip()]
        guest = str(row.get("guest") or "").strip()

        content_node_id = _content_node_id(filename, title)
        nodes[content_node_id] = GraphNode(
            id=content_node_id,
            type="content",
            label=title,
            metadata={
                "content_type": row.get("type"),
                "filename": filename,
                "date": row.get("date"),
            },
        )

        if guest:
            guest_node_id = _guest_node_id(guest)
            nodes[guest_node_id] = GraphNode(id=guest_node_id, type="guest", label=guest)
            edge_counter[(guest_node_id, content_node_id, "appeared_in")] += 1

        for tag in tags:
            topic_node_id = _topic_node_id(tag)
            nodes[topic_node_id] = GraphNode(id=topic_node_id, type="topic", label=tag)
            edge_counter[(content_node_id, topic_node_id, "tagged_with")] += 1
            if guest:
                edge_counter[(guest_node_id, topic_node_id, "discusses")] += 1

    edges: list[GraphEdge] = []
    for (source, target, rel), weight in sorted(edge_counter.items()):
        edges.append(
            GraphEdge(
                id=_edge_id(source, target, rel),
                source_node_id=source,
                target_node_id=target,
                relationship_type=rel,
                weight=weight,
            )
        )

    return list(nodes.values()), edges
