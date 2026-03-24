from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend_api.config import Settings, get_settings
from backend_api.graph_repository import GraphRepository
from backend_api.graph_service import GraphFilters, GraphService
from backend_api.schemas import GraphResponse, NodeDetailResponse, NodeType

app = FastAPI(title="LennyVerse API", version="0.2.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_graph_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> GraphRepository:
    return GraphRepository(app_settings.require_db_url())


def get_graph_service(
    repository: Annotated[GraphRepository, Depends(get_graph_repository)],
) -> GraphService:
    return GraphService(repository)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/graph", response_model=GraphResponse)
def get_graph(
    service: Annotated[GraphService, Depends(get_graph_service)],
    node_types: Annotated[list[NodeType] | None, Query(alias="nodeType")] = None,
    topic: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> GraphResponse:
    filters = GraphFilters(
        node_types=set(node_types) if node_types else None,
        topic=topic.strip() if topic else None,
        start_date=start_date,
        end_date=end_date,
    )
    return service.get_graph(filters)


@app.get("/api/graph/nodes/{node_id}", response_model=NodeDetailResponse)
def get_graph_node(
    node_id: str,
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> NodeDetailResponse:
    detail = service.get_node_detail(node_id)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found.")
    return detail
