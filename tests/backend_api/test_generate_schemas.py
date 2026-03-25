from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_outline_request_defaults() -> None:
    from backend_api.generate_schemas import OutlineRequest

    req = OutlineRequest(topic="Product-Led Growth")
    assert req.topic == "Product-Led Growth"
    assert req.num_weeks == 8
    assert req.difficulty == "intermediate"


def test_outline_request_validation_bounds() -> None:
    from backend_api.generate_schemas import OutlineRequest

    with pytest.raises(ValidationError):
        OutlineRequest(topic="X", num_weeks=1)
    with pytest.raises(ValidationError):
        OutlineRequest(topic="X", num_weeks=17)
    with pytest.raises(ValidationError):
        OutlineRequest(topic="X", difficulty="expert")


def test_outline_request_rejects_empty_topic() -> None:
    from backend_api.generate_schemas import OutlineRequest

    with pytest.raises(ValidationError):
        OutlineRequest(topic="")
    with pytest.raises(ValidationError):
        OutlineRequest(topic="   ")


def test_reading_ref_fields() -> None:
    from backend_api.generate_schemas import ReadingRef

    ref = ReadingRef(
        content_id="newsletter::plg-guide",
        title="PLG Guide",
        content_type="newsletter",
        relevance_summary="Core PLG framework",
    )
    assert ref.content_id == "newsletter::plg-guide"


def test_outline_response_round_trip() -> None:
    from backend_api.generate_schemas import OutlineResponse, ReadingRef, WeekOutline

    resp = OutlineResponse(
        topic="PLG",
        num_weeks=2,
        difficulty="intro",
        weeks=[
            WeekOutline(
                week_number=1,
                theme="Intro to PLG",
                description="Basics",
                readings=[
                    ReadingRef(
                        content_id="newsletter::plg",
                        title="PLG Guide",
                        content_type="newsletter",
                        relevance_summary="Core framework",
                    )
                ],
            )
        ],
        corpus_coverage="Found 12 relevant pieces across 638",
        low_coverage=False,
    )
    data = resp.model_dump()
    assert data["weeks"][0]["readings"][0]["content_id"] == "newsletter::plg"
    assert data["low_coverage"] is False


def test_execute_request_requires_approved_outline() -> None:
    from backend_api.generate_schemas import ExecuteRequest, ReadingRef, WeekOutline

    req = ExecuteRequest(
        topic="PLG",
        num_weeks=2,
        difficulty="intro",
        approved_outline=[
            WeekOutline(
                week_number=1,
                theme="Intro",
                description="Basics",
                readings=[
                    ReadingRef(
                        content_id="newsletter::plg",
                        title="PLG",
                        content_type="newsletter",
                        relevance_summary="Core",
                    )
                ],
            )
        ],
    )
    assert len(req.approved_outline) == 1


def test_generated_week_status_values() -> None:
    from backend_api.generate_schemas import GeneratedReading, GeneratedWeek

    week = GeneratedWeek(
        week_number=1,
        theme="PLG Intro",
        status="complete",
        learning_objectives=["Define PLG"],
        narrative_summary="PLG is...",
        readings=[
            GeneratedReading(
                content_id="newsletter::plg",
                title="PLG Guide",
                content_type="newsletter",
                key_concepts=["Self-serve"],
                notable_quotes=[],
                discussion_hooks=[],
            )
        ],
        key_takeaways=["PLG works when..."],
    )
    assert week.status == "complete"


def test_quiz_schema_structure() -> None:
    from backend_api.generate_schemas import (
        GeneratedQuiz,
        MultipleChoiceQuestion,
        QuizOption,
        ShortAnswerQuestion,
    )

    quiz = GeneratedQuiz(
        title="PLG Quiz",
        total_questions=2,
        multiple_choice=[
            MultipleChoiceQuestion(
                question_number=1,
                question="What is PLG?",
                options=[
                    QuizOption(label="A", text="Sales strategy"),
                    QuizOption(label="B", text="Product-led model"),
                    QuizOption(label="C", text="Pricing strategy"),
                    QuizOption(label="D", text="Marketing approach"),
                ],
                correct_answer="B",
                explanation="PLG is defined as...",
                source_week=1,
            )
        ],
        short_answer=[
            ShortAnswerQuestion(
                question_number=2,
                question="Compare freemium and reverse trial.",
                model_answer="Freemium works when...",
                grading_guidance="Full credit: references both.",
                source_week=[1],
            )
        ],
    )
    assert quiz.total_questions == 2
    assert len(quiz.multiple_choice) == 1
    assert len(quiz.short_answer) == 1
