from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import cos, pi, sin
from statistics import mean

from backend.app.schemas.galaxy import (
    AxisBounds,
    CompatibilityMetadata,
    FilterFacets,
    GalaxyCluster,
    GalaxyEdge,
    GalaxyNode,
    GalaxySnapshotResponse,
    Position3D,
)


@dataclass(frozen=True)
class SourceNode:
    id: str
    title: str
    source_type: str = "unknown"
    published_at: datetime | None = None
    tags: tuple[str, ...] = ()
    guest_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceEdge:
    source: str
    target: str
    weight: float = 1.0


class GalaxyBuildService:
    def __init__(self, *, schema_version: int = 1, seed: int = 42) -> None:
        self._schema_version = schema_version
        self._seed = seed

    def build_snapshot(self, *, nodes: list[SourceNode], edges: list[SourceEdge] | None = None) -> GalaxySnapshotResponse:
        clean_edges = self._sanitize_edges(nodes=nodes, edges=edges or [])
        node_degree_weight = self._weighted_degree(clean_edges)

        galaxy_nodes = [self._to_galaxy_node(node, node_degree_weight.get(node.id, 0.0)) for node in nodes]
        id_to_position = {node.id: node.position for node in galaxy_nodes}
        galaxy_edges = [self._to_galaxy_edge(edge) for edge in clean_edges]
        clusters = self._build_clusters(galaxy_nodes)

        return GalaxySnapshotResponse(
            version=f"snapshot-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            generated_at=datetime.now(UTC),
            schema_version=self._schema_version,
            compatibility=CompatibilityMetadata(
                minimum_client_schema=1,
                current_schema=self._schema_version,
            ),
            bounds=self._build_bounds(id_to_position.values()),
            nodes=galaxy_nodes,
            edges=galaxy_edges,
            clusters=clusters,
            filter_facets=self._build_facets(nodes),
        )

    def build_fallback_snapshot(self) -> GalaxySnapshotResponse:
        return GalaxySnapshotResponse(
            version="snapshot-empty",
            generated_at=datetime.now(UTC),
            schema_version=self._schema_version,
            compatibility=CompatibilityMetadata(
                minimum_client_schema=1,
                current_schema=self._schema_version,
            ),
            bounds=AxisBounds(x=(-1.0, 1.0), y=(-1.0, 1.0), z=(-1.0, 1.0)),
            nodes=[],
            edges=[],
            clusters=[],
            filter_facets=FilterFacets(),
        )

    def _to_galaxy_node(self, node: SourceNode, weighted_degree: float) -> GalaxyNode:
        influence_score = min(weighted_degree / 10.0, 1.0)
        position = self._deterministic_position(node.id)
        return GalaxyNode(
            id=node.id,
            title=node.title,
            source_type=node.source_type if node.source_type in {"newsletter", "podcast"} else "unknown",
            published_at=node.published_at,
            tags=list(node.tags),
            guest_names=list(node.guest_names),
            cluster_id=self._cluster_id_for(node),
            position=position,
            influence_score=influence_score,
            star_size=0.8 + influence_score * 2.5,
            star_brightness=0.35 + influence_score * 0.65,
        )

    def _deterministic_position(self, node_id: str) -> Position3D:
        digest = sha256(f"{self._seed}:{node_id}".encode("utf-8")).digest()
        a = int.from_bytes(digest[:8], "big") / 2**64
        b = int.from_bytes(digest[8:16], "big") / 2**64
        radius = 25.0 + (int.from_bytes(digest[16:20], "big") / 2**32) * 75.0
        theta = 2.0 * pi * a
        phi = pi * b
        return Position3D(
            x=radius * sin(phi) * cos(theta),
            y=radius * sin(phi) * sin(theta),
            z=radius * cos(phi),
        )

    @staticmethod
    def _cluster_id_for(node: SourceNode) -> str:
        if node.tags:
            return f"cluster:tag:{node.tags[0].lower()}"
        return f"cluster:source:{node.source_type.lower()}"

    @staticmethod
    def _sanitize_edges(*, nodes: list[SourceNode], edges: list[SourceEdge]) -> list[SourceEdge]:
        known_ids = {node.id for node in nodes}
        out: list[SourceEdge] = []
        for edge in edges:
            if edge.source not in known_ids or edge.target not in known_ids:
                continue
            if edge.source == edge.target:
                continue
            out.append(edge)
        out.sort(key=lambda edge: (edge.source, edge.target))
        return out

    @staticmethod
    def _weighted_degree(edges: list[SourceEdge]) -> dict[str, float]:
        degree: dict[str, float] = defaultdict(float)
        for edge in edges:
            degree[edge.source] += edge.weight
            degree[edge.target] += edge.weight
        return degree

    @staticmethod
    def _to_galaxy_edge(edge: SourceEdge) -> GalaxyEdge:
        if edge.weight >= 3.0:
            tier = "high"
        elif edge.weight >= 1.5:
            tier = "medium"
        else:
            tier = "low"
        return GalaxyEdge(source=edge.source, target=edge.target, weight=edge.weight, edge_tier=tier)

    @staticmethod
    def _build_clusters(nodes: list[GalaxyNode]) -> list[GalaxyCluster]:
        grouped: dict[str, list[GalaxyNode]] = defaultdict(list)
        for node in nodes:
            grouped[node.cluster_id].append(node)

        clusters: list[GalaxyCluster] = []
        for cluster_id, members in sorted(grouped.items(), key=lambda row: row[0]):
            labels = [tag for node in members for tag in node.tags]
            dominant_tags = sorted(set(labels))[:3]
            centroid = Position3D(
                x=mean([member.position.x for member in members]),
                y=mean([member.position.y for member in members]),
                z=mean([member.position.z for member in members]),
            )
            clusters.append(
                GalaxyCluster(
                    id=cluster_id,
                    label=cluster_id.replace("cluster:", "").replace(":", " ").title(),
                    centroid=centroid,
                    node_count=len(members),
                    dominant_tags=dominant_tags,
                )
            )
        return clusters

    @staticmethod
    def _build_bounds(positions) -> AxisBounds:
        points = list(positions)
        if not points:
            return AxisBounds(x=(-1.0, 1.0), y=(-1.0, 1.0), z=(-1.0, 1.0))
        xs = [point.x for point in points]
        ys = [point.y for point in points]
        zs = [point.z for point in points]
        return AxisBounds(x=(min(xs), max(xs)), y=(min(ys), max(ys)), z=(min(zs), max(zs)))

    @staticmethod
    def _build_facets(nodes: list[SourceNode]) -> FilterFacets:
        tags = sorted({tag for node in nodes for tag in node.tags})
        guests = sorted({guest for node in nodes for guest in node.guest_names})
        source_types = sorted({node.source_type for node in nodes if node.source_type})
        dates = sorted([node.published_at for node in nodes if node.published_at is not None])
        return FilterFacets(
            tags=tags,
            guests=guests,
            date_min=dates[0] if dates else None,
            date_max=dates[-1] if dates else None,
            source_types=source_types,
        )
