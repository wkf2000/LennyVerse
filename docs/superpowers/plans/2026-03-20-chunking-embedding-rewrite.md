# Chunking & Embedding Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the custom word-based chunker and Google Gemini embedding provider with LangChain MarkdownTextSplitter and OllamaEmbeddings (qwen3-embedding:0.6b, 1024 dims).

**Architecture:** LangChain abstractions for both chunking and embedding. MarkdownTextSplitter handles markdown-aware text splitting with char-based sizing. OllamaEmbeddings connects to a local Ollama server for embedding generation. The pipeline dataclasses and checkpoint logic stay unchanged.

**Tech Stack:** langchain-text-splitters, langchain-ollama, Ollama (local), Supabase pgvector

---

### Task 1: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Update pyproject.toml**

Replace the `google-genai` dependency with LangChain packages:

```toml
dependencies = [
    "langchain-text-splitters>=0.3.0",
    "langchain-ollama>=0.3.0",
    "supabase>=2.28.3",
]
```

**Step 2: Install dependencies**

Run: `uv sync`
Expected: Clean install with no errors.

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "swap google-genai for langchain-text-splitters and langchain-ollama"
```

---

### Task 2: Rewrite Embedder — Tests First

**Files:**
- Modify: `tests/test_ingest_pipeline.py`
- Modify: `ingest/embedder.py`

**Step 1: Write failing tests for the new embedder**

Add these tests to `tests/test_ingest_pipeline.py`:

```python
from unittest.mock import MagicMock, patch


def test_embed_texts_calls_ollama_embed_documents():
    """embed_texts delegates to OllamaEmbeddings.embed_documents."""
    import ingest.embedder as mod

    mod._embeddings = None  # reset singleton

    fake_embeddings = MagicMock()
    fake_embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]

    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_texts(["hello", "world"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    fake_embeddings.embed_documents.assert_called_once_with(["hello", "world"])


def test_embed_text_calls_ollama_embed_query():
    """embed_text delegates to OllamaEmbeddings.embed_query."""
    import ingest.embedder as mod

    mod._embeddings = None  # reset singleton

    fake_embeddings = MagicMock()
    fake_embeddings.embed_query.return_value = [0.5, 0.6]

    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_text("hello")

    assert result == [0.5, 0.6]
    fake_embeddings.embed_query.assert_called_once_with("hello")


def test_embed_texts_empty_input_returns_empty():
    """embed_texts returns [] for empty input without calling the model."""
    import ingest.embedder as mod

    mod._embeddings = None

    fake_embeddings = MagicMock()
    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_texts([])

    assert result == []
    fake_embeddings.embed_documents.assert_not_called()
```

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_ingest_pipeline.py::test_embed_texts_calls_ollama_embed_documents tests/test_ingest_pipeline.py::test_embed_text_calls_ollama_embed_query tests/test_ingest_pipeline.py::test_embed_texts_empty_input_returns_empty -v`
Expected: FAIL — the new module shape doesn't exist yet.

**Step 3: Rewrite ingest/embedder.py**

Replace the entire file with:

```python
from __future__ import annotations

import os

from langchain_ollama import OllamaEmbeddings


def _load_embeddings() -> OllamaEmbeddings:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b")
    dim_raw = os.getenv("EMBEDDING_DIMENSION", "1024")
    try:
        dimensions = int(dim_raw)
    except ValueError as e:
        raise RuntimeError(f"Invalid EMBEDDING_DIMENSION: {dim_raw!r}") from e

    return OllamaEmbeddings(
        model=model,
        base_url=base_url,
        dimensions=dimensions,
    )


_embeddings: OllamaEmbeddings | None = None


def _runtime() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = _load_embeddings()
    return _embeddings


def embed_batch_size() -> int:
    """Max texts per embedding call (from INGEST_EMBED_BATCH_SIZE, default 32)."""
    raw = os.getenv("INGEST_EMBED_BATCH_SIZE", "32")
    try:
        n = int(raw.strip())
    except ValueError as e:
        raise RuntimeError(f"Invalid INGEST_EMBED_BATCH_SIZE: {raw!r}") from e
    return max(1, n)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed many strings; order matches ``texts``."""
    if not texts:
        return []
    return _runtime().embed_documents(texts)


def embed_text(text: str) -> list[float]:
    """Embed a single string."""
    return _runtime().embed_query(text)
```

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_ingest_pipeline.py::test_embed_texts_calls_ollama_embed_documents tests/test_ingest_pipeline.py::test_embed_text_calls_ollama_embed_query tests/test_ingest_pipeline.py::test_embed_texts_empty_input_returns_empty -v`
Expected: PASS

**Step 5: Verify OllamaEmbeddings accepts dimensions kwarg**

If step 4 fails because `OllamaEmbeddings` doesn't accept `dimensions`, update `_load_embeddings` to subclass or use the `ollama` library directly:

```python
import ollama as _ollama_lib

class _DimensionAwareEmbeddings(OllamaEmbeddings):
    dimensions: int = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        result = _ollama_lib.embed(
            model=self.model, input=texts, dimensions=self.dimensions
        )
        return [list(e) for e in result["embeddings"]]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
```

**Step 6: Commit**

```bash
git add ingest/embedder.py tests/test_ingest_pipeline.py
git commit -m "rewrite embedder: OllamaEmbeddings replacing Google Gemini"
```

---

### Task 3: Rewrite Chunking — Tests First

**Files:**
- Modify: `tests/test_ingest_pipeline.py`
- Modify: `ingest/pipeline.py`

**Step 1: Write failing test for markdown-aware chunking**

Add to `tests/test_ingest_pipeline.py`:

```python
def test_build_chunks_uses_markdown_splitter(tmp_path: Path):
    """MarkdownTextSplitter respects markdown structure in split boundaries."""
    md = "\n".join([
        "---",
        "source_type: newsletter",
        "source_slug: md-split-test",
        "title: Markdown Split Test",
        "published_at: 2026-03-20T00:00:00+00:00",
        "description: fixture",
        "---",
        "# Section One",
        "",
        "First section content that is long enough to matter. " * 10,
        "",
        "# Section Two",
        "",
        "Second section content that is also long enough. " * 10,
    ])
    doc_path = tmp_path / "post.md"
    doc_path.write_text(md, encoding="utf-8")

    parsed = parse_document(doc_path)
    chunks = build_chunks(parsed, chunk_size=200, chunk_overlap=0)

    assert len(chunks) >= 2
    assert all(c.id.startswith("chunk:md-split-test:") for c in chunks)
    assert chunks[0].document_id == "doc:md-split-test"
    # Verify stable IDs are sequential
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
```

**Step 2: Update existing chunk tests to use char-based params**

Change `test_parse_and_chunk_are_deterministic`:

```python
def test_parse_and_chunk_are_deterministic(tmp_path: Path) -> None:
    doc_path = tmp_path / "post.md"
    _write_fixture(doc_path, body_word_count=35)

    parsed_a = parse_document(doc_path)
    parsed_b = parse_document(doc_path)
    assert parsed_a.id == parsed_b.id == "doc:lenny-test-post"
    assert parsed_a.checksum == parsed_b.checksum

    chunks_a = build_chunks(parsed_a, chunk_size=30, chunk_overlap=0)
    chunks_b = build_chunks(parsed_b, chunk_size=30, chunk_overlap=0)
    assert len(chunks_a) > 0
    assert [c.id for c in chunks_a] == [c.id for c in chunks_b]
```

Change `test_build_chunks_overlap_increases_windows`:

```python
def test_build_chunks_overlap_increases_windows(tmp_path: Path) -> None:
    doc_path = tmp_path / "post.md"
    _write_fixture(doc_path, body_word_count=25)

    parsed = parse_document(doc_path)
    no_overlap = build_chunks(parsed, chunk_size=30, chunk_overlap=0)
    with_overlap = build_chunks(parsed, chunk_size=30, chunk_overlap=10)
    assert len(with_overlap) >= len(no_overlap)
```

**Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_ingest_pipeline.py -v -k "chunk"`
Expected: FAIL — `build_chunks` still expects `max_words`/`overlap_words`.

**Step 4: Rewrite build_chunks and chunk_params_from_env in pipeline.py**

Update `chunk_params_from_env`:

```python
def chunk_params_from_env() -> tuple[int, int]:
    """Return (chunk_size_chars, chunk_overlap_chars) from env; defaults 1000 and 200."""
    size_raw = os.getenv("INGEST_CHUNK_SIZE_CHARS", "1000")
    overlap_raw = os.getenv("INGEST_CHUNK_OVERLAP_CHARS", "200")
    try:
        chunk_size = int(size_raw.strip())
    except ValueError as e:
        raise ValueError(f"Invalid INGEST_CHUNK_SIZE_CHARS: {size_raw!r}") from e
    try:
        chunk_overlap = int(overlap_raw.strip())
    except ValueError as e:
        raise ValueError(f"Invalid INGEST_CHUNK_OVERLAP_CHARS: {overlap_raw!r}") from e
    if chunk_size < 1:
        raise ValueError("INGEST_CHUNK_SIZE_CHARS must be >= 1")
    if chunk_overlap < 0:
        raise ValueError("INGEST_CHUNK_OVERLAP_CHARS must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("INGEST_CHUNK_OVERLAP_CHARS must be less than INGEST_CHUNK_SIZE_CHARS")
    return chunk_size, chunk_overlap
```

Update `build_chunks`:

```python
from langchain_text_splitters import MarkdownTextSplitter


def build_chunks(
    document: ParsedDocument,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[ChunkRecord]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    _, body = _parse_frontmatter(document.raw_markdown)
    if not body.strip():
        return []

    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    texts = splitter.split_text(body)

    chunks: list[ChunkRecord] = []
    for idx, content in enumerate(texts):
        chunks.append(
            ChunkRecord(
                id=stable_chunk_id(document.source_slug, idx),
                document_id=document.id,
                chunk_index=idx,
                content=content.strip(),
                token_count=len(content),
                metadata={
                    "source_slug": document.source_slug,
                    "source_type": document.source_type,
                },
            )
        )
    return chunks
```

Remove the `_read_dotenv` and `_env_or_dotenv` helper functions from pipeline.py (they're no longer needed — use `os.getenv` directly).

Update `run_pipeline` to pass `chunk_size`/`chunk_overlap` instead of `max_words`/`overlap_words`:

- Change variables from `chunk_size_words`/`chunk_overlap_words`/`stride_words` to `chunk_size_chars`/`chunk_overlap_chars`
- Update the `build_chunks()` call to use `chunk_size=chunk_size_chars, chunk_overlap=chunk_overlap_chars`
- Update logging messages from "size_words" to "size_chars"
- Update `run_payload["chunk_config"]` keys accordingly

**Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_ingest_pipeline.py -v`
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add ingest/pipeline.py tests/test_ingest_pipeline.py
git commit -m "rewrite chunking: MarkdownTextSplitter replacing word-based splitter"
```

---

### Task 4: Update Environment Configuration

**Files:**
- Modify: `.env.example`

**Step 1: Update .env.example**

Replace the embeddings and chunking sections:

```ini
########################################
# Embeddings (Ollama — local)
########################################
OLLAMA_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=qwen3-embedding:0.6b
# Must match pgvector column dimension in schema.
EMBEDDING_DIMENSION=1024

########################################
# Ingestion CLI (local-only execution)
########################################
INGEST_INPUT_DIR=./data/raw
INGEST_OUTPUT_DIR=./data/ingest-output
INGEST_STAGES=parse,chunk,embed,extract,load,project
# MarkdownTextSplitter: character-based sizing
INGEST_CHUNK_SIZE_CHARS=1000
INGEST_CHUNK_OVERLAP_CHARS=200
INGEST_SCOPE=full

########################################
# Optional model controls / safety rails
########################################
INGEST_DRY_RUN=0
INGEST_MAX_DOCS_PER_RUN=0
INGEST_EMBED_BATCH_SIZE=32
```

Remove these lines:
- `GEMINI_API_KEY=...`
- `EMBEDDING_PROVIDER=google`
- `INGEST_CHUNK_SIZE_WORDS=...`
- `INGEST_CHUNK_OVERLAP_WORDS=...`
- `INGEST_EMBED_MIN_INTERVAL_SEC=...`
- `INGEST_EMBED_429_SLEEP_SEC=...`
- `INGEST_EMBED_429_MAX_RETRIES=...`

**Step 2: Commit**

```bash
git add .env.example
git commit -m "update .env.example for Ollama embeddings and char-based chunking"
```

---

### Task 5: Schema Migration

**Files:**
- Create: `migrations/002_embedding_dimension_1024.sql`

**Step 1: Write the migration script**

```sql
-- Migration: Increase embedding dimension from 768 to 1024
-- Requires: re-embedding all chunks after running (ingest backfill --force)

-- Drop the ANN index first
DROP INDEX IF EXISTS chunks_embedding_idx;

-- Alter the column dimension
ALTER TABLE chunks
  ALTER COLUMN embedding TYPE vector(1024);

-- Recreate the ANN index
CREATE INDEX chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

**Step 2: Run the migration against Supabase**

Run via Supabase SQL editor or CLI. Verify with:

```sql
SELECT column_name, udt_name
FROM information_schema.columns
WHERE table_name = 'chunks' AND column_name = 'embedding';
```

Expected: `udt_name` reflects the new dimension.

**Step 3: Commit**

```bash
git add migrations/002_embedding_dimension_1024.sql
git commit -m "add migration: embedding dimension 768 -> 1024"
```

---

### Task 6: Smoke Test End-to-End

**Step 1: Ensure Ollama is running with the model**

Run: `ollama pull qwen3-embedding:0.6b`
Expected: Model downloaded and ready.

**Step 2: Run a limited ingest**

Run: `uv run python -m ingest run --input data/inputs --limit 1 --stages parse,chunk,embed --force`
Expected: One document parsed, chunked with MarkdownTextSplitter, embedded via Ollama. No errors.

**Step 3: Verify embedding dimensions**

Check the output JSON:

```bash
uv run python -c "
import json
chunks = json.load(open('data/ingest-output/chunks.json'))
if chunks:
    print(f'Chunks: {len(chunks)}, dim: {len(chunks[0][\"embedding\"])}')
else:
    print('No chunks produced')
"
```

Expected: `dim: 1024`

**Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All tests PASS.

**Step 5: Final commit (if any fixups)**

```bash
git add -A
git commit -m "fixups from end-to-end smoke test"
```
