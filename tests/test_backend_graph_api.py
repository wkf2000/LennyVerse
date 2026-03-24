from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backend_api.graph_repository import ContentRecord, GraphEdgeRecord, GraphNodeRecord
from backend_api.graph_service import GraphService
from backend_api.main import app, get_graph_service


class FakeGraphRepository:
    def __init__(self) -> None:
        self._nodes = [
            GraphNodeRecord(
                id="topic::growth",
                type="topic",
                label="growth",
                metadata={},
            ),
            GraphNodeRecord(
                id="guest::ada",
                type="guest",
                label="Ada Chen Rekhi",
                metadata={},
            ),
            GraphNodeRecord(
                id="content::ada-podcast",
                type="content",
                label="Ada Chen Rekhi",
                metadata={"filename": "03-podcasts/ada-chen-rekhi.md", "date": "2023-04-16"},
            ),
        ]
        self._edges = [
            GraphEdgeRecord(
                id="appeared_in::guest::ada::content::ada-podcast",
                source_node_id="guest::ada",
                target_node_id="content::ada-podcast",
                relationship_type="appeared_in",
                weight=1,
                metadata={},
            ),
            GraphEdgeRecord(
                id="tagged_with::content::ada-podcast::topic::growth",
                source_node_id="content::ada-podcast",
                target_node_id="topic::growth",
                relationship_type="tagged_with",
                weight=1,
                metadata={},
            ),
            GraphEdgeRecord(
                id="discusses::guest::ada::topic::growth",
                source_node_id="guest::ada",
                target_node_id="topic::growth",
                relationship_type="discusses",
                weight=1,
                metadata={},
            ),
        ]
        self._content = [
            ContentRecord(
                id="podcast::ada-chen-rekhi",
                title="Ada Chen Rekhi",
                content_type="podcast",
                published_at=date(2023, 4, 16),
                guest="Ada Chen Rekhi",
                tags=["growth"],
                filename="03-podcasts/ada-chen-rekhi.md",
            )
        ]

    def list_nodes(self) -> list[GraphNodeRecord]:
        return self._nodes

    def list_edges(self) -> list[GraphEdgeRecord]:
        return self._edges

    def get_node_by_id(self, node_id: str) -> GraphNodeRecord | None:
        for node in self._nodes:
            if node.id == node_id:
                return node
        return None

    def list_edges_for_node(self, node_id: str) -> list[GraphEdgeRecord]:
        return [
            edge
            for edge in self._edges
            if edge.source_node_id == node_id or edge.target_node_id == node_id
        ]

    def list_nodes_by_ids(self, node_ids: list[str]) -> list[GraphNodeRecord]:
        node_id_set = set(node_ids)
        return [node for node in self._nodes if node.id in node_id_set]

    def list_content_by_filenames(self, filenames: list[str]) -> list[ContentRecord]:
        filename_set = set(filenames)
        return [item for item in self._content if item.filename in filename_set]

    def list_content_by_ids(self, content_ids: list[str]) -> list[ContentRecord]:
        content_id_set = set(content_ids)
        return [item for item in self._content if item.id in content_id_set]


def test_get_graph_returns_nodes_and_edges() -> None:
    app.dependency_overrides[get_graph_service] = lambda: GraphService(FakeGraphRepository())
    client = TestClient(app)

    response = client.get("/api/graph")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 3
    assert len(payload["edges"]) == 3
    assert {"sourceNodeId", "targetNodeId", "relationshipType"} <= set(payload["edges"][0].keys())

    app.dependency_overrides.clear()


def test_get_graph_supports_topic_filter() -> None:
    app.dependency_overrides[get_graph_service] = lambda: GraphService(FakeGraphRepository())
    client = TestClient(app)

    response = client.get("/api/graph", params={"topic": "growth"})

    assert response.status_code == 200
    payload = response.json()
    node_ids = {node["id"] for node in payload["nodes"]}
    assert "topic::growth" in node_ids
    assert "content::ada-podcast" in node_ids

    app.dependency_overrides.clear()


def test_get_graph_node_returns_detail() -> None:
    app.dependency_overrides[get_graph_service] = lambda: GraphService(FakeGraphRepository())
    client = TestClient(app)

    response = client.get("/api/graph/nodes/topic::growth")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node"]["id"] == "topic::growth"
    assert payload["connected_node_count"] == 2
    assert payload["related_content"][0]["title"] == "Ada Chen Rekhi"

    app.dependency_overrides.clear()


def test_get_graph_node_returns_related_content_without_filename_metadata() -> None:
    repository = FakeGraphRepository()
    for index, node in enumerate(repository._nodes):
        if node.id == "content::ada-chen-rekhi":
            repository._nodes[index] = GraphNodeRecord(
                id=node.id,
                type=node.type,
                label=node.label,
                metadata={"date": "2023-04-16"},
            )
            break

    app.dependency_overrides[get_graph_service] = lambda: GraphService(repository)
    client = TestClient(app)

    response = client.get("/api/graph/nodes/topic::growth")

    assert response.status_code == 200
    payload = response.json()
    assert payload["related_content"]
    assert payload["related_content"][0]["title"] == "Ada Chen Rekhi"

    app.dependency_overrides.clear()
