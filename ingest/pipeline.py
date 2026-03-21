from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ingest.embedder import embed_text
from ingest.supabase_loader import load_documents_and_chunks

STAGES = ("parse", "chunk", "embed", "extract", "load", "project")


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


@dataclass(frozen=True)
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    metadata: dict[str, Any]
    embedding: list[float] | None = None


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
        metadata[key.strip()] = raw_value.strip().strip("'").strip('"')
    return metadata, body


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
    )


def build_chunks(document: ParsedDocument, max_words: int = 220) -> list[ChunkRecord]:
    metadata, body = _parse_frontmatter(document.raw_markdown)
    _ = metadata
    words = body.split()
    if not words:
        return []

    chunks: list[ChunkRecord] = []
    idx = 0
    for offset in range(0, len(words), max_words):
        chunk_words = words[offset : offset + max_words]
        content = " ".join(chunk_words).strip()
        chunks.append(
            ChunkRecord(
                id=stable_chunk_id(document.source_slug, idx),
                document_id=document.id,
                chunk_index=idx,
                content=content,
                token_count=len(chunk_words),
                metadata={
                    "source_slug": document.source_slug,
                    "source_type": document.source_type,
                },
            )
        )
        idx += 1
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
    paths = sorted(input_dir.rglob("*.md"))
    docs = [parse_document(path) for path in paths]

    if source_filter:
        docs = [doc for doc in docs if doc.source_type == source_filter]
    docs = [doc for doc in docs if _is_after_since(doc, since_dt)]
    if limit is not None:
        docs = docs[:limit]

    stage_stats = {stage: {"processed": 0, "skipped": 0} for stage in STAGES}
    all_chunks: list[ChunkRecord] = []
    processed_docs: list[ParsedDocument] = []
    pending_state_updates: dict[str, dict[str, str]] = {}

    for doc in docs:
        previous = state["documents"].get(doc.source_slug)
        unchanged = (not force) and previous and previous.get("checksum") == doc.checksum

        if "parse" in stages:
            stage_stats["parse"]["processed"] += 1

        if unchanged:
            for stage in stages:
                if stage != "parse":
                    stage_stats[stage]["skipped"] += 1
            continue

        processed_docs.append(doc)

        if "chunk" in stages:
            chunks = build_chunks(doc)

            if "embed" in stages:
                for idx, chunk in enumerate(chunks):
                    chunks[idx] = ChunkRecord(
                        id=chunk.id,
                        document_id=chunk.document_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        token_count=chunk.token_count,
                        metadata=chunk.metadata,
                        embedding=embed_text(chunk.content),
                    )
            all_chunks.extend(chunks)
            stage_stats["chunk"]["processed"] += 1

        for stage in ("embed", "extract", "load", "project"):
            if stage in stages:
                stage_stats[stage]["processed"] += 1

        pending_state_updates[doc.source_slug] = {
            "checksum": doc.checksum,
            "updated_at": doc.updated_at,
            "document_id": doc.id,
        }

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

    run_payload = {
        "run_at": datetime.now(UTC).isoformat(),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "stages": list(stages),
        "counts": {
            "matched_documents": len(docs),
            "processed_documents": len(processed_docs),
            "chunks_created": len(all_chunks),
        },
        "stage_stats": stage_stats,
    }

    if "load" in stages and (documents_payload or chunks_payload):
        run_payload["load_result"] = load_documents_and_chunks(documents_payload, chunks_payload)

    state["documents"].update(pending_state_updates)

    _write_json(output_dir / "documents.json", documents_payload)
    _write_json(output_dir / "chunks.json", chunks_payload)
    _write_json(output_dir / "last_run.json", run_payload)
    _write_json(checkpoint_path, state)

    return run_payload

