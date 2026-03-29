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


class HeatmapItem(BaseModel):
    year: int
    week: int
    type: str
    title: str
    published_at: str


class HeatmapResponse(BaseModel):
    items: list[HeatmapItem] = Field(default_factory=list)


class ContentBreakdownItem(BaseModel):
    quarter: str
    type: str
    count: int
    avg_word_count: int


class ContentBreakdownResponse(BaseModel):
    breakdown: list[ContentBreakdownItem] = Field(default_factory=list)


class GuestCount(BaseModel):
    guest: str
    count: int


class TopGuestsResponse(BaseModel):
    guests: list[GuestCount] = Field(default_factory=list)
