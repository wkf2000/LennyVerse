from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

load_dotenv()

logger = logging.getLogger(__name__)


class _ConceptSignal(BaseModel):
    name: str = Field(description="Concept name")
    confidence: float = Field(default=0.0, description="Confidence in [0,1]")
    evidence_span: str = Field(default="", description="Short supporting quote from chunk")
    description: str = Field(default="", description="One-line concept explanation")


class _FrameworkSignal(BaseModel):
    name: str = Field(description="Framework name")
    confidence: float = Field(default=0.0, description="Confidence in [0,1]")
    evidence_span: str = Field(default="", description="Short supporting quote from chunk")
    summary: str = Field(default="", description="One-line framework explanation")


class _ChunkExtraction(BaseModel):
    concepts: list[_ConceptSignal] = Field(default_factory=list)
    frameworks: list[_FrameworkSignal] = Field(default_factory=list)


@dataclass(frozen=True)
class ChunkExtractionResult:
    concepts: list[dict[str, Any]]
    frameworks: list[dict[str, Any]]
    error: str | None = None


def _extract_model_name() -> str:
    return os.getenv("INGEST_EXTRACT_MODEL", "llama3.1:8b")


def _extract_retries() -> int:
    raw = os.getenv("INGEST_EXTRACT_RETRIES", "2")
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_RETRIES: {raw!r}") from e
    return max(0, value)


def _extract_temperature() -> float:
    raw = os.getenv("INGEST_EXTRACT_TEMPERATURE", "0")
    try:
        return float(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_TEMPERATURE: {raw!r}") from e


def _extract_timeout_seconds() -> float:
    raw = os.getenv("INGEST_EXTRACT_TIMEOUT_SEC", "30")
    try:
        value = float(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_TIMEOUT_SEC: {raw!r}") from e
    return max(1.0, value)


def _extract_hard_timeout_seconds() -> float:
    raw = os.getenv("INGEST_EXTRACT_HARD_TIMEOUT_SEC", "")
    if not raw.strip():
        return _extract_timeout_seconds() + 5.0
    try:
        value = float(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_HARD_TIMEOUT_SEC: {raw!r}") from e
    return max(1.0, value)


def _extract_max_chars() -> int:
    raw = os.getenv("INGEST_EXTRACT_MAX_CHARS", "2500")
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_MAX_CHARS: {raw!r}") from e
    return max(500, value)


def extract_concurrency() -> int:
    """Max concurrent LLM extraction calls (INGEST_EXTRACT_CONCURRENCY, default 4)."""
    raw = os.getenv("INGEST_EXTRACT_CONCURRENCY", "4")
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_CONCURRENCY: {raw!r}") from e
    return max(1, value)


def _build_runtime() -> ChatOllama:
    base_url = os.getenv("OLLAMA_LLM_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = _extract_model_name()
    temperature = _extract_temperature()
    timeout = _extract_timeout_seconds()
    logger.info("Extractor: model=%s base_url=%s timeout=%.1fs", model, base_url, timeout)
    return ChatOllama(
        model=model,
        base_url=base_url,
        temperature=temperature,
        timeout=timeout,
    )


_runtime: ChatOllama | None = None


def _model_runtime() -> ChatOllama:
    global _runtime
    if _runtime is None:
        _runtime = _build_runtime()
    return _runtime


def _prompt_for_chunk(*, title: str, source_slug: str, chunk_text: str) -> str:
    return (
        "You extract product-thinking knowledge from one text chunk.\n"
        "Return JSON only and follow the schema exactly.\n"
        "Rules:\n"
        "- Prefer precision over recall.\n"
        "- confidence must be between 0 and 1.\n"
        "- evidence_span must be a short exact quote from this chunk when possible.\n"
        "- Do not invent entities not present in the chunk.\n\n"
        f"Document title: {title}\n"
        f"Source slug: {source_slug}\n"
        "Chunk:\n"
        f"{chunk_text}\n"
    )


def _clip_text(value: str, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, value))


def _result_from_parsed(parsed: _ChunkExtraction) -> ChunkExtractionResult:
    concepts = [
        {
            "name": item.name.strip(),
            "confidence": _clamp_confidence(item.confidence),
            "evidence_span": item.evidence_span.strip(),
            "description": item.description.strip(),
        }
        for item in parsed.concepts
        if item.name.strip()
    ]
    frameworks = [
        {
            "name": item.name.strip(),
            "confidence": _clamp_confidence(item.confidence),
            "evidence_span": item.evidence_span.strip(),
            "summary": item.summary.strip(),
        }
        for item in parsed.frameworks
        if item.name.strip()
    ]
    return ChunkExtractionResult(concepts=concepts, frameworks=frameworks)


def _coerce_raw_content_to_text(raw: Any) -> str:
    if raw is None:
        return ""
    content = getattr(raw, "content", raw)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _extract_json_blob(text: str) -> str | None:
    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1)

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return None


def _parse_structured_from_raw(raw: Any) -> _ChunkExtraction | None:
    raw_text = _coerce_raw_content_to_text(raw).strip()
    if not raw_text:
        return None
    candidates = [raw_text]
    json_blob = _extract_json_blob(raw_text)
    if json_blob and json_blob != raw_text:
        candidates.append(json_blob)

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            return _ChunkExtraction.model_validate(payload)
        except Exception:  # noqa: BLE001
            continue
    return None


def _coerce_structured_result(result: dict[str, Any]) -> ChunkExtractionResult:
    parsed = result.get("parsed")
    parsing_error = result.get("parsing_error")
    if isinstance(parsed, _ChunkExtraction):
        return _result_from_parsed(parsed)
    if parsing_error is not None:
        salvaged = _parse_structured_from_raw(result.get("raw"))
        if salvaged is not None:
            logger.warning("extract fallback recovered malformed structured output")
            return _result_from_parsed(salvaged)
        raise RuntimeError(f"structured parsing error: {parsing_error}")
    if parsed is None:
        raise RuntimeError("structured parsing returned empty payload")
    return _result_from_parsed(_ChunkExtraction.model_validate(parsed))


async def extract_chunk_signals_async(*, title: str, source_slug: str, chunk_text: str) -> ChunkExtractionResult:
    if not chunk_text.strip():
        return ChunkExtractionResult(concepts=[], frameworks=[])

    runtime = _model_runtime()
    structured = runtime.with_structured_output(_ChunkExtraction, include_raw=True)
    prompt = _prompt_for_chunk(
        title=title,
        source_slug=source_slug,
        chunk_text=_clip_text(chunk_text, _extract_max_chars()),
    )
    attempts = _extract_retries() + 1

    for attempt in range(1, attempts + 1):
        try:
            result = await asyncio.wait_for(
                structured.ainvoke(prompt),
                timeout=_extract_hard_timeout_seconds(),
            )
            if not isinstance(result, dict):
                raise RuntimeError(f"unexpected structured output type: {type(result)!r}")
            return _coerce_structured_result(result)
        except Exception as e:  # noqa: BLE001
            if attempt >= attempts:
                return ChunkExtractionResult(
                    concepts=[],
                    frameworks=[],
                    error=f"{type(e).__name__}: {e}",
                )
            logger.warning("extract retry %d/%d failed: %s", attempt, attempts, e)

    return ChunkExtractionResult(concepts=[], frameworks=[], error="unexpected extraction failure")


async def extract_chunk_signals_batch(
    jobs: list[tuple[str, str, str]],
    *,
    concurrency: int,
) -> list[ChunkExtractionResult]:
    """Run chunk extractions concurrently; order of results matches ``jobs``."""
    if not jobs:
        return []

    total = len(jobs)
    semaphore = asyncio.Semaphore(concurrency)
    progress_lock = asyncio.Lock()
    completed = 0

    async def one(title: str, source_slug: str, chunk_text: str) -> ChunkExtractionResult:
        nonlocal completed
        async with semaphore:
            result = await extract_chunk_signals_async(
                title=title,
                source_slug=source_slug,
                chunk_text=chunk_text,
            )
        async with progress_lock:
            completed += 1
            logger.info("Extractor: progress %d/%d", completed, total)
        return result

    return await asyncio.gather(*[one(t, s, c) for t, s, c in jobs])


def extract_chunk_signals(*, title: str, source_slug: str, chunk_text: str) -> ChunkExtractionResult:
    if not chunk_text.strip():
        return ChunkExtractionResult(concepts=[], frameworks=[])

    runtime = _model_runtime()
    structured = runtime.with_structured_output(_ChunkExtraction, include_raw=True)
    prompt = _prompt_for_chunk(
        title=title,
        source_slug=source_slug,
        chunk_text=_clip_text(chunk_text, _extract_max_chars()),
    )
    attempts = _extract_retries() + 1

    for attempt in range(1, attempts + 1):
        try:
            result = structured.invoke(prompt)
            return _coerce_structured_result(result)
        except Exception as e:  # noqa: BLE001
            if attempt >= attempts:
                return ChunkExtractionResult(
                    concepts=[],
                    frameworks=[],
                    error=f"{type(e).__name__}: {e}",
                )
            logger.warning("extract retry %d/%d failed: %s", attempt, attempts, e)

    return ChunkExtractionResult(concepts=[], frameworks=[], error="unexpected extraction failure")
