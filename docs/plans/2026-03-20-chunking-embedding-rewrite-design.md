# Chunking & Embedding Rewrite Design

Date: 2026-03-20
Status: Approved
Approach: Full LangChain (Approach A)

## Summary

Replace the custom word-based chunker and Google Gemini embedding provider with LangChain abstractions: `MarkdownTextSplitter` for chunking and `OllamaEmbeddings` for local embedding via Ollama. Switch embedding model to `qwen3-embedding:0.6b` at 1024 dimensions.

## 1) Dependencies and Environment Configuration

### Dependencies (`pyproject.toml`)

- Remove: `google-genai>=1.68.0`
- Add: `langchain-text-splitters`, `langchain-ollama`

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Ollama model name |
| `EMBEDDING_DIMENSION` | `1024` | Output vector dimensions (MRL) |
| `INGEST_CHUNK_SIZE_CHARS` | `1000` | MarkdownTextSplitter chunk_size |
| `INGEST_CHUNK_OVERLAP_CHARS` | `200` | MarkdownTextSplitter chunk_overlap |

### Removed env vars

- `GEMINI_API_KEY`, `EMBEDDING_PROVIDER` — no longer using Google
- `INGEST_EMBED_MIN_INTERVAL_SEC`, `INGEST_EMBED_429_SLEEP_SEC`, `INGEST_EMBED_429_MAX_RETRIES` — Ollama is local, no rate limits
- `INGEST_CHUNK_SIZE_WORDS`, `INGEST_CHUNK_OVERLAP_WORDS` — replaced by char-based equivalents

## 2) Embedder Module (`ingest/embedder.py`)

Complete rewrite. Replace the Gemini client with LangChain's `OllamaEmbeddings`.

### Core logic

- Instantiate `OllamaEmbeddings` with `model`, `base_url`, and `dimensions` from env vars (lazy-loaded singleton)
- `embed_texts(texts) -> list[list[float]]` calls `embeddings.embed_documents(texts)`
- `embed_text(text) -> list[float]` calls `embeddings.embed_query(text)`
- `embed_batch_size()` stays as a public function for pipeline progress logging; actual batching delegated to LangChain

### Removed

- All Google `genai` imports and client setup
- Rate-limiting/throttling logic
- 429 retry logic
- Manual `.env` reader — replaced by `os.getenv` with defaults

### Dimension handling

If `OllamaEmbeddings` doesn't natively expose a `dimensions` kwarg, pass it through Ollama model options or write a thin subclass that calls the underlying `ollama` library's `embed(dimensions=N)` directly. Public API stays the same either way.

## 3) Chunking in Pipeline (`ingest/pipeline.py`)

Replace `build_chunks()` internals with LangChain's `MarkdownTextSplitter`.

### Changes

- Import `MarkdownTextSplitter` from `langchain_text_splitters`
- Create splitter with `chunk_size` and `chunk_overlap` from env (char-based)
- Feed markdown body (after frontmatter stripping) through `splitter.split_text(body)`
- Wrap results into existing `ChunkRecord` dataclass with stable IDs
- `chunk_params_from_env()` returns `(chunk_size_chars, chunk_overlap_chars)`
- `build_chunks()` signature: `chunk_size/chunk_overlap` (chars) instead of `max_words/overlap_words`
- `token_count` on `ChunkRecord` switches to character count (or rename to `char_count`)

### Unchanged

- `ParsedDocument` dataclass
- `ChunkRecord` dataclass structure and stable ID scheme
- Frontmatter parsing (`_parse_frontmatter`)
- Pipeline checkpoint/skip logic
- Embedding loop in `run_pipeline` (iterates chunks in batches, calls new embedder)

## 4) Schema Migration

- `chunks.embedding` column: `vector(768)` → `vector(1024)`
- Drop and recreate ANN index on `embedding`
- All existing chunks need re-embedding (`ingest backfill --force` after migration)
- Deliver as a SQL migration script

## 5) Tests

### Updated tests

- `test_parse_and_chunk_are_deterministic` — use char-based params
- `test_build_chunks_overlap_increases_windows` — assert on char-based behavior

### New tests

- `test_build_chunks_uses_markdown_splitter` — verify markdown structure influences split boundaries

### Unchanged tests

- `test_rerun_skips_unchanged_documents`
- `test_force_rerun_reprocesses_unchanged_documents`

### Embedding tests

Ollama is a local service dependency. Embedding tests use mocked `OllamaEmbeddings`, no integration tests in CI.
