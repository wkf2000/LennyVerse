from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from backend.app.schemas.galaxy import GalaxyNodeDetailResponse, GalaxySnapshotResponse
from backend.app.services.galaxy_query_service import (
    GalaxyNodeNotFoundError,
    GalaxyQueryService,
    GalaxySnapshotUnavailableError,
)


def create_router(service: GalaxyQueryService | None = None) -> APIRouter:
    query_service = service or GalaxyQueryService()
    router = APIRouter(prefix="/galaxy", tags=["galaxy"])

    @router.get("/snapshot", response_model=GalaxySnapshotResponse)
    def get_snapshot(response: Response) -> GalaxySnapshotResponse:
        try:
            snapshot = query_service.get_snapshot()
            stats = query_service.last_snapshot_stats
            if "build_ms" in stats:
                response.headers["X-Galaxy-Build-Ms"] = str(stats["build_ms"])
            if "payload_bytes" in stats:
                response.headers["X-Galaxy-Payload-Bytes"] = str(stats["payload_bytes"])
            if "source" in stats:
                response.headers["X-Galaxy-Snapshot-Source"] = str(stats["source"])
            return snapshot
        except GalaxySnapshotUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.get("/node/{node_id}", response_model=GalaxyNodeDetailResponse)
    def get_node(node_id: str) -> GalaxyNodeDetailResponse:
        try:
            return query_service.get_node(node_id)
        except GalaxyNodeNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"Node not found: {node_id}") from exc
        except GalaxySnapshotUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return router
