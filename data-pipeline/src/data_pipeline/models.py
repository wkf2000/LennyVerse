from __future__ import annotations

from datetime import date as DateType
from typing import Any, Literal

from pydantic import BaseModel, Field


ContentType = Literal["newsletter", "podcast"]
NodeType = Literal["guest", "topic", "content", "concept"]


class ParsedDocument(BaseModel):
    id: str
    type: ContentType
    title: str
    date: DateType | None = None
    tags: list[str] = Field(default_factory=list)
    guest: str | None = None
    word_count: int | None = None
    filename: str
    subtitle: str | None = None
    description: str | None = None
    body: str
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    id: str
    content_id: str
    chunk_index: int
    text: str
    section_header: str | None = None
    embedding: list[float] | None = None


class GraphNode(BaseModel):
    id: str
    type: NodeType
    label: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    weight: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
