from __future__ import annotations

import logging
import os
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


def _extract_max_chars() -> int:
    raw = os.getenv("INGEST_EXTRACT_MAX_CHARS", "2500")
    try:
        value = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EXTRACT_MAX_CHARS: {raw!r}") from e
    return max(500, value)


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
            parsed = result.get("parsed")
            parsing_error = result.get("parsing_error")
            if parsing_error is not None:
                raise RuntimeError(f"structured parsing error: {parsing_error}")
            if parsed is None:
                raise RuntimeError("structured parsing returned empty payload")

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
        except Exception as e:  # noqa: BLE001
            if attempt >= attempts:
                return ChunkExtractionResult(
                    concepts=[],
                    frameworks=[],
                    error=f"{type(e).__name__}: {e}",
                )
            logger.warning("extract retry %d/%d failed: %s", attempt, attempts, e)

    return ChunkExtractionResult(concepts=[], frameworks=[], error="unexpected extraction failure")
