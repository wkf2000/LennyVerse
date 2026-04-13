from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OutlineRequest(BaseModel):
    topic: str
    num_weeks: int = Field(default=8, ge=2, le=16)
    difficulty: Literal["intro", "intermediate", "advanced"] = "intermediate"
    role: str | None = None
    company_stage: str | None = None

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        topic = value.strip()
        if not topic:
            raise ValueError("topic must not be empty or whitespace only")
        return topic


class ReadingRef(BaseModel):
    content_id: str
    title: str
    content_type: str
    relevance_summary: str


class WeekOutline(BaseModel):
    week_number: int
    theme: str
    description: str
    readings: list[ReadingRef]


class OutlineResponse(BaseModel):
    topic: str
    num_weeks: int
    difficulty: str
    weeks: list[WeekOutline]
    corpus_coverage: str
    low_coverage: bool


class ExecuteRequest(BaseModel):
    topic: str
    num_weeks: int
    difficulty: str
    approved_outline: list[WeekOutline]
    role: str | None = None
    company_stage: str | None = None


class GeneratedReading(BaseModel):
    content_id: str
    title: str
    content_type: str
    key_concepts: list[str]
    notable_quotes: list[str]
    discussion_hooks: list[str]


class GeneratedWeek(BaseModel):
    week_number: int
    theme: str
    status: Literal["complete", "incomplete"]
    learning_objectives: list[str]
    narrative_summary: str
    readings: list[GeneratedReading]
    key_takeaways: list[str]


class GeneratedSyllabus(BaseModel):
    topic: str
    difficulty: str
    weeks: list[GeneratedWeek]


class StepLogPayload(BaseModel):
    node: str
    status: Literal["running", "done", "error"]
    message: str
    week: int | None = None


class GenerateResultPayload(BaseModel):
    syllabus: GeneratedSyllabus


class GenerateDonePayload(BaseModel):
    total_duration_ms: int
    weeks_generated: int


class GenerateErrorPayload(BaseModel):
    message: str
    retriable: bool


class InfographicRequest(BaseModel):
    syllabus: GeneratedSyllabus


class InfographicResponse(BaseModel):
    html: str
