# Data/Foundation Layer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a P0-ready data foundation for LennyVerse using Supabase (canonical relational + vector store), Neo4j (graph projection), and a local-only Python CLI ingestion pipeline.

**Architecture:** Postgres in Supabase is the source of truth and pgvector retrieval layer. Neo4j is a derived, rebuildable projection for graph exploration features. A local Python CLI performs deterministic parse -> chunk -> embed -> extract -> load -> project stages with idempotent upserts and resumability.

**Tech Stack:** Supabase Postgres + pgvector, Neo4j (Docker), Python 3.11+, SQLAlchemy + Alembic, Neo4j Python driver, Pydantic, pytest, Docker Compose.

---

### Task 1: Scaffold Foundation Repository Layout

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/neo4j/.gitkeep`
- Create: `ingestion/pyproject.toml`
- Create: `ingestion/src/ingest/__init__.py`
- Create: `ingestion/src/ingest/cli.py`
- Create: `ingestion/tests/test_cli_smoke.py`

**Step 1: Write the failing test**

```python
from typer.testing import CliRunner
from ingest.cli import app

def test_cli_shows_help():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `cd ingestion && pytest ingestion/tests/test_cli_smoke.py -v`  
Expected: FAIL with import/module not found errors.

**Step 3: Write minimal implementation**

```python
import typer

app = typer.Typer()

@app.command()
def run():
    pass
```

**Step 4: Run test to verify it passes**

Run: `cd ingestion && pytest ingestion/tests/test_cli_smoke.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add infra/docker-compose.yml ingestion/pyproject.toml ingestion/src/ingest ingestion/tests/test_cli_smoke.py
git commit -m "chore: scaffold ingestion package and docker baseline"
```

### Task 2: Implement Canonical Supabase Schema + Migrations

**Files:**
- Create: `db/migrations/001_init_extensions.sql`
- Create: `db/migrations/002_canonical_tables.sql`
- Create: `db/migrations/003_vector_search_rpc.sql`
- Create: `db/migrations/004_ingestion_runs.sql`
- Create: `db/tests/test_schema_smoke.sql`

**Step 1: Write the failing test**

```sql
-- Assert expected tables exist
select to_regclass('public.documents') is not null as has_documents;
select to_regclass('public.chunks') is not null as has_chunks;
```

**Step 2: Run test to verify it fails**

Run: `psql "$SUPABASE_DB_URL" -f db/tests/test_schema_smoke.sql`  
Expected: FAIL / false assertions before migrations.

**Step 3: Write minimal implementation**

```sql
create extension if not exists vector with schema extensions;
create table if not exists documents (...);
create table if not exists chunks (... embedding extensions.vector(768) ...);
create index if not exists chunks_embedding_hnsw on chunks using hnsw (embedding vector_ip_ops);
```

**Step 4: Run test to verify it passes**

Run: `psql "$SUPABASE_DB_URL" -f db/tests/test_schema_smoke.sql`  
Expected: PASS / true assertions.

**Step 5: Commit**

```bash
git add db/migrations db/tests
git commit -m "feat: add canonical postgres schema and vector search rpc"
```

### Task 3: Implement Neo4j Projection Schema and Constraints

**Files:**
- Create: `graph/schema/constraints.cypher`
- Create: `graph/schema/indexes.cypher`
- Create: `graph/tests/test_constraints.cypher`
- Modify: `infra/docker-compose.yml`

**Step 1: Write the failing test**

```cypher
// verify uniqueness constraints exist
SHOW CONSTRAINTS;
```

**Step 2: Run test to verify it fails**

Run: `cypher-shell -a bolt://localhost:7687 -u neo4j -p $NEO4J_PASSWORD -f graph/tests/test_constraints.cypher`  
Expected: no required constraints found.

**Step 3: Write minimal implementation**

```cypher
CREATE CONSTRAINT document_id_unique IF NOT EXISTS FOR (n:Document) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT guest_id_unique IF NOT EXISTS FOR (n:Guest) REQUIRE n.id IS UNIQUE;
```

**Step 4: Run test to verify it passes**

Run: `cypher-shell -a bolt://localhost:7687 -u neo4j -p $NEO4J_PASSWORD -f graph/tests/test_constraints.cypher`  
Expected: required constraints present.

**Step 5: Commit**

```bash
git add graph/schema graph/tests infra/docker-compose.yml
git commit -m "feat: add neo4j schema constraints for projection model"
```

### Task 4: Build Deterministic Parse + Chunk Pipeline

**Files:**
- Create: `ingestion/src/ingest/parsers/markdown_parser.py`
- Create: `ingestion/src/ingest/chunking/policy.py`
- Create: `ingestion/tests/test_parse_frontmatter.py`
- Create: `ingestion/tests/test_chunk_determinism.py`

**Step 1: Write the failing test**

```python
def test_chunk_ids_stable_for_same_document():
    a = chunk_document(doc_text="x y z", source_slug="doc-1")
    b = chunk_document(doc_text="x y z", source_slug="doc-1")
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
```

**Step 2: Run test to verify it fails**

Run: `cd ingestion && pytest ingestion/tests/test_chunk_determinism.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
chunk_id = f"chunk:{source_slug}:{chunk_index}"
```

**Step 4: Run test to verify it passes**

Run: `cd ingestion && pytest ingestion/tests/test_parse_frontmatter.py ingestion/tests/test_chunk_determinism.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add ingestion/src/ingest/parsers ingestion/src/ingest/chunking ingestion/tests
git commit -m "feat: add deterministic parsing and chunking pipeline"
```

### Task 5: Add Embedding Provider Interface + Google Provider

**Files:**
- Create: `ingestion/src/ingest/embeddings/base.py`
- Create: `ingestion/src/ingest/embeddings/google_gemini.py`
- Create: `ingestion/src/ingest/embeddings/factory.py`
- Create: `ingestion/tests/test_embedding_provider_contract.py`
- Modify: `ingestion/src/ingest/cli.py`

**Step 1: Write the failing test**

```python
def test_provider_returns_fixed_dimension_vectors():
    provider = FakeProvider(dimension=768)
    vecs = provider.embed(["hello", "world"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 768
```

**Step 2: Run test to verify it fails**

Run: `cd ingestion && pytest ingestion/tests/test_embedding_provider_contract.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

**Step 4: Run test to verify it passes**

Run: `cd ingestion && pytest ingestion/tests/test_embedding_provider_contract.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add ingestion/src/ingest/embeddings ingestion/tests/test_embedding_provider_contract.py ingestion/src/ingest/cli.py
git commit -m "feat: add embedding provider abstraction and google implementation"
```

### Task 6: Implement Postgres Load Stage (Upserts + Run Tracking)

**Files:**
- Create: `ingestion/src/ingest/loaders/postgres_loader.py`
- Create: `ingestion/src/ingest/models/run_state.py`
- Create: `ingestion/tests/test_postgres_upsert_idempotent.py`

**Step 1: Write the failing test**

```python
def test_second_load_does_not_duplicate_rows(db):
    load_document_fixture(db, "doc:abc")
    load_document_fixture(db, "doc:abc")
    assert count_rows(db, "documents") == 1
```

**Step 2: Run test to verify it fails**

Run: `cd ingestion && pytest ingestion/tests/test_postgres_upsert_idempotent.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
insert ... on conflict (source_slug) do update set ...
```

**Step 4: Run test to verify it passes**

Run: `cd ingestion && pytest ingestion/tests/test_postgres_upsert_idempotent.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add ingestion/src/ingest/loaders ingestion/src/ingest/models ingestion/tests/test_postgres_upsert_idempotent.py
git commit -m "feat: implement idempotent postgres loader with run tracking"
```

### Task 7: Implement Neo4j Projection Stage (MERGE Upserts)

**Files:**
- Create: `ingestion/src/ingest/projectors/neo4j_projector.py`
- Create: `ingestion/tests/test_neo4j_projection_idempotent.py`

**Step 1: Write the failing test**

```python
def test_projection_merge_is_idempotent(graph_client):
    project_fixture(graph_client, "doc:abc")
    project_fixture(graph_client, "doc:abc")
    assert count_nodes(graph_client, "Document", "doc:abc") == 1
```

**Step 2: Run test to verify it fails**

Run: `cd ingestion && pytest ingestion/tests/test_neo4j_projection_idempotent.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
MERGE (d:Document {id: $document_id})
MERGE (g:Guest {id: $guest_id})
MERGE (d)-[:FEATURES_GUEST]->(g)
```

**Step 4: Run test to verify it passes**

Run: `cd ingestion && pytest ingestion/tests/test_neo4j_projection_idempotent.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add ingestion/src/ingest/projectors ingestion/tests/test_neo4j_projection_idempotent.py
git commit -m "feat: add idempotent neo4j projection stage"
```

### Task 8: End-to-End Local Runbook and Smoke Validation

**Files:**
- Create: `docs/runbooks/local-data-stack.md`
- Create: `docs/runbooks/ingestion-local-smoke.md`
- Modify: `README.md`

**Step 1: Write the failing test**

```bash
# test script expectation
./scripts/smoke_ingestion.sh
```

**Step 2: Run test to verify it fails**

Run: `./scripts/smoke_ingestion.sh`  
Expected: FAIL until runbook paths/commands are accurate.

**Step 3: Write minimal implementation**

```markdown
1. Start docker compose
2. Apply db migrations
3. Run one-document ingestion
4. Verify postgres and neo4j row/node counts
```

**Step 4: Run test to verify it passes**

Run: `./scripts/smoke_ingestion.sh`  
Expected: PASS with deterministic counts.

**Step 5: Commit**

```bash
git add docs/runbooks README.md scripts/smoke_ingestion.sh
git commit -m "docs: add local stack and ingestion smoke runbooks"
```

## Cross-Cutting Standards

- Keep changes DRY and YAGNI; avoid speculative P2/P3 schema.
- Apply TDD for each task (fail -> minimal pass -> refactor).
- Keep commits small and scoped to one task.
- Prefer deterministic IDs and explicit upsert semantics across both stores.
- Do not introduce CI/CD automation for ingestion (local-only by requirement).
