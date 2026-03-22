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
  - `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` — `project` stage and `rebuild-graph` (local Neo4j; see `.env.example`)
  - (optional) `INGEST_INPUT_DIR` — default markdown root for `run` / `backfill` when `--input` is omitted (otherwise `data/inputs`)

### Run

From the repository root, always invoke Python through `uv run`:

```bash
uv run python -m ingest run
```

Progress logs go to **stderr**; the final run summary is printed as JSON on **stdout**.

### Common options

| Flag | Purpose |
|------|---------|
| `--input DIR` | Markdown root (default: `INGEST_INPUT_DIR` from `.env`, else `data/inputs`) |
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

### Neo4j projection (`project` stage)

When `project` is included in `--stages` (the default), the pipeline upserts documents, chunks, entities, and relationships into **Neo4j** after a successful `load`. If projection fails, the run exits non-zero and the local checkpoint is not advanced for that run.

- Optional tuning: `NEO4J_PROJECTION_BATCH_SIZE` (default `500`).

Graph shape (chunk nodes, `PART_OF`, rollups, `RELATED_TO`) is documented in [`docs/data-foundation-layer-design.md`](docs/data-foundation-layer-design.md).

### Rebuild graph from canonical Supabase

`rebuild-graph` does **not** read local markdown. It fetches canonical rows from Supabase (same tables the loader writes), clears in-scope Neo4j labels, then runs a full projection. Use this after schema or projection logic changes, or to fix drift.

```bash
uv run python -m ingest rebuild-graph
```

Prints JSON stats on stdout; exits `1` on Supabase read errors or Neo4j errors. If you pass `--output`, it is ignored (compatibility only; a warning is logged).

## Knowledge Galaxy (backend, frontend, snapshot)

The **Knowledge Galaxy** UI loads graph data from the FastAPI backend. Snapshot JSON (precomputed layout + nodes/edges) is built when the snapshot endpoint runs against **Neo4j**, then written under `data/galaxy-snapshots/` by default.

More detail: [`docs/knowledge-galaxy-runbook.md`](docs/knowledge-galaxy-runbook.md).

### Prerequisites

- Same **`.env`** as ingestion for **Neo4j** (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, optional `NEO4J_DATABASE`).
- **Neo4j must already contain the graph** (e.g. ingest with `project` stage, or `uv run python -m ingest rebuild-graph`).
- **HTTP server for the API:** install once if needed:

  ```bash
  uv add uvicorn
  ```

Load env vars in the shell before starting the backend (for example `set -a && source .env && set +a` if your `.env` is valid for the shell, or export the variables you need).

### Run the backend

From the **repository root**:

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

To build snapshots from Neo4j (not only serve a static file), enable the topology source:

```bash
GALAXY_ENABLE_NEO4J_SOURCE=1 uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- **`GALAXY_SNAPSHOT_DIR`** — where JSON artifacts are written (default: `data/galaxy-snapshots`). Set to empty to disable writing files.
- **`GALAXY_SNAPSHOT_PATH`** — if set and the file exists, the API **loads that JSON** and does **not** rebuild from Neo4j. Omit or unset for a fresh Neo4j-backed build.

Health check: open `http://127.0.0.1:8000/docs` (FastAPI OpenAPI).

### Generate / refresh the galaxy snapshot

There is **no separate CLI** for snapshots; generation is triggered by calling the same endpoint the UI uses.

1. Start the backend with **`GALAXY_ENABLE_NEO4J_SOURCE=1`** and valid Neo4j credentials.
2. Request the snapshot once (writes `latest.json` and a versioned file under `GALAXY_SNAPSHOT_DIR`):

   ```bash
   curl -sS -D - "http://127.0.0.1:8000/api/v1/galaxy/snapshot" -o /dev/null
   ```

Check response headers such as `X-Galaxy-Snapshot-Source` (`neo4j` vs `artifact` vs `fallback`).

**Without HTTP** (same logic as the API, from repo root):

```bash
uv run python -c "from backend.app.services.galaxy_query_service import GalaxyQueryService; s=GalaxyQueryService(); s.get_snapshot(); print(s.last_snapshot_stats)"
```

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The galaxy client calls **`/api/v1/galaxy/...`** on the **same origin** as the page. Local **`vite.config.ts`** proxies **`/api`** to **`http://127.0.0.1:8000`**, so keep the backend on port **8000** while using `npm run dev`. In production, serve the UI and API from the same host or adjust proxy / API base URL accordingly.

Production build:

```bash
cd frontend
npm run build
```
