from __future__ import annotations

import json
import time
from collections.abc import Callable, Iterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from backend_api.config import Settings
from backend_api.generate_schemas import (
    GeneratedQuiz,
    GeneratedReading,
    GeneratedSyllabus,
    GeneratedWeek,
    OutlineResponse,
    ReadingRef,
    WeekOutline,
)
from backend_api.rag_repository import RagChunkHit, RagRepository
from backend_api.rag_service import stable_chunk_result_id

LlmJsonCall = Callable[[list[dict[str, str]], str, Any], str]

LOW_COVERAGE_THRESHOLD = 5


def _as_list_of_str(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def _build_outline_system_prompt(num_weeks: int, difficulty: str) -> str:
    return (
        "You are a curriculum designer for university courses. You create structured "
        "course outlines from a corpus of product management, growth, and startup content "
        "by Lenny Rachitsky (newsletters and podcast interviews).\n\n"
        f"Given search results from the corpus, design a {num_weeks}-week course outline "
        f"at the {difficulty} level.\n\n"
        "Rules:\n"
        "- Each week must build on the previous - order for pedagogical progression\n"
        '- Difficulty "intro" = foundational concepts, "intermediate" = frameworks and case studies, '
        '"advanced" = nuanced strategy and edge cases\n'
        "- Only reference content_id values from the provided sources\n"
        "- For each reading, explain in one sentence why it fits that week\n"
        "- If the corpus has thin coverage for a week's theme, flag it honestly by reducing readings\n\n"
        "Respond with JSON: "
        '{"weeks":[{"week_number":int,"theme":str,"description":str,"readings":[{"content_id":str,'
        '"title":str,"content_type":str,"relevance_summary":str}]}]}'
    )


def _build_outline_user_prompt(topic: str, hits: list[RagChunkHit]) -> str:
    lines: list[str] = []
    seen_content_ids: set[str] = set()
    for hit in hits:
        if hit.content_id in seen_content_ids:
            continue
        seen_content_ids.add(hit.content_id)
        lines.append(
            f"- content_id={hit.content_id!r} title={hit.title!r} type={hit.content_type} tags={hit.tags}"
        )
    sources_block = "\n".join(lines) if lines else "(no results found)"
    return f"Topic: {topic}\n\nAvailable sources:\n{sources_block}"


def _default_embed_query(settings: Settings) -> Callable[[str], list[float]]:
    client = OpenAI(
        api_key=settings.embedding_api_key,
        base_url=(settings.ollama_embed_base_url or "").rstrip("/"),
    )

    def embed(text: str) -> list[float]:
        response = client.embeddings.create(model=settings.embedding_model, input=text)
        return list(response.data[0].embedding)

    return embed


def _default_llm_json_call(settings: Settings) -> LlmJsonCall:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for outline generation.")

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_api_base or None,
    )

    def call(messages: list[dict[str, str]], model: str, response_format: Any = None) -> str:
        kwargs: dict[str, Any] = {"model": model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or "{}"

    return call


class GenerateService:
    def __init__(
        self,
        repository: RagRepository,
        settings: Settings,
        *,
        embed_query: Callable[[str], list[float]] | None = None,
        llm_json_call: LlmJsonCall | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._embed_query = embed_query or _default_embed_query(settings)
        self._llm_json_call = llm_json_call or _default_llm_json_call(settings)

    def generate_outline(self, topic: str, num_weeks: int, difficulty: str) -> OutlineResponse:
        embedding = self._embed_query(topic)
        hits = self._repository.search_similar_chunks(
            query_embedding=embedding,
            k=self._settings.generate_outline_k,
        )
        unique_content_ids = {hit.content_id for hit in hits}
        low_coverage = len(unique_content_ids) < LOW_COVERAGE_THRESHOLD

        messages = [
            {"role": "system", "content": _build_outline_system_prompt(num_weeks, difficulty)},
            {"role": "user", "content": _build_outline_user_prompt(topic, hits)},
        ]
        raw_json = self._llm_json_call(messages, self._settings.openai_model, {"type": "json_object"})
        parsed = json.loads(raw_json)

        weeks_data = parsed.get("weeks", [])
        weeks = [
            WeekOutline(
                week_number=week["week_number"],
                theme=week["theme"],
                description=week["description"],
                readings=[ReadingRef(**reading) for reading in week.get("readings", [])],
            )
            for week in weeks_data
        ]

        return OutlineResponse(
            topic=topic,
            num_weeks=num_weeks,
            difficulty=difficulty,
            weeks=weeks,
            corpus_coverage=f"Found {len(unique_content_ids)} relevant pieces across the corpus",
            low_coverage=low_coverage,
        )

    def _build_deep_context(self, approved_outline: list[WeekOutline]) -> dict[str, list[RagChunkHit]]:
        content_ids: list[str] = []
        for week in approved_outline:
            for reading in week.readings:
                content_ids.append(reading.content_id)
        unique_content_ids = list(dict.fromkeys(content_ids))
        hits = self._repository.fetch_chunks_by_content_ids(
            content_ids=unique_content_ids,
            max_chunks_per_content=self._settings.generate_retrieval_k_per_reading,
        )
        grouped: dict[str, list[RagChunkHit]] = {cid: [] for cid in unique_content_ids}
        for hit in hits:
            grouped.setdefault(hit.content_id, []).append(hit)
        return grouped

    def _generate_week(self, week: WeekOutline, deep_chunks: dict[str, list[RagChunkHit]], difficulty: str) -> GeneratedWeek:
        chunk_lines: list[str] = []
        for reading in week.readings:
            hits = deep_chunks.get(reading.content_id, [])
            for hit in hits:
                cite = stable_chunk_result_id(hit.content_id, hit.chunk_index)
                chunk_lines.append(f"[cite:{cite}] title={hit.title!r} excerpt={hit.chunk_text!r}")
        chunks_block = "\n".join(chunk_lines) if chunk_lines else "(no chunks available)"
        outline_readings = "\n".join(
            f"- {r.title} ({r.content_type}) id={r.content_id}" for r in week.readings
        )

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are generating detailed course material for Week {week.week_number} "
                    f"of a university course at the {difficulty} level.\n"
                    "Generate valid JSON with keys: learning_objectives, narrative_summary, readings, key_takeaways.\n"
                    "Ground claims in sources and include [cite:CHUNK_ID] markers."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Week theme: {week.theme}\n"
                    f"Week description: {week.description}\n"
                    f"Assigned readings:\n{outline_readings}\n\n"
                    f"Source chunks:\n{chunks_block}"
                ),
            },
        ]
        raw = self._llm_json_call(messages, self._settings.openai_model, {"type": "json_object"})
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise

        try:
            readings_raw = parsed.get("readings", [])
            generated_readings: list[GeneratedReading] = []
            if isinstance(readings_raw, list):
                for idx, item in enumerate(readings_raw):
                    fallback = week.readings[idx] if idx < len(week.readings) else (week.readings[0] if week.readings else None)
                    if isinstance(item, dict):
                        generated_readings.append(
                            GeneratedReading(
                                content_id=item.get("content_id", fallback.content_id if fallback else "unknown"),
                                title=item.get("title", fallback.title if fallback else "Unknown"),
                                content_type=item.get("content_type", fallback.content_type if fallback else "unknown"),
                                key_concepts=_as_list_of_str(item.get("key_concepts")),
                                notable_quotes=_as_list_of_str(item.get("notable_quotes")),
                                discussion_hooks=_as_list_of_str(item.get("discussion_hooks")),
                            )
                        )
                    else:
                        text = str(item).strip()
                        generated_readings.append(
                            GeneratedReading(
                                content_id=fallback.content_id if fallback else "unknown",
                                title=fallback.title if fallback else (text or "Unknown"),
                                content_type=fallback.content_type if fallback else "unknown",
                                key_concepts=[text] if text else [],
                                notable_quotes=[],
                                discussion_hooks=[],
                            )
                        )
            if not generated_readings and week.readings:
                generated_readings = [
                    GeneratedReading(
                        content_id=ref.content_id,
                        title=ref.title,
                        content_type=ref.content_type,
                        key_concepts=[],
                        notable_quotes=[],
                        discussion_hooks=[],
                    )
                    for ref in week.readings
                ]
        except Exception:
            raise

        return GeneratedWeek(
            week_number=week.week_number,
            theme=week.theme,
            status="complete",
            learning_objectives=_as_list_of_str(parsed.get("learning_objectives")),
            narrative_summary=str(parsed.get("narrative_summary", "")),
            readings=generated_readings,
            key_takeaways=_as_list_of_str(parsed.get("key_takeaways")),
        )

    def _generate_quiz(self, topic: str, difficulty: str, generated_weeks: list[GeneratedWeek]) -> GeneratedQuiz:
        weeks_block = []
        for week in generated_weeks:
            weeks_block.append(
                f"Week {week.week_number}: {week.theme}\n"
                f"Objectives: {week.learning_objectives}\n"
                f"Summary: {week.narrative_summary}\n"
            )
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are an assessment designer creating a comprehensive quiz for a {difficulty} "
                    f"university course on '{topic}'. Return JSON with keys title, total_questions, "
                    "multiple_choice, short_answer."
                ),
            },
            {
                "role": "user",
                "content": "Course material:\n" + "\n".join(weeks_block),
            },
        ]
        raw = self._llm_json_call(messages, self._settings.openai_model, {"type": "json_object"})
        parsed = json.loads(raw)
        try:
            return GeneratedQuiz.model_validate(parsed)
        except Exception:  # noqa: BLE001
            mc_raw = parsed.get("multiple_choice") if isinstance(parsed, dict) else None
            sa_raw = parsed.get("short_answer") if isinstance(parsed, dict) else None
            mc_count = mc_raw if isinstance(mc_raw, int) else 0
            sa_count = sa_raw if isinstance(sa_raw, int) else 0
            if mc_count == 0 and sa_count == 0:
                mc_count = 5
                sa_count = 2

            fallback_mc: list[dict[str, Any]] = []
            for idx in range(mc_count):
                source_week = generated_weeks[idx % len(generated_weeks)].week_number if generated_weeks else 1
                fallback_mc.append(
                    {
                        "question_number": idx + 1,
                        "question": f"[Fallback] Which concept from week {source_week} best supports pricing decisions?",
                        "options": [
                            {"label": "A", "text": "Value metric alignment"},
                            {"label": "B", "text": "Ignoring customer segmentation"},
                            {"label": "C", "text": "One-size-fits-all packaging"},
                            {"label": "D", "text": "No experimentation"},
                        ],
                        "correct_answer": "A",
                        "explanation": "Fallback question due to malformed quiz payload from model.",
                        "source_week": source_week,
                    }
                )

            fallback_sa: list[dict[str, Any]] = []
            for idx in range(sa_count):
                source_week = generated_weeks[idx % len(generated_weeks)].week_number if generated_weeks else 1
                qn = mc_count + idx + 1
                fallback_sa.append(
                    {
                        "question_number": qn,
                        "question": f"[Fallback] Explain a pricing trade-off covered in week {source_week}.",
                        "model_answer": "A strong answer references value metric, packaging, and growth implications.",
                        "grading_guidance": "Full credit for grounded trade-off reasoning tied to course material.",
                        "source_week": [source_week],
                    }
                )

            recovered = {
                "title": parsed.get("title", "Recovered Comprehensive Quiz") if isinstance(parsed, dict) else "Recovered Comprehensive Quiz",
                "total_questions": mc_count + sa_count,
                "multiple_choice": fallback_mc,
                "short_answer": fallback_sa,
            }
            return GeneratedQuiz.model_validate(recovered)

    def iter_generate_sse_events(
        self,
        topic: str,
        num_weeks: int,
        difficulty: str,
        approved_outline: list[WeekOutline],
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        class SyllabusState(TypedDict):
            topic: str
            num_weeks: int
            difficulty: str
            approved_outline: list[WeekOutline]
            deep_chunks: dict[str, list[RagChunkHit]]
            current_week: int
            generated_weeks: list[GeneratedWeek]
            quiz: GeneratedQuiz | None
            step_log: list[dict[str, Any]]
            result_payload: dict[str, Any] | None
            error: str | None

        def retrieve_deep_context(state: SyllabusState) -> dict[str, Any]:
            step_log = list(state["step_log"])
            step_log.append(
                {
                    "node": "retrieve_deep_context",
                    "status": "running",
                    "message": f"Retrieving content for {len(state['approved_outline'])} weeks...",
                }
            )
            deep_chunks = self._build_deep_context(state["approved_outline"])
            source_count = sum(len(v) for v in deep_chunks.values())
            step_log.append(
                {
                    "node": "retrieve_deep_context",
                    "status": "done",
                    "message": f"Retrieved {source_count} source passages",
                }
            )
            return {"deep_chunks": deep_chunks, "step_log": step_log}

        def generate_weeks(state: SyllabusState) -> dict[str, Any]:
            idx = state["current_week"]
            outline = state["approved_outline"]
            if idx >= len(outline):
                return {}

            week = outline[idx]
            step_log = list(state["step_log"])
            generated = list(state["generated_weeks"])
            step_log.append(
                {
                    "node": "generate_weeks",
                    "status": "running",
                    "message": f"Generating Week {week.week_number}: {week.theme}",
                    "week": week.week_number,
                }
            )
            try:
                gen_week = self._generate_week(week, state["deep_chunks"], state["difficulty"])
                generated.append(gen_week)
                step_log.append(
                    {
                        "node": "generate_weeks",
                        "status": "done",
                        "message": f"Week {week.week_number} complete",
                        "week": week.week_number,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                generated.append(
                    GeneratedWeek(
                        week_number=week.week_number,
                        theme=week.theme,
                        status="incomplete",
                        learning_objectives=[],
                        narrative_summary=f"Week generation failed: {exc}",
                        readings=[],
                        key_takeaways=[],
                    )
                )
                step_log.append(
                    {
                        "node": "generate_weeks",
                        "status": "error",
                        "message": f"Week {week.week_number} generation failed: {exc}",
                        "week": week.week_number,
                    }
                )
            return {"generated_weeks": generated, "current_week": idx + 1, "step_log": step_log}

        def route_after_weeks(state: dict[str, Any]) -> str:
            if state["current_week"] < len(state["approved_outline"]):
                return "generate_weeks"
            return "generate_quiz"

        def generate_quiz(state: SyllabusState) -> dict[str, Any]:
            step_log = list(state["step_log"])
            step_log.append(
                {
                    "node": "generate_quiz",
                    "status": "running",
                    "message": "Generating comprehensive quiz...",
                }
            )
            try:
                quiz = self._generate_quiz(state["topic"], state["difficulty"], state["generated_weeks"])
                step_log.append(
                    {
                        "node": "generate_quiz",
                        "status": "done",
                        "message": "Quiz generated",
                    }
                )
                return {"quiz": quiz, "step_log": step_log}
            except Exception as exc:  # noqa: BLE001
                step_log.append(
                    {
                        "node": "generate_quiz",
                        "status": "error",
                        "message": f"Quiz generation failed: {exc}",
                    }
                )
                return {"quiz": None, "step_log": step_log}

        def format_output(state: SyllabusState) -> dict[str, Any]:
            syllabus = GeneratedSyllabus(
                topic=state["topic"],
                difficulty=state["difficulty"],
                weeks=state["generated_weeks"],
            )
            quiz = state["quiz"] or GeneratedQuiz(
                title="Quiz generation failed",
                total_questions=0,
                multiple_choice=[],
                short_answer=[],
            )
            result_payload = {
                "syllabus": syllabus.model_dump(),
                "quiz": quiz.model_dump(),
            }
            return {"result_payload": result_payload}

        workflow = StateGraph(SyllabusState)
        workflow.add_node("retrieve_deep_context", retrieve_deep_context)
        workflow.add_node("generate_weeks", generate_weeks)
        workflow.add_node("generate_quiz", generate_quiz)
        workflow.add_node("format_output", format_output)
        workflow.add_edge(START, "retrieve_deep_context")
        workflow.add_edge("retrieve_deep_context", "generate_weeks")
        workflow.add_conditional_edges(
            "generate_weeks",
            route_after_weeks,
            {"generate_weeks": "generate_weeks", "generate_quiz": "generate_quiz"},
        )
        workflow.add_edge("generate_quiz", "format_output")
        workflow.add_edge("format_output", END)
        graph = workflow.compile()

        started = time.perf_counter()
        initial_state: SyllabusState = {
            "topic": topic,
            "num_weeks": num_weeks,
            "difficulty": difficulty,
            "approved_outline": list(approved_outline),
            "deep_chunks": {},
            "current_week": 0,
            "generated_weeks": [],
            "quiz": None,
            "step_log": [],
            "result_payload": None,
            "error": None,
        }
        seen_step_count = 0
        partial_result: dict[str, Any] | None = None
        total_weeks = 0
        quiz_questions = 0

        try:
            for update in graph.stream(initial_state):
                elapsed = time.perf_counter() - started
                if elapsed > float(self._settings.generate_timeout_seconds):
                    yield "error", {"message": "Generation timed out", "retriable": True}
                    break

                for node_update in update.values():
                    if "step_log" in node_update:
                        step_log = node_update["step_log"]
                        for entry in step_log[seen_step_count:]:
                            yield "step_log", dict(entry)
                        seen_step_count = len(step_log)
                    if "result_payload" in node_update and node_update["result_payload"] is not None:
                        partial_result = node_update["result_payload"]
                        total_weeks = len(partial_result.get("syllabus", {}).get("weeks", []))
                        quiz_questions = partial_result.get("quiz", {}).get("total_questions", 0)
        except Exception as exc:  # noqa: BLE001
            yield "error", {"message": f"Generation failed: {exc}", "retriable": True}

        if partial_result is None:
            partial_result = {
                "syllabus": {
                    "topic": topic,
                    "difficulty": difficulty,
                    "weeks": [],
                },
                "quiz": {
                    "title": "Quiz generation failed",
                    "total_questions": 0,
                    "multiple_choice": [],
                    "short_answer": [],
                },
            }

        yield "result", partial_result
        yield "done", {
            "total_duration_ms": int((time.perf_counter() - started) * 1000),
            "weeks_generated": total_weeks,
            "quiz_questions": quiz_questions,
        }
