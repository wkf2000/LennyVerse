# LennyVerse
AI-Powered Product Wisdom Platform

## Ingestion (local CLI)

The ingest pipeline reads markdown from disk, chunks and embeds content, writes JSON artifacts under the output directory, and optionally upserts into Supabase.

### Prerequisites

- [uv](https://github.com/astral-sh/uv) for Python.
- A `.env` in the repo root (copy from `.env.example`). For a full run you need at least:
  - `OLLAMA_EMBED_BASE_URL`, `EMBEDDING_MODEL` — embeddings
  - `OLLAMA_LLM_BASE_URL`, `INGEST_EXTRACT_MODEL` — extraction stage (`extract`)
  - (optional fallback) `OLLAMA_BASE_URL` — used if specific embed/LLM URL vars are unset
  - `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (or `SUPABASE_KEY`) — load stage

### Run

From the repository root, always invoke Python through `uv run`:

```bash
uv run python -m ingest run
```

Progress logs go to **stderr**; the final run summary is printed as JSON on **stdout**.

### Common options

| Flag | Purpose |
|------|---------|
| `--input DIR` | Markdown root (default: `data/inputs`) |
| `--output DIR` | Artifacts + checkpoint (default: `data/ingest-output`) |
| `--force` | Reprocess even when document checksum is unchanged (needed after changing chunk settings or to reload Supabase) |
| `--since ISO` | Only documents with `published_at` ≥ this time |
| `--limit N` | Cap how many documents are processed |
| `--stages A,B,...` | Subset of: `parse`, `chunk`, `embed`, `extract`, `load`, `project` |

Examples:

```bash
# Full pipeline with defaults
uv run python -m ingest run

# Re-embed and reload everything (ignore local checkpoint)
uv run python -m ingest run --force

# Parse + chunk only (no API calls)
uv run python -m ingest run --stages parse,chunk

# Parse + chunk + extract + load (entities + joins)
uv run python -m ingest run --stages parse,chunk,extract,load

# Backfill one source type
uv run python -m ingest backfill --source newsletter --force
```

### Chunking (environment)

When the `chunk` stage runs, window size and overlap are read from the environment or `.env`:

- `INGEST_CHUNK_SIZE_CHARS` (default `1000`)
- `INGEST_CHUNK_OVERLAP_CHARS` (default `200`; must be smaller than chunk size)

Embeddings are sent in batches (`INGEST_EMBED_BATCH_SIZE`, default `32`) with one API call per batch.

### Extraction (environment)

When the `extract` stage runs, the pipeline performs deterministic metadata extraction for guests/tags and Ollama-backed structured extraction for concepts/frameworks:

- `INGEST_EXTRACT_MODEL` (default `llama3.1:8b`)
- `INGEST_EXTRACT_RETRIES` (default `2`)
- `INGEST_EXTRACT_TEMPERATURE` (default `0`)
- `INGEST_EXTRACT_TIMEOUT_SEC` (default `30`)
- `INGEST_EXTRACT_MAX_CHARS` (default `2500`)

Extraction artifacts are written to `extractions.json` in the output directory.

### Other commands

```bash
uv run python -m ingest rebuild-graph --output data/ingest-output
```
