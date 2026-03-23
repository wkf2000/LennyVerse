from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
from slugify import slugify

from data_pipeline.config import Settings
from data_pipeline.models import ParsedDocument


def _to_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        return date.fromisoformat(value)
    return None


def _normalize_tags(raw_tags: Any) -> list[str]:
    if raw_tags is None:
        return []
    if isinstance(raw_tags, list):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if isinstance(raw_tags, str):
        return [raw_tags.strip()] if raw_tags.strip() else []
    return []


def _content_type_for_path(path: Path) -> str:
    if "podcast" in path.parts:
        return "podcast"
    return "newsletter"


def _content_id(path: Path) -> str:
    return slugify(path.stem)


def parse_markdown_file(path: Path, root: Path) -> ParsedDocument:
    post = frontmatter.load(path)
    metadata = dict(post.metadata)
    body = post.content.strip()
    content_type = str(metadata.get("type") or _content_type_for_path(path))
    rel_filename = path.relative_to(root).as_posix()

    return ParsedDocument(
        id=_content_id(path),
        type=content_type,  # type: ignore[arg-type]
        title=str(metadata.get("title") or path.stem),
        date=_to_date(metadata.get("date")),
        tags=_normalize_tags(metadata.get("tags")),
        guest=str(metadata["guest"]).strip() if metadata.get("guest") else None,
        word_count=int(metadata["word_count"]) if metadata.get("word_count") else None,
        filename=rel_filename,
        subtitle=str(metadata["subtitle"]).strip() if metadata.get("subtitle") else None,
        description=str(metadata["description"]).strip() if metadata.get("description") else None,
        body=body,
        raw_metadata=metadata,
    )


def iter_markdown_files(settings: Settings) -> list[Path]:
    paths: list[Path] = []
    for directory in (settings.newsletters_dir, settings.podcasts_dir):
        if directory.exists():
            paths.extend(sorted(directory.glob("*.md")))
    return paths


def parse_corpus(settings: Settings) -> list[ParsedDocument]:
    if not settings.data_root.exists():
        raise FileNotFoundError(f"Dataset root does not exist: {settings.data_root}")

    parsed: list[ParsedDocument] = []
    for path in iter_markdown_files(settings):
        try:
            parsed.append(parse_markdown_file(path, settings.data_root))
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[warn] failed parsing {path}: {exc}")
    return parsed
