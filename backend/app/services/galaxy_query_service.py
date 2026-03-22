from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import ValidationError

from backend.app.schemas.galaxy import GalaxyNodeDetailResponse, GalaxySnapshotResponse
from backend.app.services.galaxy_build_service import GalaxyBuildService, SourceEdge, SourceNode
from backend.app.services.galaxy_snapshot_store import GalaxySnapshotStore
from backend.app.services.galaxy_topology_source import Neo4jTopologySource


class GalaxySnapshotUnavailableError(RuntimeError):
    pass


class GalaxyNodeNotFoundError(LookupError):
    pass


class GalaxyTopologySource(Protocol):
    def fetch_nodes(self) -> list[SourceNode]: ...
    def fetch_edges(self) -> list[SourceEdge]: ...


class GalaxyQueryService:
    def __init__(
        self,
        *,
        snapshot_path: Path | None = None,
        build_service: GalaxyBuildService | None = None,
        topology_source: GalaxyTopologySource | None = None,
        snapshot_store: GalaxySnapshotStore | None = None,
    ) -> None:
        env_path = os.environ.get("GALAXY_SNAPSHOT_PATH")
        self._snapshot_path = snapshot_path or (Path(env_path) if env_path else None)
        self._build_service = build_service or GalaxyBuildService()
        self._topology_source = topology_source if topology_source is not None else self._default_topology_source()
        self._snapshot_store = snapshot_store if snapshot_store is not None else self._default_store()
        self._cache: GalaxySnapshotResponse | None = None
        self._detail_cache: dict[str, GalaxyNodeDetailResponse] = {}
        self.last_snapshot_stats: dict[str, Any] = {}

    def get_snapshot(self) -> GalaxySnapshotResponse:
        if self._cache is not None:
            return self._cache

        if self._snapshot_path is not None and self._snapshot_path.exists():
            payload = self._read_json(self._snapshot_path)
            try:
                snapshot = GalaxySnapshotResponse.model_validate(payload)
            except ValidationError as exc:
                raise GalaxySnapshotUnavailableError("Snapshot payload failed schema validation") from exc
            self._cache = snapshot
            self.last_snapshot_stats = {
                "source": "artifact",
                "snapshot_path": str(self._snapshot_path),
                "node_count": len(snapshot.nodes),
                "edge_count": len(snapshot.edges),
                "payload_bytes": len(json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=True)),
            }
            return snapshot

        if self._topology_source is not None:
            snapshot = self._build_snapshot_from_topology_source()
            self._cache = snapshot
            return snapshot

        self._cache = self._build_service.build_fallback_snapshot()
        self.last_snapshot_stats = {
            "source": "fallback",
            "node_count": 0,
            "edge_count": 0,
            "snapshot_path": str(self._snapshot_path) if self._snapshot_path else None,
        }
        return self._cache

    def get_node(self, node_id: str) -> GalaxyNodeDetailResponse:
        if node_id in self._detail_cache:
            return self._detail_cache[node_id]

        snapshot = self.get_snapshot()
        node = next((candidate for candidate in snapshot.nodes if candidate.id == node_id), None)
        if node is None:
            raise GalaxyNodeNotFoundError(node_id)

        related_ids = [
            edge.target
            for edge in snapshot.edges
            if edge.source == node_id
        ] + [
            edge.source
            for edge in snapshot.edges
            if edge.target == node_id
        ]

        detail = GalaxyNodeDetailResponse(
            id=node.id,
            title=node.title,
            source_type=node.source_type,
            published_at=node.published_at,
            description=None,
            summary=None,
            tags=node.tags,
            guest_names=node.guest_names,
            related_document_ids=sorted(set(related_ids)),
            reader_url=f"/reader/{node.id}",
        )
        self._detail_cache[node_id] = detail
        return detail

    def refresh_from_source(
        self, *, nodes: list[dict[str, Any]], edges: list[dict[str, Any]] | None = None, version_prefix: str = "snapshot"
    ) -> GalaxySnapshotResponse:
        source_nodes = [
            SourceNode(
                id=str(node["id"]),
                title=str(node.get("title", node["id"])),
                source_type=str(node.get("source_type", "unknown")),
                published_at=_parse_optional_datetime(node.get("published_at")),
                tags=tuple(_coerce_str_list(node.get("tags", []))),
                guest_names=tuple(_coerce_str_list(node.get("guest_names", []))),
            )
            for node in nodes
        ]
        source_edges = [
            SourceEdge(
                source=str(edge["source"]),
                target=str(edge["target"]),
                weight=float(edge.get("weight", 1.0)),
            )
            for edge in (edges or [])
        ]
        snapshot = self._build_service.build_snapshot(nodes=source_nodes, edges=source_edges)
        snapshot.version = f"{version_prefix}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        self._cache = snapshot
        self._detail_cache.clear()
        self._persist_snapshot(snapshot)
        return snapshot

    def _build_snapshot_from_topology_source(self) -> GalaxySnapshotResponse:
        started = time.perf_counter()
        try:
            nodes = self._topology_source.fetch_nodes()
        except Exception as exc:
            raise GalaxySnapshotUnavailableError("Failed to load galaxy node topology from Neo4j") from exc

        edges: list[SourceEdge]
        edge_derivation_error: str | None = None
        try:
            edges = self._topology_source.fetch_edges()
        except Exception as exc:
            edges = []
            edge_derivation_error = f"{type(exc).__name__}: {exc}"

        snapshot = self._build_service.build_snapshot(nodes=nodes, edges=edges)
        persisted_path = self._persist_snapshot(snapshot)
        self.last_snapshot_stats = {
            "source": "neo4j",
            "node_count": len(snapshot.nodes),
            "edge_count": len(snapshot.edges),
            "build_ms": int((time.perf_counter() - started) * 1000),
            "payload_bytes": len(json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=True)),
            "persisted_path": str(persisted_path) if persisted_path else None,
            "edge_derivation_error": edge_derivation_error,
        }
        return snapshot

    def _persist_snapshot(self, snapshot: GalaxySnapshotResponse) -> Path | None:
        if self._snapshot_store is None:
            return None
        return self._snapshot_store.write(snapshot)

    @staticmethod
    def _default_topology_source() -> GalaxyTopologySource | None:
        if os.environ.get("GALAXY_ENABLE_NEO4J_SOURCE", "0").strip().lower() in {"0", "false", "no"}:
            return None
        return Neo4jTopologySource()

    @staticmethod
    def _default_store() -> GalaxySnapshotStore | None:
        snapshot_dir = os.environ.get("GALAXY_SNAPSHOT_DIR", "data/galaxy-snapshots").strip()
        if not snapshot_dir:
            return None
        return GalaxySnapshotStore(base_dir=Path(snapshot_dir))

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _parse_optional_datetime(raw: Any) -> datetime | None:
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
