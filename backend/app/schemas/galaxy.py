from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AxisBounds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: tuple[float, float]
    y: tuple[float, float]
    z: tuple[float, float]


class Position3D(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    z: float


class GalaxyNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: Literal["newsletter", "podcast", "unknown"] = "unknown"
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    guest_names: list[str] = Field(default_factory=list)
    cluster_id: str
    position: Position3D
    influence_score: float = Field(ge=0.0, le=1.0)
    star_size: float = Field(gt=0.0)
    star_brightness: float = Field(ge=0.0, le=1.0)


class GalaxyEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    weight: float = Field(ge=0.0)
    edge_tier: Literal["high", "medium", "low"]


class GalaxyCluster(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    centroid: Position3D
    node_count: int = Field(ge=0)
    dominant_tags: list[str] = Field(default_factory=list)


class FilterFacets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tags: list[str] = Field(default_factory=list)
    guests: list[str] = Field(default_factory=list)
    date_min: datetime | None = None
    date_max: datetime | None = None
    source_types: list[str] = Field(default_factory=list)


class CompatibilityMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_client_schema: int = 1
    current_schema: int = 1


class GalaxySnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    generated_at: datetime
    schema_version: int = Field(ge=1, default=1)
    compatibility: CompatibilityMetadata = Field(default_factory=CompatibilityMetadata)
    bounds: AxisBounds
    nodes: list[GalaxyNode]
    edges: list[GalaxyEdge]
    clusters: list[GalaxyCluster]
    filter_facets: FilterFacets


class GalaxyNodeDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: Literal["newsletter", "podcast", "unknown"] = "unknown"
    published_at: datetime | None = None
    description: str | None = None
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    guest_names: list[str] = Field(default_factory=list)
    related_document_ids: list[str] = Field(default_factory=list)
    reader_url: str
