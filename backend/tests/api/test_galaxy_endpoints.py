from __future__ import annotations

import json

from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.galaxy_query_service import GalaxyNodeNotFoundError, GalaxyQueryService


def test_get_snapshot_returns_payload(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "version": "snapshot-test",
                "generated_at": "2026-03-21T00:00:00+00:00",
                "schema_version": 1,
                "compatibility": {"minimum_client_schema": 1, "current_schema": 1},
                "bounds": {"x": [-1, 1], "y": [-1, 1], "z": [-1, 1]},
                "nodes": [
                    {
                        "id": "doc:alpha",
                        "title": "Alpha",
                        "source_type": "newsletter",
                        "published_at": "2026-01-01T00:00:00+00:00",
                        "tags": ["ai"],
                        "guest_names": ["Lenny"],
                        "cluster_id": "cluster:tag:ai",
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "influence_score": 0.4,
                        "star_size": 1.5,
                        "star_brightness": 0.6,
                    }
                ],
                "edges": [],
                "clusters": [
                    {
                        "id": "cluster:tag:ai",
                        "label": "Tag Ai",
                        "centroid": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "node_count": 1,
                        "dominant_tags": ["ai"],
                    }
                ],
                "filter_facets": {
                    "tags": ["ai"],
                    "guests": ["Lenny"],
                    "date_min": "2026-01-01T00:00:00+00:00",
                    "date_max": "2026-01-01T00:00:00+00:00",
                    "source_types": ["newsletter"],
                },
            }
        ),
        encoding="utf-8",
    )
    app = create_app(galaxy_service=GalaxyQueryService(snapshot_path=snapshot_path))
    client = TestClient(app)

    response = client.get("/api/v1/galaxy/snapshot")
    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "snapshot-test"
    assert payload["schema_version"] == 1
    assert payload["filter_facets"]["tags"] == ["ai"]
    assert response.headers["X-Galaxy-Snapshot-Source"] == "artifact"
    assert int(response.headers["X-Galaxy-Payload-Bytes"]) > 0


def test_get_node_404_for_missing_node(tmp_path) -> None:
    app = create_app(galaxy_service=GalaxyQueryService(snapshot_path=tmp_path / "does-not-exist.json"))
    client = TestClient(app)

    response = client.get("/api/v1/galaxy/node/doc:nope")
    assert response.status_code == 404
    assert response.json()["detail"] == "Node not found: doc:nope"


def test_get_node_returns_detail_for_existing_node(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "version": "snapshot-test",
                "generated_at": "2026-03-21T00:00:00+00:00",
                "schema_version": 1,
                "compatibility": {"minimum_client_schema": 1, "current_schema": 1},
                "bounds": {"x": [-1, 1], "y": [-1, 1], "z": [-1, 1]},
                "nodes": [
                    {
                        "id": "doc:alpha",
                        "title": "Alpha",
                        "source_type": "newsletter",
                        "published_at": "2026-01-01T00:00:00+00:00",
                        "tags": ["ai"],
                        "guest_names": ["Lenny"],
                        "cluster_id": "cluster:tag:ai",
                        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "influence_score": 0.4,
                        "star_size": 1.5,
                        "star_brightness": 0.6,
                    }
                ],
                "edges": [],
                "clusters": [],
                "filter_facets": {
                    "tags": ["ai"],
                    "guests": ["Lenny"],
                    "date_min": "2026-01-01T00:00:00+00:00",
                    "date_max": "2026-01-01T00:00:00+00:00",
                    "source_types": ["newsletter"],
                },
            }
        ),
        encoding="utf-8",
    )
    app = create_app(galaxy_service=GalaxyQueryService(snapshot_path=snapshot_path))
    client = TestClient(app)

    response = client.get("/api/v1/galaxy/node/doc:alpha")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "doc:alpha"
    assert payload["reader_url"] == "/reader/doc:alpha"
