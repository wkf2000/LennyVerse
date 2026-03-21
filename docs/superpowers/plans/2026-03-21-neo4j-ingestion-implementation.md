# Neo4j Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a production-grade Neo4j projection stage to local ingestion, including canonical rebuild support and deterministic graph contracts.

**Architecture:** Keep the existing pipeline as the orchestrator and add a dedicated `neo4j_projector` module for graph-specific responsibilities. `run/backfill` project from in-memory payloads, while `rebuild-graph` reads canonical Supabase tables, clears in-scope graph data, and reprojects. Failures in projection or rebuild flow must exit non-zero.

**Tech Stack:** Python 3.11, `neo4j` Python driver, Supabase Python client, pytest, existing ingestion CLI.

---

## File Structure (planned changes)

- Modify: `pyproject.toml`
  - Add Neo4j driver dependency.
- Create: `ingest/neo4j_projector.py`
  - Neo4j auth/config loading, constraint setup, node/edge upserts, rebuild clear step, projection stats.
- Modify: `ingest/pipeline.py`
  - Invoke projector during `project` stage, enforce checkpoint ordering, include projection diagnostics.
- Modify: `ingest/cli.py`
  - Replace `rebuild-graph` marker behavior with canonical fetch + projector execution.
- Modify: `ingest/supabase_loader.py`
  - Add canonical read helpers for `rebuild-graph` (documents/entities/joins/chunks links).
- Modify: `tests/test_ingest_pipeline.py`
  - Add tests for project-stage success/failure and checkpoint behavior.
- Create: `tests/test_neo4j_projector.py`
  - Unit tests for rollups, `RELATED_TO` canonicalization, idempotent payload shaping.
- Create: `tests/test_ingest_cli_rebuild_graph.py`
  - Focused tests for `rebuild-graph` command semantics.

---

### Task 1: Add Neo4j dependency and baseline test guard

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_neo4j_projector.py`

- [ ] **Step 1: Write the failing test**

```python
def test_projector_module_imports() -> None:
    import ingest.neo4j_projector as mod
    assert mod is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_neo4j_projector.py::test_projector_module_imports -v`  
Expected: FAIL with `ModuleNotFoundError` or missing dependency error.

- [ ] **Step 3: Add dependency and minimal module scaffold**

```toml
# pyproject.toml
dependencies = [
  # ...existing deps...
  "neo4j>=5.28.0",
]
```

```python
# ingest/neo4j_projector.py
"""Neo4j projection helpers for ingestion pipeline."""
```

- [ ] **Step 3.5: Refresh lockfile**

Run: `uv lock`  
Expected: `uv.lock` updated to include `neo4j`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_neo4j_projector.py::test_projector_module_imports -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock ingest/neo4j_projector.py tests/test_neo4j_projector.py
git commit -m "add neo4j projector module scaffold"
```

---

### Task 2: Implement deterministic projection payload builders

**Files:**
- Modify: `ingest/neo4j_projector.py`
- Test: `tests/test_neo4j_projector.py`

- [ ] **Step 1: Write failing unit tests for rollups and `RELATED_TO`**

```python
def test_mentions_concept_rollup_uses_sum_confidence_and_distinct_chunks():
    # assert weight == sum(confidence), evidence_count == distinct chunk_id count
    ...

def test_uses_framework_rollup_uses_sum_confidence_and_distinct_chunks():
    # assert weight == sum(confidence), evidence_count == distinct chunk_id count
    ...

def test_related_to_uses_distinct_document_count_and_canonical_direction():
    # assert edge direction lower_id -> higher_id, no self-pairs, method=cooccurrence_p0
    ...

def test_projection_builds_guest_and_tag_edges_with_stable_ids():
    # assert FEATURES_GUEST/HAS_TAG edges are emitted from joins with stable IDs
    ...
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_neo4j_projector.py -k "rollup or related_to or guest_and_tag" -v`  
Expected: FAIL on missing functions/assertions.

- [ ] **Step 3: Implement payload builders**

```python
def build_mentions_concept_edges(chunk_concepts, chunk_to_document): ...
def build_uses_framework_edges(chunk_frameworks, chunk_to_document): ...
def build_related_to_edges(chunk_concepts, chunk_to_document): ...
```

Implementation rules:
- `weight = sum(confidence)` with missing confidence treated as `0.0`
- `evidence_count = count(distinct chunk_id)`
- `RELATED_TO.weight = count(distinct document_id)`
- `RELATED_TO.method = "cooccurrence_p0"` on every edge
- one edge per unordered concept pair using lexical order (`lower_id -> higher_id`)
- self-pairs excluded

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_neo4j_projector.py -k "rollup or related_to or guest_and_tag" -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/neo4j_projector.py tests/test_neo4j_projector.py
git commit -m "add deterministic neo4j edge rollup builders"
```

---

### Task 3: Add Neo4j write layer (constraints, node upserts, relationship upserts)

**Files:**
- Modify: `ingest/neo4j_projector.py`
- Test: `tests/test_neo4j_projector.py`

- [ ] **Step 1: Write failing tests for query orchestration**

```python
def test_project_to_neo4j_executes_constraints_then_node_and_edge_batches():
    # mock neo4j session/driver and assert call order + parameters
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_neo4j_projector.py -k "constraints or project_to_neo4j" -v`  
Expected: FAIL due to missing orchestrator.

- [ ] **Step 3: Implement projector write API**

```python
class ProjectionPayload(TypedDict):
    documents: list[dict]
    chunks: list[dict]
    guests: list[dict]
    tags: list[dict]
    concepts: list[dict]
    frameworks: list[dict]
    document_guests: list[dict]
    document_tags: list[dict]
    chunk_concepts: list[dict]
    chunk_frameworks: list[dict]

def project_to_neo4j(payload: ProjectionPayload, *, clear_first=False) -> dict[str, int]:
    # ensure constraints
    # optionally clear in-scope labels/relationships
    # upsert nodes and relationships in batches
    # return counts + elapsed_ms
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_neo4j_projector.py -k "constraints or project_to_neo4j" -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/neo4j_projector.py tests/test_neo4j_projector.py
git commit -m "implement neo4j constraints and projection upserts"
```

---

### Task 4: Integrate `project` stage into pipeline with fail-run semantics

**Files:**
- Modify: `ingest/pipeline.py`
- Modify: `tests/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing integration tests for `project` stage**

```python
def test_project_stage_success_adds_projection_result(tmp_path):
    ...

def test_project_stage_failure_raises_and_does_not_update_checkpoint(tmp_path):
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_ingest_pipeline.py -k "project_stage" -v`  
Expected: FAIL because `project` is currently a no-op.

- [ ] **Step 3: Implement pipeline integration**

```python
if "project" in stages:
    run_payload["projection_result"] = project_to_neo4j(...)
```

Requirements:
- call projector only after extraction/load payloads are prepared
- build `ProjectionPayload` from in-memory pipeline artifacts (documents/chunks/entities/joins)
- include structured projection error block in `last_run` payload on failure
- enforce checkpoint update order:
  - with `project` enabled: update checkpoint only after successful projection
  - with `project` disabled: existing behavior after final enabled stage

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_ingest_pipeline.py -k "project_stage or checkpoint" -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/pipeline.py tests/test_ingest_pipeline.py
git commit -m "wire neo4j project stage into ingestion pipeline"
```

---

### Task 5: Implement canonical fetch path for `rebuild-graph`

**Files:**
- Modify: `ingest/supabase_loader.py`
- Modify: `ingest/cli.py`
- Test: `tests/test_ingest_cli_rebuild_graph.py`

- [ ] **Step 1: Write failing CLI tests for rebuild behavior**

```python
def test_rebuild_graph_reads_canonical_data_and_projects(monkeypatch, tmp_path):
    ...

def test_rebuild_graph_nonzero_on_supabase_read_failure(monkeypatch):
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_ingest_cli_rebuild_graph.py -v`  
Expected: FAIL because CLI still writes marker file.

- [ ] **Step 3: Implement canonical fetch and rebuild command**

```python
def fetch_projection_inputs() -> ProjectionPayload:
    # read canonical tables and joins from Supabase and return exact projector payload shape
```

```python
if args.command == "rebuild-graph":
    payload = fetch_projection_inputs()
    result = project_to_neo4j(payload, clear_first=True)
    print(json.dumps(result))
```

Requirements:
- clear in-scope graph labels/relationships before reproject
- non-zero exit on canonical read failure, payload assembly failure, clear failure, or write failure

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/test_ingest_cli_rebuild_graph.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest/supabase_loader.py ingest/cli.py tests/test_ingest_cli_rebuild_graph.py
git commit -m "replace rebuild-graph marker with canonical neo4j rebuild"
```

---

### Task 6: Add end-to-end regression coverage for run/backfill/rebuild contracts

**Files:**
- Modify: `tests/test_ingest_pipeline.py`
- Modify: `tests/test_ingest_cli_rebuild_graph.py`

- [ ] **Step 1: Write failing contract tests**

```python
def test_backfill_exits_nonzero_on_projection_failure(...):
    ...

def test_rebuild_graph_removes_stale_in_scope_nodes(...):
    ...

def test_rebuild_graph_identity_sets_match_canonical_projection_input(...):
    # assert node identity set keyed by (label,id) and edge set keyed by
    # (type,start_id,end_id) match canonical-derived projection input exactly
    # after normalization of optional fields and float properties
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `uv run pytest tests/test_ingest_pipeline.py tests/test_ingest_cli_rebuild_graph.py -k "backfill or stale or identity_sets" -v`  
Expected: FAIL.

- [ ] **Step 3: Implement minimal fixes to satisfy contracts**

```python
# adjust error propagation and stale-removal assertions/helpers
...
```

- [ ] **Step 4: Run targeted tests to verify pass**

Run: `uv run pytest tests/test_ingest_pipeline.py tests/test_ingest_cli_rebuild_graph.py -k "backfill or stale or identity_sets" -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ingest_pipeline.py tests/test_ingest_cli_rebuild_graph.py
git commit -m "add regression tests for rebuild and failure contracts"
```

---

### Task 7: Full verification and cleanup

**Files:**
- Modify: `ingest/*.py` and `tests/*.py` (only if final fixes are needed)

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`  
Expected: PASS with no regressions.

- [ ] **Step 2: Run lint and targeted tests**

Run: `uv run ruff check .`  
Expected: PASS.

Run: `uv run pytest tests/test_ingest_pipeline.py tests/test_neo4j_projector.py tests/test_ingest_cli_rebuild_graph.py -v`  
Expected: PASS.

- [ ] **Step 3: Apply minimal final fixes if any failures remain**

```python
# keep fixes scoped; no drive-by refactors
...
```

- [ ] **Step 4: Re-run verification**

Run: `uv run pytest -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ingest tests pyproject.toml uv.lock
git commit -m "finalize neo4j ingestion projection implementation"
```

