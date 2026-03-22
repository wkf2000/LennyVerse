from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.app.services.galaxy_build_service import SourceEdge, SourceNode
from backend.app.services.galaxy_query_service import GalaxyQueryService, GalaxySnapshotUnavailableError
from backend.app.services.galaxy_snapshot_store import GalaxySnapshotStore


class _FakeTopologySource:
    def __init__(self, *, fail_edges: bool = False, fail_nodes: bool = False) -> None:
        self._fail_edges = fail_edges
        self._fail_nodes = fail_nodes

    def fetch_nodes(self) -> list[SourceNode]:
        if self._fail_nodes:
            raise RuntimeError("nodes down")
        return [
            SourceNode(
                id="doc:alpha",
                title="Alpha",
                source_type="newsletter",
                published_at=datetime(2026, 1, 1, tzinfo=UTC),
                tags=("ai",),
                guest_names=("Lenny",),
            ),
            SourceNode(
                id="doc:beta",
                title="Beta",
                source_type="podcast",
                published_at=datetime(2026, 2, 1, tzinfo=UTC),
                tags=("product",),
                guest_names=("Jane",),
            ),
        ]

    def fetch_edges(self) -> list[SourceEdge]:
        if self._fail_edges:
            raise RuntimeError("edge derivation unavailable")
        return [SourceEdge(source="doc:alpha", target="doc:beta", weight=2.0)]


def test_builds_snapshot_from_topology_and_persists_artifacts(tmp_path) -> None:
    store = GalaxySnapshotStore(base_dir=tmp_path / "galaxy-snapshots")
    service = GalaxyQueryService(
        topology_source=_FakeTopologySource(),
        snapshot_store=store,
    )

    snapshot = service.get_snapshot()
    latest = tmp_path / "galaxy-snapshots" / "latest.json"
    versioned = tmp_path / "galaxy-snapshots" / f"{snapshot.version}.json"

    assert len(snapshot.nodes) == 2
    assert len(snapshot.edges) == 1
    assert latest.exists()
    assert versioned.exists()
    assert service.last_snapshot_stats["source"] == "neo4j"


def test_edges_failure_returns_node_only_snapshot(tmp_path) -> None:
    service = GalaxyQueryService(
        topology_source=_FakeTopologySource(fail_edges=True),
        snapshot_store=GalaxySnapshotStore(base_dir=tmp_path / "galaxy-snapshots"),
    )

    snapshot = service.get_snapshot()
    assert len(snapshot.nodes) == 2
    assert snapshot.edges == []
    assert "edge derivation unavailable" in str(service.last_snapshot_stats["edge_derivation_error"])


def test_node_fetch_failure_raises_unavailable_error() -> None:
    service = GalaxyQueryService(topology_source=_FakeTopologySource(fail_nodes=True), snapshot_store=None)
    with pytest.raises(GalaxySnapshotUnavailableError, match="Failed to load galaxy node topology"):
        service.get_snapshot()
