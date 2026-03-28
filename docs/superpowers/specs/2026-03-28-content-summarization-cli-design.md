# Design: Content Summarization CLI

Status: APPROVED
Date: 2026-03-28

## Problem

The LennyVerse corpus has 638 content items (newsletters + podcasts) but no precomputed summaries. Summaries would be useful for UI display, search result previews, and graph node tooltips. We need a CLI tool in the data-pipeline that calls an LLM to generate a concise summary for each content item and stores it in Supabase.

## Approach

Single-threaded sequential CLI script following the existing ingest script pattern. Uses the `openai` Python SDK (already a project dependency) pointed at a separately configured LLM endpoint. Processes content one row at a time, skips already-summarized rows by default.

### Why sequential over concurrent

- Matches existing pipeline patterns (all scripts are synchronous)
- 638 items at ~1-2 req/sec is a 10-15 minute one-time job
- Simpler error handling and debugging
- No new dependencies required

## Configuration

New env vars in `.env` (with corresponding additions to `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SUMMARIZE_API_BASE` | (required) | OpenAI-compatible base URL for summarization LLM |
| `SUMMARIZE_API_KEY` | (required) | API key for the summarization endpoint |
| `SUMMARIZE_MODEL` | (required) | Model name (e.g. `gpt-4o-mini`) |
| `SUMMARIZE_MAX_CHARS` | `8000` | Max body characters sent to the LLM |

These are added to `data_pipeline.config.Settings` as optional fields (they are only required when the summarize script runs).

## Database Changes

Migration `002_add_content_summary.sql`:

```sql
ALTER TABLE content ADD COLUMN IF NOT EXISTS summary TEXT;
```

Adds a nullable `summary` TEXT column to the existing `content` table.

## CLI Interface

```
uv run python -m data_pipeline.scripts.summarize [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Count unsummarized rows; no LLM calls or DB writes |
| `--force` | Re-summarize rows that already have a summary |
| `--limit N` | Process only first N eligible rows (for testing) |

Makefile target:

```makefile
summarize:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.summarize
```

## Processing Flow

1. Load `Settings`, connect to DB.
2. Query content rows from DB. Filter out rows with non-null `summary` unless `--force`.
3. For each eligible row:
   a. Load the markdown file via the existing `parse_markdown_file` parser.
   b. Truncate `body` to `SUMMARIZE_MAX_CHARS` characters.
   c. Call the LLM with a system prompt and the truncated body as user content.
   d. Write the returned summary to `content.summary` in DB.
   e. Print progress: `[ok] summarized "{title}" ({i}/{total})`.
4. Print final count on completion.

If an LLM call fails for a single item, log a warning and continue to the next item (do not abort the run).

## LLM Prompt

System prompt:
> Summarize the following content in 2-3 concise sentences. Focus on the key topics, insights, and takeaways.

User message: the truncated body text.

## New Files

| File | Purpose |
|------|---------|
| `data-pipeline/sql/migrations/002_add_content_summary.sql` | DB migration |
| `data-pipeline/src/data_pipeline/summarizer.py` | `SummarizerClient` class wrapping the OpenAI SDK |
| `data-pipeline/src/data_pipeline/scripts/summarize.py` | CLI entry point |

## Modified Files

| File | Change |
|------|--------|
| `data-pipeline/src/data_pipeline/config.py` | Add `SUMMARIZE_*` fields to `Settings` |
| `data-pipeline/src/data_pipeline/db.py` | Add `fetch_unsummarized_content_ids()` and `update_summary()` methods |
| `Makefile` | Add `summarize` target |
| `.env.example` | Add `SUMMARIZE_*` vars |

## Components

### `SummarizerClient` (`summarizer.py`)

- Constructor takes `Settings`, initializes `openai.OpenAI` client with `SUMMARIZE_API_BASE` and `SUMMARIZE_API_KEY`.
- `summarize(text: str) -> str` method: calls `chat.completions.create` with the system prompt and truncated text. Returns the summary string.
- Uses `tenacity` retry (same pattern as `EmbeddingClient`): 3 attempts, exponential backoff.

### DB Methods (`db.py`)

- `fetch_unsummarized_content(force: bool = False) -> list[dict]`: returns `id` and `filename` for rows needing summarization. If `force=True`, returns all rows.
- `update_summary(content_id: str, summary: str) -> None`: `UPDATE content SET summary = %s, updated_at = now() WHERE id = %s`.

### CLI Script (`scripts/summarize.py`)

- Parses args (`--dry-run`, `--force`, `--limit`).
- Loads settings, creates DB and SummarizerClient instances.
- Fetches eligible rows from DB.
- Applies `--limit` if set.
- If `--dry-run`, prints count and returns.
- Loops over rows: parse markdown file, truncate body, call summarizer, update DB, print progress.
- Catches per-item exceptions with warning log and continues.

## Success Criteria

1. `make summarize` processes all 638 content items and writes summaries to DB.
2. Re-running without `--force` is a no-op (skips all rows).
3. `--force` re-summarizes everything.
4. `--dry-run` reports count without making LLM calls.
5. `--limit N` processes only N items.
6. Individual LLM failures do not abort the run.
