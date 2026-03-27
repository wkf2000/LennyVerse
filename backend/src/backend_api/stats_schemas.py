from __future__ import annotations

from pydantic import BaseModel, Field


class TopicTrendItem(BaseModel):
    quarter: str
    topic: str
    count: int


class TopicCount(BaseModel):
    topic: str
    count: int


class DateRange(BaseModel):
    start: str
    end: str


class StatsSummary(BaseModel):
    total_content: int
    total_podcasts: int
    total_newsletters: int
    date_range: DateRange
    top_topics: list[TopicCount] = Field(default_factory=list)


class TopicTrendsResponse(BaseModel):
    trends: list[TopicTrendItem] = Field(default_factory=list)
    summary: StatsSummary
