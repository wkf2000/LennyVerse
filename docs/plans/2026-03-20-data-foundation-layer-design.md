# LennyVerse Data/Foundation Layer Design

Date: 2026-03-20  
Scope: P0-first foundation with extension points for P1  
Status: Approved direction (Option A)

## 1) Core Architecture and Boundaries

Use a dual-store foundation with clear ownership.

- Supabase Postgres is the system of record for canonical content and product state.
- Supabase pgvector handles semantic retrieval on chunk embeddings.
- Neo4j is a derived graph projection optimized for traversal-heavy exploration.
- Python local CLI ingestion writes canonical data first, then graph projections.

### Ownership Rules

- Postgres owns truth for documents, chunks, entities, joins, and user learning state.
- Neo4j is rebuildable from canonical Postgres entities and extraction outputs.
- User-facing core flows (search, learning paths, quizzes) must continue if Neo4j is unavailable.

## 2) Canonical Schema and Graph Model

## Postgres canonical tables

- `documents`
  - `id` (uuid pk), `source_type` (`newsletter|podcast`), `source_slug` (unique), `title`, `published_at`, `word_count`, `description`, `raw_markdown`, `checksum`, `ingested_at`, `updated_at`
- `chunks`
  - `id` (uuid pk), `document_id` (fk), `chunk_index`, `content`, `token_count`, `embedding vector(...)`, `metadata jsonb`
  - unique: (`document_id`, `chunk_index`)
  - indexes: `document_id`, ANN index on `embedding`
- `guests`
  - canonical person entity table for deduplication and joins
  - `id`, `name` (unique), optional profile enrichment fields
- `tags`
  - `id`, `name` (unique)
- `concepts`
  - `id`, `name` (unique), `normalized_name`, optional `description`
- `frameworks`
  - `id`, `name` (unique), `summary`, `confidence`
- join tables
  - `document_guests(document_id, guest_id, role, confidence)`
  - `document_tags(document_id, tag_id)`
  - `chunk_concepts(chunk_id, concept_id, confidence, evidence_span)`
  - `chunk_frameworks(chunk_id, framework_id, confidence, evidence_span)`
- product-state tables (P0 enabling)
  - `learning_paths`, `learning_path_items`, `quiz_items`, `quiz_attempts`, `user_progress`

### Vector Search Contract

Define an RPC-style search function (for example `match_chunks`) that accepts:

- query embedding
- match count
- metadata filters (`tag`, `guest`, `date_range`, `source_type`)

Return:

- `chunk_id`, `document_id`, `content/excerpt`, `metadata`, `similarity`

### Neo4j projection model

Node labels:

- `Document {id}`
- `Guest {id}`
- `Tag {id}`
- `Concept {id}`
- `Framework {id}`

Relationships:

- `(Document)-[:FEATURES_GUEST]->(Guest)`
- `(Document)-[:HAS_TAG]->(Tag)`
- `(Document)-[:MENTIONS_CONCEPT {weight, evidence_count}]->(Concept)`
- `(Document)-[:USES_FRAMEWORK {weight, evidence_count}]->(Framework)`
- `(Concept)-[:RELATED_TO {weight, method}]->(Concept)`

Constraints:

- uniqueness on node `id` for each label

### Stable ID strategy (idempotency-critical)

- `doc:{source_slug}`
- `chunk:{doc_slug}:{chunk_index}`
- `guest:{slug(name)}`
- `concept:{slug(normalized_name)}`
- `framework:{slug(name)}`

Use these IDs in both Postgres and Neo4j projections.

## 3) Python CLI Ingestion Pipeline (Local Only)

Ingestion is local/manual only. No CI/CD ingestion path is required.

## CLI shape

- `python -m ingest run --input data/raw --since <date> --limit <n> --stages parse,chunk,embed,extract,load,project`
- `python -m ingest backfill --source newsletter|podcast`
- `python -m ingest rebuild-graph`

## Stage flow

1. Parse markdown + YAML frontmatter; normalize metadata and compute checksum.
2. Chunk deterministically with stable chunk IDs.
3. Embed chunks (skip unchanged content by hash/checksum).
4. Extract concepts/framework mentions with confidence and evidence.
5. Load Postgres canonical entities and joins in transactions.
6. Project to Neo4j via idempotent upserts.

## Re-run and failure semantics

- Idempotent by stable IDs and upsert patterns.
- Document-level incremental updates on checksum changes.
- Stage-level checkpoints and resumability.
- Rebuildable graph projection from canonical Postgres data.

## 4) Query Patterns and API Contracts

### Semantic Search (`DSC-1`)

- flow: query -> embed -> pgvector RPC -> optional rerank -> cited results
- output: ranked chunks + document metadata + citation anchors
- source: Postgres only

### Framework Library (`DSC-2`)

- flow: `frameworks` + evidence joins + associated entities
- output: framework summary, confidence, source citations, related guests/tags
- source: Postgres canonical tables

### Knowledge Galaxy (`VIZ-1`)

- flow: precompute graph payload from Neo4j projection
- output: `nodes[]`, `edges[]`, filters, basic visual attributes
- source: Neo4j topology + optional Postgres enrichment

### Learning Paths and Quizzes (`LRN-1`, `LRN-2`)

- flow: retrieval grounded in Postgres vectors + canonical content
- output: generated items and attempt state persisted in Postgres
- source: Postgres only

## 5) Reliability, Cost, Security, Testing

### Reliability

- track runs with `ingestion_runs` and `ingestion_run_items`
- store stage status, counts, latencies, and error payloads
- add dead-letter table for failed documents/chunks
- run periodic drift checks between canonical entities and graph projections

### Cost controls

- incremental checksum-driven ingestion
- embedding cache keyed by content hash
- precompute hot artifacts where useful (framework summaries, graph payloads)
- strict token budgets for extraction/summarization steps

### Security

- Supabase service credentials only in backend/CLI, never client
- RLS enabled for app-facing access patterns
- redact secrets and sensitive payloads in logs
- least-privilege Neo4j account for projection writes

### Testing

- unit tests: parsing, chunking determinism, ID generation
- integration tests: fixture corpus -> full pipeline -> idempotent rerun
- query contract tests: response shape, filters, citation guarantees

### P0 non-goals

- no distributed orchestration
- no real-time ingestion
- no CI/CD ingestion automation
- no mandatory Neo4j dependency for core search/learning APIs

## 6) Infrastructure and Cloud Services

All runtime services are self-hosted with Docker, except Supabase managed free tier.

### Data plane

- Supabase (free tier cloud): Postgres + pgvector as canonical store and vector retrieval
- Neo4j self-hosted in Docker: graph projection for exploration

### Application plane

- app/API self-hosted in Docker
- Redis self-hosted in Docker (cache and optional lightweight coordination)

### AI/embedding plane

- external embedding API for MVP speed (Google Gemini embedding model)
- implement a provider interface in ingestion code for future swap without schema change

### Ingestion plane

- local-only Python CLI execution
- no CI/CD pipeline requirement for ingestion

### Explicitly deferred

- observability stack/log aggregation/tracing
- managed queue/orchestration services
- autoscaling and multi-region complexity

## 7) Decision Summary

- Chosen architecture: Option A (Postgres-first + Neo4j projection)
- Scope focus: P0-first
- Runtime model: Docker self-hosted app + Redis + Neo4j, Supabase managed Postgres
- Ingestion model: local CLI only, idempotent, resumable, incremental
