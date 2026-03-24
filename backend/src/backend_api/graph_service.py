from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend_api.graph_repository import GraphEdgeRecord, GraphNodeRecord, GraphRepository
from backend_api.schemas import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    NodeDetailResponse,
    NodeType,
    RelatedContentResponse,
)


@dataclass(slots=True)
class GraphFilters:
    node_types: set[NodeType] | None = None
    topic: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class GraphService:
    def __init__(self, repository: GraphRepository) -> None:
        self._repository = repository

    def get_graph(self, filters: GraphFilters) -> GraphResponse:
        nodes = self._repository.list_nodes()
        edges = self._repository.list_edges()

        node_map = {node.id: node for node in nodes}
        candidate_ids = set(node_map.keys())

        if filters.topic:
            topic_ids = {
                node.id
                for node in nodes
                if node.type == "topic" and filters.topic.lower() in node.label.lower()
            }
            topic_context_ids = _expand_neighbor_ids(topic_ids, edges) if topic_ids else set()
            candidate_ids &= topic_context_ids

        if filters.start_date or filters.end_date:
            content_ids = {
                node.id
                for node in nodes
                if node.type == "content"
                and _is_content_in_date_range(node, filters.start_date, filters.end_date)
            }
            date_context_ids = _expand_neighbor_ids(content_ids, edges) if content_ids else set()
            candidate_ids &= date_context_ids

        if filters.node_types:
            candidate_ids = {node_id for node_id in candidate_ids if node_map[node_id].type in filters.node_types}

        filtered_nodes = [node for node in nodes if node.id in candidate_ids]
        filtered_edges = [
            edge
            for edge in edges
            if edge.source_node_id in candidate_ids and edge.target_node_id in candidate_ids
        ]

        return GraphResponse(
            nodes=[_to_node_response(node) for node in filtered_nodes],
            edges=[_to_edge_response(edge) for edge in filtered_edges],
        )

    def get_node_detail(self, node_id: str) -> NodeDetailResponse | None:
        node = self._repository.get_node_by_id(node_id)
        if not node:
            return None

        related_edges = self._repository.list_edges_for_node(node_id)
        connected_ids = set()
        for edge in related_edges:
            if edge.source_node_id != node_id:
                connected_ids.add(edge.source_node_id)
            if edge.target_node_id != node_id:
                connected_ids.add(edge.target_node_id)

        related_nodes = self._repository.list_nodes_by_ids(sorted(connected_ids))
        content_filenames = [str(n.metadata.get("filename")) for n in related_nodes if n.type == "content" and n.metadata.get("filename")]
        related_content = self._repository.list_content_by_filenames(content_filenames)

        return NodeDetailResponse(
            node=_to_node_response(node),
            connected_node_count=len(connected_ids),
            related_content=[
                RelatedContentResponse(
                    id=content.id,
                    title=content.title,
                    content_type=content.content_type,
                    published_at=content.published_at,
                    guest=content.guest,
                    tags=content.tags,
                    filename=content.filename,
                )
                for content in related_content
            ],
        )


def _to_node_response(node: GraphNodeRecord) -> GraphNodeResponse:
    return GraphNodeResponse(id=node.id, type=node.type, label=node.label, metadata=node.metadata)


def _to_edge_response(edge: GraphEdgeRecord) -> GraphEdgeResponse:
    return GraphEdgeResponse(
        id=edge.id,
        sourceNodeId=edge.source_node_id,
        targetNodeId=edge.target_node_id,
        relationshipType=edge.relationship_type,
        weight=edge.weight,
        metadata=edge.metadata,
    )


def _expand_neighbor_ids(seed_ids: set[str], edges: list[GraphEdgeRecord]) -> set[str]:
    if not seed_ids:
        return set()
    expanded = set(seed_ids)
    for edge in edges:
        if edge.source_node_id in seed_ids or edge.target_node_id in seed_ids:
            expanded.add(edge.source_node_id)
            expanded.add(edge.target_node_id)
    return expanded


def _is_content_in_date_range(node: GraphNodeRecord, start_date: date | None, end_date: date | None) -> bool:
    raw_date = node.metadata.get("date")
    if not raw_date:
        return False

    try:
        parsed = date.fromisoformat(str(raw_date))
    except ValueError:
        return False

    if start_date and parsed < start_date:
        return False
    if end_date and parsed > end_date:
        return False
    return True
