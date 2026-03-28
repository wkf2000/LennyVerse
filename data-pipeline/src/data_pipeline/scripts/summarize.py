from __future__ import annotations

import argparse

from data_pipeline.config import Settings
from data_pipeline.db import Database
from data_pipeline.parser import parse_markdown_file
from data_pipeline.summarizer import SummarizerClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM summaries for content items.")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible rows; no LLM calls or DB writes.")
    parser.add_argument("--force", action="store_true", help="Re-summarize rows that already have a summary.")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N eligible rows.")
    args = parser.parse_args()

    settings = Settings()
    db = Database(settings.require_db_url())
    rows = db.fetch_unsummarized_content(force=args.force)

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0.")
        rows = rows[: args.limit]

    print(f"[info] eligible content rows: {len(rows)}")

    if args.dry_run:
        return

    summarizer = SummarizerClient(settings)
    total = len(rows)
    summarized = 0

    for i, row in enumerate(rows, start=1):
        content_id = row["id"]
        title = row["title"]
        filename = row["filename"]
        file_path = settings.data_root / filename

        try:
            doc = parse_markdown_file(file_path, settings.data_root)
            body = doc.body.strip()
            if not body:
                print(f"[skip] empty body for \"{title}\" ({i}/{total})")
                continue
            truncated = body[: settings.summarize_max_chars]
            summary = summarizer.summarize(truncated)
            db.update_summary(content_id, summary)
            summarized += 1
            print(f"[ok] summarized \"{title}\" ({i}/{total})")
        except Exception as exc:
            print(f"[warn] failed \"{title}\": {exc}")

    print(f"[done] summarized {summarized}/{total} content items")


if __name__ == "__main__":
    main()
