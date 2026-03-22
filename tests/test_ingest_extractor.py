from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import ingest.extractor as extractor


class _FakeStructured:
    def __init__(self, *, result: dict[str, Any], delay_seconds: float = 0.0):
        self._result = result
        self._delay_seconds = delay_seconds

    async def ainvoke(self, _prompt: str) -> dict[str, Any]:
        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)
        return self._result

    def invoke(self, _prompt: str) -> dict[str, Any]:
        return self._result


class _FakeRuntime:
    def __init__(self, *, result: dict[str, Any], delay_seconds: float = 0.0):
        self._result = result
        self._delay_seconds = delay_seconds

    def with_structured_output(self, _schema: Any, include_raw: bool = True) -> _FakeStructured:
        assert include_raw is True
        return _FakeStructured(result=self._result, delay_seconds=self._delay_seconds)


def test_extract_async_salvages_fenced_json_when_parser_fails(monkeypatch) -> None:
    result = {
        "parsed": None,
        "parsing_error": RuntimeError("Invalid json output"),
        "raw": SimpleNamespace(
            content=(
                "```json\n"
                '{"concepts":[{"name":"North Star Metric","confidence":0.9,"evidence_span":"north star",'
                '"description":"Core growth metric"}],"frameworks":[]}\n'
                "```"
            )
        ),
    }
    monkeypatch.setattr(extractor, "_runtime", _FakeRuntime(result=result))
    monkeypatch.setenv("INGEST_EXTRACT_RETRIES", "0")
    out = asyncio.run(
        extractor.extract_chunk_signals_async(
            title="Doc",
            source_slug="slug",
            chunk_text="A chunk about north star metrics",
        )
    )

    assert out.error is None
    assert out.concepts == [
        {
            "name": "North Star Metric",
            "confidence": 0.9,
            "evidence_span": "north star",
            "description": "Core growth metric",
        }
    ]
    assert out.frameworks == []


def test_extract_async_hard_timeout_returns_error(monkeypatch) -> None:
    result = {
        "parsed": extractor._ChunkExtraction(concepts=[], frameworks=[]),
        "parsing_error": None,
        "raw": SimpleNamespace(content="{}"),
    }
    monkeypatch.setattr(extractor, "_runtime", _FakeRuntime(result=result, delay_seconds=1.2))
    monkeypatch.setenv("INGEST_EXTRACT_RETRIES", "0")
    monkeypatch.setenv("INGEST_EXTRACT_HARD_TIMEOUT_SEC", "0.01")
    out = asyncio.run(
        extractor.extract_chunk_signals_async(
            title="Doc",
            source_slug="slug",
            chunk_text="A chunk",
        )
    )

    assert out.concepts == []
    assert out.frameworks == []
    assert out.error is not None
    assert out.error.startswith("TimeoutError:")
