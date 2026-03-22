from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_text_splitters import MarkdownTextSplitter

from ingest.embedder import embed_batch_size, embed_texts
from ingest.extractor import extract_chunk_signals_batch, extract_concurrency
from ingest.neo4j_projector import ProjectionPayload, project_to_neo4j
from ingest.supabase_loader import load_documents_and_chunks

STAGES = ("parse", "chunk", "embed", "extract", "load", "project")

# Basenames to skip when scanning for ingest markdown (repo docs, not content).
_SKIP_INGEST_MARKDOWN_NAMES = frozenset({"readme.md", "license.md"})

logger = logging.getLogger(__name__)


def chunk_params_from_env() -> tuple[int, int]:
    """Return (chunk_size_chars, chunk_overlap_chars) from env; defaults 1000 and 200."""
    size_raw = os.getenv("INGEST_CHUNK_SIZE_CHARS", "1000")
    overlap_raw = os.getenv("INGEST_CHUNK_OVERLAP_CHARS", "200")
    try:
        chunk_size = int(size_raw.strip())
    except ValueError as e:
        raise ValueError(f"Invalid INGEST_CHUNK_SIZE_CHARS: {size_raw!r}") from e
    try:
        chunk_overlap = int(overlap_raw.strip())
    except ValueError as e:
        raise ValueError(f"Invalid INGEST_CHUNK_OVERLAP_CHARS: {overlap_raw!r}") from e
    if chunk_size < 1:
        raise ValueError("INGEST_CHUNK_SIZE_CHARS must be >= 1")
    if chunk_overlap < 0:
        raise ValueError("INGEST_CHUNK_OVERLAP_CHARS must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("INGEST_CHUNK_OVERLAP_CHARS must be less than INGEST_CHUNK_SIZE_CHARS")
    return chunk_size, chunk_overlap


@dataclass(frozen=True)
class ParsedDocument:
    id: str
    source_type: str
    source_slug: str
    title: str
    published_at: str | None
    word_count: int
    description: str
    raw_markdown: str
    checksum: str
    ingested_at: str
    updated_at: str
    path: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any]
    embedding: list[float] | None = None


@dataclass(frozen=True)
class ExtractionError:
    source_slug: str
    chunk_id: str
    message: str


def slugify(value: str) -> str:
    cleaned = []
    prev_dash = False
    for char in value.lower().strip():
        if char.isalnum():
            cleaned.append(char)
            prev_dash = False
        elif not prev_dash:
            cleaned.append("-")
            prev_dash = True
    slug = "".join(cleaned).strip("-")
    return slug or "untitled"


def stable_doc_id(source_slug: str) -> str:
    return f"doc:{source_slug}"


def stable_chunk_id(source_slug: str, chunk_index: int) -> str:
    return f"chunk:{source_slug}:{chunk_index}"


def stable_guest_id(name: str) -> str:
    return f"guest:{slugify(name)}"


def stable_tag_id(name: str) -> str:
    return f"tag:{slugify(name)}"


def stable_concept_id(name: str) -> str:
    return f"concept:{slugify(name)}"


def stable_framework_id(name: str) -> str:
    return f"framework:{slugify(name)}"


def normalize_entity_name(value: str) -> str:
    return " ".join(value.strip().split())


def _split_metadata_values(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [normalize_entity_name(part.strip().strip("'").strip('"')) for part in inner.split(",")]
    parts = [part.strip() for part in value.replace("|", ",").split(",")]
    return [normalize_entity_name(part) for part in parts if normalize_entity_name(part)]


def _metadata_values(metadata: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = metadata.get(key)
        if raw:
            values.extend(_split_metadata_values(raw))
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(value)
    return deduped


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _parse_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    end = markdown.find("\n---\n", 4)
    if end == -1:
        return {}, markdown

    fm_block = markdown[4:end].splitlines()
    body = markdown[end + 5 :]
    metadata: dict[str, str] = {}
    for line in fm_block:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        normalized_key = _canonical_frontmatter_key(key)
        # Keep first value when aliases map to same canonical key.
        metadata.setdefault(normalized_key, raw_value.strip().strip("'").strip('"'))
    return metadata, body


def _canonical_frontmatter_key(key: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", "", key.strip().lower())
    aliases = {
        "sourcetype": "source_type",
        "type": "source_type",
        "sourceslug": "source_slug",
        "slug": "source_slug",
        "publishedat": "published_at",
        "publishedon": "published_at",
        "date": "published_at",
        "topic": "topics",
    }
    return aliases.get(compact, key.strip().lower())


def parse_document(path: Path) -> ParsedDocument:
    raw = path.read_text(encoding="utf-8")
    metadata, body = _parse_frontmatter(raw)

    source_type = metadata.get("source_type", "").strip().lower()
    if source_type not in {"newsletter", "podcast"}:
        source_type = "newsletter"

    title = metadata.get("title") or path.stem.replace("-", " ").title()
    source_slug = metadata.get("source_slug") or slugify(title)
    published_at = metadata.get("published_at")
    description = metadata.get("description", "")
    now = datetime.now(UTC).isoformat()

    return ParsedDocument(
        id=stable_doc_id(source_slug),
        source_type=source_type,
        source_slug=source_slug,
        title=title,
        published_at=published_at,
        word_count=len(body.split()),
        description=description,
        raw_markdown=raw,
        checksum=sha256_text(raw),
        ingested_at=now,
        updated_at=now,
        path=str(path),
        metadata=metadata,
    )


def build_chunks(
    document: ParsedDocument,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[ChunkRecord]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    _, body = _parse_frontmatter(document.raw_markdown)
    if not body.strip():
        return []

    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    texts = splitter.split_text(body)

    chunks: list[ChunkRecord] = []
    for idx, content in enumerate(texts):
        chunks.append(
            ChunkRecord(
                id=stable_chunk_id(document.source_slug, idx),
                document_id=document.id,
                chunk_index=idx,
                content=content.strip(),
                token_count=len(content),
                metadata={
                    "source_slug": document.source_slug,
                    "source_type": document.source_type,
                },
            )
        )
    return chunks


def _parse_since(since: str | None) -> datetime | None:
    if not since:
        return None
    return datetime.fromisoformat(since)


def _is_after_since(doc: ParsedDocument, since_dt: datetime | None) -> bool:
    if since_dt is None:
        return True
    if not doc.published_at:
        return False
    return datetime.fromisoformat(doc.published_at) >= since_dt


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    since: str | None = None,
    limit: int | None = None,
    stages: tuple[str, ...] = STAGES,
    source_filter: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    invalid = [stage for stage in stages if stage not in STAGES]
    if invalid:
        raise ValueError(f"Invalid stages: {invalid}")

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / "checkpoint_state.json"
    state = {"documents": {}}
    if checkpoint_path.exists():
        state = json.loads(checkpoint_path.read_text(encoding="utf-8"))

    since_dt = _parse_since(since)
    paths = sorted(
        p
        for p in input_dir.rglob("*.md")
        if p.name.lower() not in _SKIP_INGEST_MARKDOWN_NAMES
    )
    logger.info("Scanning %s — found %d markdown file(s)", input_dir, len(paths))
    docs = [parse_document(path) for path in paths]

    if source_filter:
        docs = [doc for doc in docs if doc.source_type == source_filter]
    docs = [doc for doc in docs if _is_after_since(doc, since_dt)]
    if limit is not None:
        docs = docs[:limit]

    filter_parts: list[str] = []
    if source_filter:
        filter_parts.append(f"source={source_filter}")
    if since:
        filter_parts.append(f"since={since}")
    if limit is not None:
        filter_parts.append(f"limit={limit}")
    filter_note = f" ({', '.join(filter_parts)})" if filter_parts else ""
    logger.info("Matched %d document(s) after filters%s", len(docs), filter_note)
    logger.info("Stages: %s", ", ".join(stages))

    chunk_size_chars, chunk_overlap_chars = 1000, 200
    if "chunk" in stages or "extract" in stages:
        chunk_size_chars, chunk_overlap_chars = chunk_params_from_env()
        logger.info("Chunking: size_chars=%d overlap_chars=%d", chunk_size_chars, chunk_overlap_chars)

    embed_bs = 32
    if "embed" in stages:
        embed_bs = embed_batch_size()
        logger.info("Embedding: batch_size=%d (INGEST_EMBED_BATCH_SIZE)", embed_bs)

    extract_conc = 1
    if "extract" in stages:
        extract_conc = extract_concurrency()
        logger.info("Extraction: concurrency=%d (INGEST_EXTRACT_CONCURRENCY)", extract_conc)

    stage_stats = {stage: {"processed": 0, "skipped": 0} for stage in STAGES}
    all_chunks: list[ChunkRecord] = []
    processed_docs: list[ParsedDocument] = []
    pending_state_updates: dict[str, dict[str, str]] = {}
    guest_rows_by_id: dict[str, dict[str, Any]] = {}
    tag_rows_by_id: dict[str, dict[str, Any]] = {}
    concept_rows_by_id: dict[str, dict[str, Any]] = {}
    framework_rows_by_id: dict[str, dict[str, Any]] = {}
    document_guest_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    document_tag_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    chunk_concept_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    chunk_framework_rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    extraction_errors: list[ExtractionError] = []
    pending_extractions: list[tuple[ParsedDocument, ChunkRecord]] = []

    total_docs = len(docs)
    for doc_index, doc in enumerate(docs, start=1):
        previous = state["documents"].get(doc.source_slug)
        unchanged = (not force) and previous and previous.get("checksum") == doc.checksum

        if "parse" in stages:
            stage_stats["parse"]["processed"] += 1

        if unchanged:
            for stage in stages:
                if stage != "parse":
                    stage_stats[stage]["skipped"] += 1
            logger.info(
                "[%d/%d] skip %s — unchanged checksum",
                doc_index,
                total_docs,
                doc.source_slug,
            )
            continue

        logger.info(
            "[%d/%d] process %s — %s",
            doc_index,
            total_docs,
            doc.source_slug,
            doc.title,
        )
        processed_docs.append(doc)
        chunks: list[ChunkRecord] = []

        if "chunk" in stages or "extract" in stages:
            chunks = build_chunks(
                doc,
                chunk_size=chunk_size_chars,
                chunk_overlap=chunk_overlap_chars,
            )

            if "embed" in stages:
                n_chunks = len(chunks)
                if n_chunks:
                    logger.info("  embedding %d chunk(s) for %s", n_chunks, doc.source_slug)
                step = max(1, n_chunks // 10) if n_chunks > 20 else 1
                done = 0
                for batch_start in range(0, n_chunks, embed_bs):
                    batch_end = min(batch_start + embed_bs, n_chunks)
                    slice_chunks = chunks[batch_start:batch_end]
                    vectors = embed_texts([c.content for c in slice_chunks])
                    for offset, (chunk, vec) in enumerate(zip(slice_chunks, vectors, strict=True)):
                        idx = batch_start + offset
                        chunks[idx] = ChunkRecord(
                            id=chunk.id,
                            document_id=chunk.document_id,
                            chunk_index=chunk.chunk_index,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            metadata=chunk.metadata,
                            embedding=vec,
                        )
                        done = idx + 1
                        if done == 1 or done == n_chunks or done % step == 0:
                            logger.info("    chunk %d/%d", done, n_chunks)
            if "chunk" in stages:
                all_chunks.extend(chunks)
                stage_stats["chunk"]["processed"] += 1

        if "extract" in stages:
            metadata_guests = _metadata_values(doc.metadata, ("guests", "guest"))
            metadata_tags = _metadata_values(doc.metadata, ("tags", "tag", "topics"))

            for guest_name in metadata_guests:
                guest_id = stable_guest_id(guest_name)
                guest_rows_by_id[guest_id] = {
                    "id": guest_id,
                    "name": guest_name,
                    "profile": {},
                }
                document_guest_rows_by_key[(doc.id, guest_id)] = {
                    "document_id": doc.id,
                    "guest_id": guest_id,
                    "role": "",
                    "confidence": 1.0,
                }

            for tag_name in metadata_tags:
                tag_id = stable_tag_id(tag_name.lower())
                tag_rows_by_id[tag_id] = {
                    "id": tag_id,
                    "name": tag_name.lower(),
                }
                document_tag_rows_by_key[(doc.id, tag_id)] = {
                    "document_id": doc.id,
                    "tag_id": tag_id,
                }

            for chunk in chunks:
                pending_extractions.append((doc, chunk))

        for stage in ("embed", "extract", "load", "project"):
            if stage in stages:
                stage_stats[stage]["processed"] += 1

        pending_state_updates[doc.source_slug] = {
            "checksum": doc.checksum,
            "updated_at": doc.updated_at,
            "document_id": doc.id,
        }

    if "extract" in stages and pending_extractions:
        n_pending = len(pending_extractions)
        logger.info("LLM extract: %d chunk(s), concurrency=%d", n_pending, extract_conc)
        jobs = [(d.title, d.source_slug, c.content) for d, c in pending_extractions]
        extraction_results = asyncio.run(
            extract_chunk_signals_batch(jobs, concurrency=extract_conc),
        )
        for (doc, chunk), chunk_extract in zip(pending_extractions, extraction_results, strict=True):
            if chunk_extract.error:
                extraction_errors.append(
                    ExtractionError(
                        source_slug=doc.source_slug,
                        chunk_id=chunk.id,
                        message=chunk_extract.error,
                    )
                )
                continue

            for concept in chunk_extract.concepts:
                concept_name = normalize_entity_name(str(concept.get("name", "")))
                if not concept_name:
                    continue
                concept_id = stable_concept_id(concept_name.lower())
                description = normalize_entity_name(str(concept.get("description", "")))
                concept_rows_by_id.setdefault(
                    concept_id,
                    {
                        "id": concept_id,
                        "name": concept_name.lower(),
                        "normalized_name": concept_name.lower(),
                        "description": description,
                    },
                )
                if description and len(description) > len(concept_rows_by_id[concept_id]["description"]):
                    concept_rows_by_id[concept_id]["description"] = description

                confidence = float(concept.get("confidence", 0.0))
                evidence_span = normalize_entity_name(str(concept.get("evidence_span", "")))
                key = (chunk.id, concept_id)
                previous = chunk_concept_rows_by_key.get(key)
                candidate = {
                    "chunk_id": chunk.id,
                    "concept_id": concept_id,
                    "confidence": confidence,
                    "evidence_span": evidence_span,
                }
                if previous is None or candidate["confidence"] >= previous["confidence"]:
                    chunk_concept_rows_by_key[key] = candidate

            for framework in chunk_extract.frameworks:
                framework_name = normalize_entity_name(str(framework.get("name", "")))
                if not framework_name:
                    continue
                framework_id = stable_framework_id(framework_name.lower())
                summary = normalize_entity_name(str(framework.get("summary", "")))
                confidence = float(framework.get("confidence", 0.0))
                framework_rows_by_id.setdefault(
                    framework_id,
                    {
                        "id": framework_id,
                        "name": framework_name.lower(),
                        "summary": summary,
                        "confidence": confidence,
                    },
                )
                if summary and len(summary) > len(framework_rows_by_id[framework_id]["summary"]):
                    framework_rows_by_id[framework_id]["summary"] = summary
                if confidence > framework_rows_by_id[framework_id]["confidence"]:
                    framework_rows_by_id[framework_id]["confidence"] = confidence

                evidence_span = normalize_entity_name(str(framework.get("evidence_span", "")))
                key = (chunk.id, framework_id)
                previous = chunk_framework_rows_by_key.get(key)
                candidate = {
                    "chunk_id": chunk.id,
                    "framework_id": framework_id,
                    "confidence": confidence,
                    "evidence_span": evidence_span,
                }
                if previous is None or candidate["confidence"] >= previous["confidence"]:
                    chunk_framework_rows_by_key[key] = candidate

    documents_payload = [
        {
            "id": doc.id,
            "source_type": doc.source_type,
            "source_slug": doc.source_slug,
            "title": doc.title,
            "published_at": doc.published_at,
            "word_count": doc.word_count,
            "description": doc.description,
            "raw_markdown": doc.raw_markdown,
            "checksum": doc.checksum,
            "ingested_at": doc.ingested_at,
            "updated_at": doc.updated_at,
            "path": doc.path,
        }
        for doc in processed_docs
    ]
    chunks_payload = [
        {
            "id": chunk.id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "token_count": chunk.token_count,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding,
        }
        for chunk in all_chunks
    ]
    extraction_payload: dict[str, Any] = {
        "guests": sorted(guest_rows_by_id.values(), key=lambda row: row["id"]),
        "tags": sorted(tag_rows_by_id.values(), key=lambda row: row["id"]),
        "concepts": sorted(concept_rows_by_id.values(), key=lambda row: row["id"]),
        "frameworks": sorted(framework_rows_by_id.values(), key=lambda row: row["id"]),
        "document_guests": sorted(
            document_guest_rows_by_key.values(), key=lambda row: (row["document_id"], row["guest_id"])
        ),
        "document_tags": sorted(document_tag_rows_by_key.values(), key=lambda row: (row["document_id"], row["tag_id"])),
        "chunk_concepts": sorted(chunk_concept_rows_by_key.values(), key=lambda row: (row["chunk_id"], row["concept_id"])),
        "chunk_frameworks": sorted(
            chunk_framework_rows_by_key.values(), key=lambda row: (row["chunk_id"], row["framework_id"])
        ),
        "errors": [
            {"source_slug": item.source_slug, "chunk_id": item.chunk_id, "message": item.message}
            for item in extraction_errors
        ],
    }

    run_payload: dict[str, Any] = {
        "run_at": datetime.now(UTC).isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "stages": list(stages),
        "counts": {
            "matched_documents": len(docs),
            "processed_documents": len(processed_docs),
            "chunks_created": len(all_chunks),
            "guests_extracted": len(extraction_payload["guests"]),
            "tags_extracted": len(extraction_payload["tags"]),
            "concepts_extracted": len(extraction_payload["concepts"]),
            "frameworks_extracted": len(extraction_payload["frameworks"]),
            "extraction_errors": len(extraction_payload["errors"]),
        },
        "stage_stats": stage_stats,
    }
    if "chunk" in stages or "extract" in stages:
        run_payload["chunk_config"] = {
            "size_chars": chunk_size_chars,
            "overlap_chars": chunk_overlap_chars,
        }

    if "load" in stages and (
        documents_payload
        or chunks_payload
        or extraction_payload["guests"]
        or extraction_payload["tags"]
        or extraction_payload["concepts"]
        or extraction_payload["frameworks"]
    ):
        logger.info(
            "Loading to Supabase: %d document(s), %d chunk(s), %d guest(s), %d tag(s), %d concept(s), %d framework(s)",
            len(documents_payload),
            len(chunks_payload),
            len(extraction_payload["guests"]),
            len(extraction_payload["tags"]),
            len(extraction_payload["concepts"]),
            len(extraction_payload["frameworks"]),
        )
        run_payload["load_result"] = load_documents_and_chunks(
            documents_payload,
            chunks_payload,
            guests=extraction_payload["guests"],
            tags=extraction_payload["tags"],
            concepts=extraction_payload["concepts"],
            frameworks=extraction_payload["frameworks"],
            document_guests=extraction_payload["document_guests"],
            document_tags=extraction_payload["document_tags"],
            chunk_concepts=extraction_payload["chunk_concepts"],
            chunk_frameworks=extraction_payload["chunk_frameworks"],
        )
        logger.info("Load finished: %s", run_payload["load_result"])
    elif "load" in stages:
        logger.info("Load stage skipped — no documents or chunks to upsert")

    if "project" in stages:
        projection_payload: ProjectionPayload = {
            "documents": documents_payload,
            "chunks": chunks_payload,
            "guests": extraction_payload["guests"],
            "tags": extraction_payload["tags"],
            "concepts": extraction_payload["concepts"],
            "frameworks": extraction_payload["frameworks"],
            "document_guests": extraction_payload["document_guests"],
            "document_tags": extraction_payload["document_tags"],
            "chunk_concepts": extraction_payload["chunk_concepts"],
            "chunk_frameworks": extraction_payload["chunk_frameworks"],
        }
        try:
            logger.info(
                "Starting Neo4j projection: %d document(s), %d chunk(s), %d guest(s), %d tag(s), "
                "%d concept(s), %d framework(s)",
                len(documents_payload),
                len(chunks_payload),
                len(extraction_payload["guests"]),
                len(extraction_payload["tags"]),
                len(extraction_payload["concepts"]),
                len(extraction_payload["frameworks"]),
            )
            run_payload["projection_result"] = project_to_neo4j(projection_payload, clear_first=False)
            logger.info("Projection finished: %s", run_payload["projection_result"])
        except Exception as exc:
            run_payload["projection_error"] = {
                "type": type(exc).__name__,
                "message": str(exc),
            }
            if exc.__cause__ is not None:
                run_payload["projection_error"]["cause"] = str(exc.__cause__)
            logger.error("Neo4j projection failed (%s): %s", type(exc).__name__, exc)
            logger.info("Writing artifacts to %s (projection failed; checkpoint unchanged)", output_dir)
            _write_json(output_dir / "documents.json", documents_payload)
            _write_json(output_dir / "chunks.json", chunks_payload)
            _write_json(output_dir / "extractions.json", extraction_payload)
            _write_json(output_dir / "last_run.json", run_payload)
            _write_json(checkpoint_path, state)
            raise

    state["documents"].update(pending_state_updates)

    logger.info("Writing artifacts to %s", output_dir)
    _write_json(output_dir / "documents.json", documents_payload)
    _write_json(output_dir / "chunks.json", chunks_payload)
    _write_json(output_dir / "extractions.json", extraction_payload)
    _write_json(output_dir / "last_run.json", run_payload)
    _write_json(checkpoint_path, state)

    skipped_docs = total_docs - len(processed_docs)
    logger.info(
        "Done — processed %d document(s), skipped %d (unchanged), %d chunk(s), checkpoint updated",
        len(processed_docs),
        skipped_docs,
        len(all_chunks),
    )

    return run_payload

