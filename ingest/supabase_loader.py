from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from supabase import Client, create_client

logger = logging.getLogger(__name__)


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


def _supabase_credentials() -> tuple[str, str]:
    dotenv_values = _read_dotenv(Path(".env"))
    url = os.getenv("SUPABASE_URL") or dotenv_values.get("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_KEY")
        or dotenv_values.get("SUPABASE_SECRET_KEY")
        or dotenv_values.get("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError(
            "Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_SECRET_KEY "
            "(or SUPABASE_KEY) in environment or .env."
        )
    return url, key


def _chunked(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def load_documents_and_chunks(
    documents: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    batch_size: int = 500,
) -> dict[str, int]:
    url, key = _supabase_credentials()
    supabase: Client = create_client(url, key)

    document_fields = {
        "id",
        "source_type",
        "source_slug",
        "title",
        "published_at",
        "word_count",
        "description",
        "raw_markdown",
        "checksum",
        "ingested_at",
        "updated_at",
    }
    chunk_fields = {
        "id",
        "document_id",
        "chunk_index",
        "content",
        "token_count",
        "metadata",
        "embedding",
    }
    document_rows = [{k: v for k, v in row.items() if k in document_fields} for row in documents]
    chunk_rows = [{k: v for k, v in row.items() if k in chunk_fields} for row in chunks]

    if document_rows:
        logger.info("  upserting %d document row(s)", len(document_rows))
        supabase.table("documents").upsert(document_rows, on_conflict="id").execute()
    if chunk_rows:
        batches = _chunked(chunk_rows, batch_size)
        for batch_index, page in enumerate(batches, start=1):
            logger.info(
                "  chunks batch %d/%d (%d row(s))",
                batch_index,
                len(batches),
                len(page),
            )
            sanitized = [{k: v for k, v in row.items() if k in chunk_fields} for row in page]
            supabase.table("chunks").upsert(sanitized, on_conflict="id").execute()

    return {
        "documents_upserted": len(document_rows),
        "chunks_upserted": len(chunk_rows),
    }

