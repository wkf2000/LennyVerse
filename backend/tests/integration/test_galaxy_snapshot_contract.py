from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.galaxy_build_service import SourceEdge, SourceNode
from backend.app.services.galaxy_query_service import GalaxyQueryService
from backend.app.services.galaxy_snapshot_store import GalaxySnapshotStore


class _ContractTopologySource:
    def __init__(self, *, fail_edges: bool = False) -> None:
        self._fail_edges = fail_edges

    def fetch_nodes(self) -> list[SourceNode]:
        return [
            SourceNode(
                id="doc:alpha",
                title="Alpha",
                source_type="newsletter",
                published_at=datetime(2026, 3, 1, tzinfo=UTC),
                tags=("ai", "product"),
                guest_names=("Lenny",),
            ),
            SourceNode(
                id="doc:beta",
                title="Beta",
                source_type="podcast",
                published_at=datetime(2026, 3, 2, tzinfo=UTC),
                tags=("growth",),
                guest_names=("Jane",),
            ),
        ]

    def fetch_edges(self) -> list[SourceEdge]:
        if self._fail_edges:
            raise RuntimeError("edge derivation unavailable")
        return [SourceEdge(source="doc:alpha", target="doc:beta", weight=2.2)]


def test_snapshot_contract_includes_expected_fields(tmp_path) -> None:
    service = GalaxyQueryService(
        topology_source=_ContractTopologySource(),
        snapshot_store=GalaxySnapshotStore(base_dir=tmp_path / "snapshots"),
    )
    client = TestClient(create_app(galaxy_service=service))

    response = client.get("/api/v1/galaxy/snapshot")
    assert response.status_code == 200
    payload = response.json()

    assert payload["schema_version"] == 1
    assert payload["compatibility"]["minimum_client_schema"] == 1
    assert len(payload["nodes"]) == 2
    assert len(payload["edges"]) == 1
    assert payload["filter_facets"]["source_types"] == ["newsletter", "podcast"]
    assert response.headers["X-Galaxy-Snapshot-Source"] == "neo4j"
    assert int(response.headers["X-Galaxy-Build-Ms"]) >= 0
    assert int(response.headers["X-Galaxy-Payload-Bytes"]) > 0


def test_snapshot_degrades_to_node_only_when_edges_fail(tmp_path) -> None:
    service = GalaxyQueryService(
        topology_source=_ContractTopologySource(fail_edges=True),
        snapshot_store=GalaxySnapshotStore(base_dir=tmp_path / "snapshots"),
    )
    client = TestClient(create_app(galaxy_service=service))

    snapshot_response = client.get("/api/v1/galaxy/snapshot")
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()
    assert len(snapshot_payload["nodes"]) == 2
    assert snapshot_payload["edges"] == []

    detail_response = client.get("/api/v1/galaxy/node/doc:alpha")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == "doc:alpha"
    assert detail_payload["reader_url"] == "/reader/doc:alpha"
