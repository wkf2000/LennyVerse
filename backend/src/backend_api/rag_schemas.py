from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ContentTypeFilter = Literal["podcast", "newsletter"]


class RagSearchFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tags: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    content_type: ContentTypeFilter | None = Field(default=None, alias="type")


class SearchRequest(BaseModel):
    query: str
    k: int | None = None
    filters: RagSearchFilters | None = None

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("query must not be empty or whitespace only")
        return query


class SearchResult(BaseModel):
    id: str
    score: float
    title: str
    guest: str | None = None
    date: str | None = None
    tags: list[str] = Field(default_factory=list)
    excerpt: str
    content_id: str
    chunk_index: int


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    query: str
    k: int | None = None
    filters: RagSearchFilters | None = None
    history: list[ChatMessage] | None = None


class AnswerDeltaPayload(BaseModel):
    text_delta: str


class SourceRef(BaseModel):
    id: str
    span: dict[str, Any] | None = None


class CitationUsedPayload(BaseModel):
    source_ref: SourceRef


class RagStreamErrorPayload(BaseModel):
    code: str
    message: str
    retryable: bool


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class DonePayload(BaseModel):
    latency_ms: int
    token_usage: TokenUsage
    source_count: int
    partial: bool
