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
    *,
    guests: list[dict[str, Any]] | None = None,
    tags: list[dict[str, Any]] | None = None,
    concepts: list[dict[str, Any]] | None = None,
    frameworks: list[dict[str, Any]] | None = None,
    document_guests: list[dict[str, Any]] | None = None,
    document_tags: list[dict[str, Any]] | None = None,
    chunk_concepts: list[dict[str, Any]] | None = None,
    chunk_frameworks: list[dict[str, Any]] | None = None,
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
    guest_fields = {"id", "name", "profile"}
    tag_fields = {"id", "name"}
    concept_fields = {"id", "name", "normalized_name", "description"}
    framework_fields = {"id", "name", "summary", "confidence"}
    document_guest_fields = {"document_id", "guest_id", "role", "confidence"}
    document_tag_fields = {"document_id", "tag_id"}
    chunk_concept_fields = {"chunk_id", "concept_id", "confidence", "evidence_span"}
    chunk_framework_fields = {"chunk_id", "framework_id", "confidence", "evidence_span"}

    document_rows = [{k: v for k, v in row.items() if k in document_fields} for row in documents]
    chunk_rows = [{k: v for k, v in row.items() if k in chunk_fields} for row in chunks]
    guest_rows = [{k: v for k, v in row.items() if k in guest_fields} for row in (guests or [])]
    tag_rows = [{k: v for k, v in row.items() if k in tag_fields} for row in (tags or [])]
    concept_rows = [{k: v for k, v in row.items() if k in concept_fields} for row in (concepts or [])]
    framework_rows = [{k: v for k, v in row.items() if k in framework_fields} for row in (frameworks or [])]
    document_guest_rows = [
        {k: v for k, v in row.items() if k in document_guest_fields} for row in (document_guests or [])
    ]
    document_tag_rows = [{k: v for k, v in row.items() if k in document_tag_fields} for row in (document_tags or [])]
    chunk_concept_rows = [{k: v for k, v in row.items() if k in chunk_concept_fields} for row in (chunk_concepts or [])]
    chunk_framework_rows = [
        {k: v for k, v in row.items() if k in chunk_framework_fields} for row in (chunk_frameworks or [])
    ]

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
    if guest_rows:
        logger.info("  upserting %d guest row(s)", len(guest_rows))
        supabase.table("guests").upsert(guest_rows, on_conflict="id").execute()
    if tag_rows:
        logger.info("  upserting %d tag row(s)", len(tag_rows))
        supabase.table("tags").upsert(tag_rows, on_conflict="id").execute()
    if concept_rows:
        logger.info("  upserting %d concept row(s)", len(concept_rows))
        supabase.table("concepts").upsert(concept_rows, on_conflict="id").execute()
    if framework_rows:
        logger.info("  upserting %d framework row(s)", len(framework_rows))
        supabase.table("frameworks").upsert(framework_rows, on_conflict="id").execute()
    if document_guest_rows:
        logger.info("  upserting %d document_guest row(s)", len(document_guest_rows))
        supabase.table("document_guests").upsert(
            document_guest_rows,
            on_conflict="document_id,guest_id",
        ).execute()
    if document_tag_rows:
        logger.info("  upserting %d document_tag row(s)", len(document_tag_rows))
        supabase.table("document_tags").upsert(document_tag_rows, on_conflict="document_id,tag_id").execute()
    if chunk_concept_rows:
        logger.info("  upserting %d chunk_concept row(s)", len(chunk_concept_rows))
        supabase.table("chunk_concepts").upsert(chunk_concept_rows, on_conflict="chunk_id,concept_id").execute()
    if chunk_framework_rows:
        logger.info("  upserting %d chunk_framework row(s)", len(chunk_framework_rows))
        supabase.table("chunk_frameworks").upsert(
            chunk_framework_rows,
            on_conflict="chunk_id,framework_id",
        ).execute()

    return {
        "documents_upserted": len(document_rows),
        "chunks_upserted": len(chunk_rows),
        "guests_upserted": len(guest_rows),
        "tags_upserted": len(tag_rows),
        "concepts_upserted": len(concept_rows),
        "frameworks_upserted": len(framework_rows),
        "document_guests_upserted": len(document_guest_rows),
        "document_tags_upserted": len(document_tag_rows),
        "chunk_concepts_upserted": len(chunk_concept_rows),
        "chunk_frameworks_upserted": len(chunk_framework_rows),
    }

