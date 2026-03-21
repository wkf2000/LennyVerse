from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings

load_dotenv()


def _load_embeddings() -> OllamaEmbeddings:
    base_url = os.getenv("OLLAMA_EMBED_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b")

    logging.info(f"Loading embeddings from {base_url} with model {model}")
    return OllamaEmbeddings(
        model=model,
        base_url=base_url,
    )


_embeddings: OllamaEmbeddings | None = None


def _runtime() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = _load_embeddings()
    return _embeddings


def embed_batch_size() -> int:
    """Max texts per embedding call (from INGEST_EMBED_BATCH_SIZE, default 32)."""
    raw = os.getenv("INGEST_EMBED_BATCH_SIZE", "32")
    try:
        n = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EMBED_BATCH_SIZE: {raw!r}") from e
    return max(1, n)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed many strings; order matches ``texts``."""
    if not texts:
        return []
    return _runtime().embed_documents(texts)


def embed_text(text: str) -> list[float]:
    """Embed a single string."""
    return _runtime().embed_query(text)
