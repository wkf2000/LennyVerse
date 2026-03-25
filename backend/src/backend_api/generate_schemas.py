from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class OutlineRequest(BaseModel):
    topic: str
    num_weeks: int = Field(default=8, ge=2, le=16)
    difficulty: Literal["intro", "intermediate", "advanced"] = "intermediate"

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


class QuizOption(BaseModel):
    label: str
    text: str


class MultipleChoiceQuestion(BaseModel):
    question_number: int
    question: str
    options: list[QuizOption]
    correct_answer: str
    explanation: str
    source_week: int


class ShortAnswerQuestion(BaseModel):
    question_number: int
    question: str
    model_answer: str
    grading_guidance: str
    source_week: list[int]


class GeneratedQuiz(BaseModel):
    title: str
    total_questions: int
    multiple_choice: list[MultipleChoiceQuestion]
    short_answer: list[ShortAnswerQuestion]


class StepLogPayload(BaseModel):
    node: str
    status: Literal["running", "done", "error"]
    message: str
    week: int | None = None


class GenerateResultPayload(BaseModel):
    syllabus: GeneratedSyllabus
    quiz: GeneratedQuiz


class GenerateDonePayload(BaseModel):
    total_duration_ms: int
    weeks_generated: int
    quiz_questions: int


class GenerateErrorPayload(BaseModel):
    message: str
    retriable: bool
