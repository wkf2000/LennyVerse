from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


NodeType = Literal["guest", "topic", "content", "concept"]


class GraphNodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    type: NodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source_node_id: str = Field(alias="sourceNodeId")
    target_node_id: str = Field(alias="targetNodeId")
    relationship_type: str = Field(alias="relationshipType")
    weight: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class RelatedContentResponse(BaseModel):
    id: str
    title: str
    content_type: str
    published_at: date | None = None
    guest: str | None = None
    tags: list[str] = Field(default_factory=list)
    filename: str


class NodeDetailResponse(BaseModel):
    node: GraphNodeResponse
    connected_node_count: int
    related_content: list[RelatedContentResponse]


class ContentSummaryResponse(BaseModel):
    content_id: str
    summary: str | None = None
