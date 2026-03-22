from __future__ import annotations

from datetime import UTC, datetime

import json

from backend.app.services.galaxy_build_service import GalaxyBuildService, SourceEdge, SourceNode


def test_build_snapshot_is_deterministic_for_layout() -> None:
    service = GalaxyBuildService(seed=77)
    nodes = [
        SourceNode(id="doc:a", title="A", source_type="newsletter", tags=("product",)),
        SourceNode(id="doc:b", title="B", source_type="podcast", tags=("growth",)),
    ]
    edges = [SourceEdge(source="doc:a", target="doc:b", weight=3.2)]

    snapshot_a = service.build_snapshot(nodes=nodes, edges=edges)
    snapshot_b = service.build_snapshot(nodes=nodes, edges=edges)

    coords_a = {node.id: node.position.model_dump() for node in snapshot_a.nodes}
    coords_b = {node.id: node.position.model_dump() for node in snapshot_b.nodes}
    assert coords_a == coords_b
    assert snapshot_a.edges[0].edge_tier == "high"
    assert snapshot_a.filter_facets.tags == ["growth", "product"]


def test_build_snapshot_drops_invalid_edges_and_computes_facets() -> None:
    service = GalaxyBuildService(seed=11)
    nodes = [
        SourceNode(
            id="doc:a",
            title="A",
            source_type="newsletter",
            published_at=datetime(2025, 1, 1, tzinfo=UTC),
            tags=("ai",),
            guest_names=("Lenny",),
        ),
        SourceNode(
            id="doc:b",
            title="B",
            source_type="podcast",
            published_at=datetime(2025, 6, 1, tzinfo=UTC),
            tags=("product",),
            guest_names=("Jane",),
        ),
    ]
    edges = [
        SourceEdge(source="doc:a", target="doc:b", weight=1.8),
        SourceEdge(source="doc:a", target="doc:missing", weight=5.0),
        SourceEdge(source="doc:b", target="doc:b", weight=2.0),
    ]

    snapshot = service.build_snapshot(nodes=nodes, edges=edges)

    assert len(snapshot.edges) == 1
    assert snapshot.edges[0].edge_tier == "medium"
    assert snapshot.filter_facets.guests == ["Jane", "Lenny"]
    assert snapshot.filter_facets.date_min == datetime(2025, 1, 1, tzinfo=UTC)
    assert snapshot.filter_facets.date_max == datetime(2025, 6, 1, tzinfo=UTC)
    assert snapshot.compatibility.current_schema == 1


def test_fallback_snapshot_is_empty_but_valid() -> None:
    service = GalaxyBuildService()
    snapshot = service.build_fallback_snapshot()

    assert snapshot.version == "snapshot-empty"
    assert snapshot.nodes == []
    assert snapshot.edges == []
    assert snapshot.clusters == []


def test_build_snapshot_supports_638_nodes_reproducibly() -> None:
    service = GalaxyBuildService(seed=123)
    nodes = [
        SourceNode(
            id=f"doc:{idx:03d}",
            title=f"Doc {idx}",
            source_type="newsletter" if idx % 2 == 0 else "podcast",
            tags=(f"tag-{idx % 12}",),
            guest_names=(f"guest-{idx % 20}",),
        )
        for idx in range(638)
    ]
    edges = [
        SourceEdge(source=f"doc:{idx:03d}", target=f"doc:{idx + 1:03d}", weight=1.0 + (idx % 4) * 0.5)
        for idx in range(0, 637)
    ]

    snapshot_a = service.build_snapshot(nodes=nodes, edges=edges)
    snapshot_b = service.build_snapshot(nodes=nodes, edges=edges)

    assert len(snapshot_a.nodes) == 638
    assert len(snapshot_a.edges) == 637
    assert snapshot_a.filter_facets.tags[0].startswith("tag-")
    coords_a = [node.position.model_dump() for node in snapshot_a.nodes]
    coords_b = [node.position.model_dump() for node in snapshot_b.nodes]
    assert coords_a == coords_b
    payload_bytes = len(json.dumps(snapshot_a.model_dump(mode="json"), ensure_ascii=True))
    assert payload_bytes > 0
