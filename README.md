# LennyVerse

AI-powered product wisdom platform built as a monorepo.

## Monorepo Layout

- `backend/` - FastAPI service scaffold
- `frontend/` - Vite + Tailwind app scaffold
- `data-pipeline/` - ingestion, schema migrations, and verification scripts
- `data/lennys-newsletterpodcastdata/` - canonical corpus directory

## Phase 1 Quickstart

1. Copy env:
   - `cp .env.example .env`
2. Install Python deps:
   - `make setup`
3. Normalize dataset location:
   - `make normalize-data`
4. Apply database schema:
   - `make migrate`
5. Run ingestion:
   - `make ingest`
6. Verify ingest:
   - `make verify`

## Common Commands

- API server: `make run-api`
- Dry-run ingest (no writes): `make ingest-dry-run`
- Tests: `make test`

## Operational Runbook (Phase 1)

- **Malformed frontmatter**: parser logs warnings and skips bad files; re-run after fixing source files.
- **Supabase paused / cold start**: retry `make migrate` or `make ingest` after project wake-up in dashboard.
- **Embedding endpoint timeout**: ensure Ollama/NIM is reachable at `OLLAMA_EMBED_BASE_URL`, then retry ingest.
