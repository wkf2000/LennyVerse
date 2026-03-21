from __future__ import annotations

import os
import time
from pathlib import Path

from google import genai
from google.genai import errors as genai_errors
from google.genai import types


def _read_dotenv(dotenv_path: Path) -> dict[str, str]:
    if not dotenv_path.exists():
        return {}
    pairs: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        pairs[key.strip()] = raw_value.strip().strip('"').strip("'")
    return pairs


def _env_or_dotenv(name: str, dotenv_values: dict[str, str]) -> str | None:
    v = os.getenv(name)
    if v is not None and v != "":
        return v
    dv = dotenv_values.get(name)
    return dv if dv else None


def _load_embedding_runtime() -> tuple[genai.Client, str, int]:
    dotenv_values = _read_dotenv(Path(".env"))
    api_key = _env_or_dotenv("GEMINI_API_KEY", dotenv_values)
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in environment or .env.")

    model = _env_or_dotenv("EMBEDDING_MODEL", dotenv_values) or "gemini-embedding-001"
    dim_raw = _env_or_dotenv("EMBEDDING_DIMENSION", dotenv_values) or "768"
    try:
        output_dimensionality = int(dim_raw)
    except ValueError as e:
        raise RuntimeError(f"Invalid EMBEDDING_DIMENSION: {dim_raw!r}") from e

    return genai.Client(api_key=api_key), model, output_dimensionality


_client: genai.Client | None = None
_model: str | None = None
_output_dimensionality: int | None = None


def _runtime() -> tuple[genai.Client, str, int]:
    global _client, _model, _output_dimensionality
    if _client is None:
        _client, _model, _output_dimensionality = _load_embedding_runtime()
    assert _model is not None and _output_dimensionality is not None
    return _client, _model, _output_dimensionality


_dotenv_cache: dict[str, str] | None = None


def _dotenv() -> dict[str, str]:
    global _dotenv_cache
    if _dotenv_cache is None:
        _dotenv_cache = _read_dotenv(Path(".env"))
    return _dotenv_cache


_last_embed_mono: float = 0.0


def _min_interval_between_embeds() -> float:
    raw = _env_or_dotenv("INGEST_EMBED_MIN_INTERVAL_SEC", _dotenv())
    if raw is None or raw == "":
        return 1.25
    return max(0.0, float(raw))


def _throttle_before_embed() -> None:
    global _last_embed_mono
    interval = _min_interval_between_embeds()
    if interval <= 0 or _last_embed_mono <= 0:
        return
    wait = interval - (time.monotonic() - _last_embed_mono)
    if wait > 0:
        time.sleep(wait)


def _mark_embed_attempt_finished() -> None:
    global _last_embed_mono
    _last_embed_mono = time.monotonic()


def _embed_429_max_retries() -> int:
    raw = _env_or_dotenv("INGEST_EMBED_429_MAX_RETRIES", _dotenv())
    if raw is None or raw == "":
        return 12
    return max(1, int(raw))


def _embed_429_sleep_seconds(attempt: int) -> float:
    raw = _env_or_dotenv("INGEST_EMBED_429_SLEEP_SEC", _dotenv())
    base = float(raw) if raw else 65.0
    # TPM limits roll with time; wait at least one window before retrying hard.
    return min(base + 5.0 * attempt, 180.0)


def embed_text(text: str) -> list[float]:
    client, model, output_dimensionality = _runtime()
    max_retries = _embed_429_max_retries()

    for attempt in range(max_retries):
        _throttle_before_embed()
        try:
            result = client.models.embed_content(
                model=model,
                contents=text,
                config=types.EmbedContentConfig(output_dimensionality=output_dimensionality),
            )
        except genai_errors.ClientError as e:
            _mark_embed_attempt_finished()
            if e.code != 429:
                raise
            if attempt >= max_retries - 1:
                raise
            time.sleep(_embed_429_sleep_seconds(attempt))
            continue

        _mark_embed_attempt_finished()
        if not result.embeddings:
            raise RuntimeError("Gemini embedding API returned no embeddings.")
        [embedding_obj] = result.embeddings
        values = embedding_obj.values
        if not values:
            raise RuntimeError("Gemini embedding API returned empty embedding values.")
        return [float(value) for value in values]

    raise RuntimeError("Embedding failed after retries.")
