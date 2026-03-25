# Design Spec: RAG Search + Chat (Balanced, UX-First)

## Context

This spec defines the next implementation slice after completing:
- Data pipeline (ingestion, chunking, embeddings, Supabase storage)
- Landing page knowledge graph

Goal: deliver a balanced, UX-first RAG experience that combines semantic search and grounded chat in one unified workspace.

LLM integration requirement for this slice: use an OpenAI API-compatible interface so the backend can target OpenAI or compatible providers without changing application contracts.

## Scope

### In Scope
- Unified `/search` workspace with one input
- `/api/search` endpoint for semantic retrieval
- `/api/chat` endpoint for retrieval-augmented answer streaming
- Citation-linked UX between answer and sources
- Critical-path tests for reliability and UX behavior

### Out of Scope (for this slice)
- Agentic syllabus/quiz generator
- Graph deep-link/pan integration ("View in Graph")
- Full production hardening across all observability/security concerns

## Approach Selection

Chosen approach: **Unified search workspace** (recommended option A).

Why:
- Best UX coherence: ask, read, verify in one flow
- Strong demo narrative for interviews/hackathon judges
- Maintains trust by keeping evidence visible while answers stream

Alternatives considered:
- Two-tab Search/Chat split (simpler boundaries, weaker flow)
- Chat-first with retrieval drawer (cleaner layout, weaker default source visibility)

## Architecture and Components

### Frontend (`/search`)
- **Unified input**: one prompt field triggers retrieval + chat.
- **Answer stream panel (top)**: token-by-token grounded response.
- **Sources list (bottom-left)**: ranked retrieved chunks with metadata.
- **Source detail panel (bottom-right)**: selected source context with highlighted cited span.

### Backend (FastAPI)
- `POST /api/search`: semantic retrieval and ranked source return.
- `POST /api/chat` (SSE): retrieval + generation with streaming answer and citation events.
- Shared retrieval service used by both endpoints to ensure ranking and citation consistency.

### Shared retrieval contract
- Stable `search_result.id` per chunk
- Chat citation references use same IDs (`source_ref.id`)
- Enables real-time UI synchronization when citation events arrive

## Data Flow

### Search flow
1. User submits query in unified input.
2. Frontend requests `/api/search`.
3. Backend embeds query and runs pgvector similarity on `chunks.embedding`.
4. Backend joins `content` metadata and returns normalized ranked results.
5. UI renders source rows immediately.

### Chat flow
1. Same query triggers `/api/chat` SSE.
2. Backend calls same retrieval service first.
3. Top-k sources are packed into model context.
4. Server streams:
   - `answer_delta`
   - `citation_used` (as claims reference specific sources)
   - `done` (latency/tokens/source_count summary)
5. UI highlights cited source rows in real time.

## API Contract (Shape)

### Request contracts
- `POST /api/search`
  - Body: `{ "query": string, "k"?: number, "filters"?: { "tags"?: string[], "date_from"?: string, "date_to"?: string, "type"?: "podcast" | "newsletter" } }`
  - Notes: query is sent in JSON body to avoid URL length/logging issues for long prompts.
- `POST /api/chat` (SSE response)
  - Body: `{ "query": string, "k"?: number, "filters"?: {...}, "history"?: ChatMessage[] }`
  - `history` is optional and capped to a small recent window for this slice (for example, last 4 turns).
  - `ChatMessage` shape: `{ "role": "user" | "assistant", "content": string }` in chronological order.

### `/api/search` response
- `query`: string
- `results`: `SearchResult[]`
  - `id` (chunk-stable)
  - `score` (`0.0..1.0` normalized similarity)
  - `title`
  - `guest`
  - `date`
  - `tags[]`
  - `excerpt`
  - `content_id`
  - `chunk_index`

### `/api/chat` SSE events
- `answer_delta`
  - `text_delta`
- `citation_used`
  - `source_ref.id` (matches `SearchResult.id`)
  - optional excerpt span metadata
- `error`
  - `code`
  - `message`
  - `retryable`
- `done`
  - `latency_ms`
  - `token_usage` (`input_tokens`, `output_tokens`, `total_tokens`)
  - `source_count`
  - `partial` (boolean)

### SSE lifecycle rules
- If stream opens successfully, it always terminates with exactly one `done` event.
- Recoverable generation failures emit `error` followed by `done { partial: true }`.
- Failures before SSE initialization return non-2xx HTTP JSON error (no SSE frame).

## Reliability, Error Handling, and UX Guarantees

### Timeout behavior
- Retrieval timeout (short): return graceful retry state.
- Generation timeout (longer): preserve partial answer and keep sources visible.

### Degraded mode behavior
- If chat fails but search succeeds:
  - Keep ranked sources visible.
  - Show retry action: "Generate answer from these sources."
  - Stream emits `error` then `done { partial: true }` so frontend can close cleanly.
- If citation parse fails for some text:
  - Mark as uncited instead of implying certainty.

### Empty-result policy
- If retrieval returns no results, chat does not fabricate an answer.
- UI shows "insufficient evidence" guidance and suggested broader follow-up queries.
- SSE returns a short grounded response plus `done` with `source_count: 0`.

### Grounding guardrails
- Prompt policy: grounded-only answering from retrieved evidence.
- If evidence is weak, answer explicitly communicates uncertainty.
- Citation density check before `done` for factual outputs.
  - Initial rule for this slice: at least one citation for every two factual statements in final answer.
  - Factual statement detection uses sentence-level heuristics (declarative statements excluding obvious hedges/opinions).
  - If rule fails, backend appends uncertainty/disclaimer text and marks the uncited portions.

### UX guarantees
- Immediate feedback text while working ("Searching Lenny's archive...").
- Early perceived responsiveness via quick prelude before answer stream.
- Source rows appear as soon as retrieval is complete, not after final answer.

## Testing Strategy

Balanced coverage for critical path only.

### Backend tests
- Retrieval ranking sanity for known queries
- `/api/search` response contract and empty-result behavior
- `/api/chat` SSE event sequencing
- Timeout and degraded-mode handling

### Frontend tests
- Unified input triggers retrieval rendering + answer stream
- Citation/source synchronization interactions
- Error banners and retry actions for partial failures
- Source detail rendering from selected source row

## Acceptance Criteria

1. User asks a question and sees a streaming answer with visible citations.
2. Typical PM/growth queries return at least three relevant source rows.
3. Partial failures never dead-end the interface; actionable next steps remain.
4. Two to three golden prompts run reliably for demo/interview flow.

## Risks and Mitigations

- **Risk:** slow first token harms perceived quality.
  - **Mitigation:** immediate status/prelude messaging and prompt size control.
- **Risk:** inconsistent source IDs between search/chat.
  - **Mitigation:** single shared retrieval service and contract tests.
- **Risk:** overconfident uncited model output.
  - **Mitigation:** grounding prompt + citation density checks + uncited labeling.

## Proposed Work Breakdown (for planning handoff)

1. Define shared retrieval module and schemas
2. Implement `/api/search`
3. Implement `/api/chat` SSE with citation events
4. Build `/search` unified workspace UI
5. Wire citation/source sync and source detail pane
6. Add critical-path backend + frontend tests
7. Validate with golden prompts and UX smoke checks

## Definition of Done for This Slice

This slice is done when the `/search` experience delivers a smooth, grounded search-plus-chat loop with reliable citations, graceful partial failure behavior, and passing critical-path tests.
