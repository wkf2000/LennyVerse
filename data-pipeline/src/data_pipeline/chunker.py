from __future__ import annotations

import re

from data_pipeline.models import ChunkRecord, ParsedDocument

HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def _split_sections(markdown: str) -> list[tuple[str | None, str]]:
    matches = list(HEADER_RE.finditer(markdown))
    if not matches:
        return [(None, markdown.strip())]

    sections: list[tuple[str | None, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(markdown)
        section_text = markdown[start:end].strip()
        header = match.group(2).strip()
        sections.append((header, section_text))
    return sections


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    cleaned = text.strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    cursor = 0
    stride = chunk_size - overlap
    while cursor < len(cleaned):
        piece = cleaned[cursor : cursor + chunk_size].strip()
        if piece:
            chunks.append(piece)
        cursor += stride
    return chunks


def chunk_document(doc: ParsedDocument, chunk_size: int, overlap: int) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    chunk_index = 0
    for section_header, section_text in _split_sections(doc.body):
        for text in _chunk_text(section_text, chunk_size, overlap):
            records.append(
                ChunkRecord(
                    id=f"{doc.id}:{chunk_index}",
                    content_id=doc.id,
                    chunk_index=chunk_index,
                    text=text,
                    section_header=section_header,
                )
            )
            chunk_index += 1
    return records


def chunk_documents(documents: list[ParsedDocument], chunk_size: int, overlap: int) -> list[ChunkRecord]:
    chunks: list[ChunkRecord] = []
    for doc in documents:
        chunks.extend(chunk_document(doc, chunk_size, overlap))
    return chunks
