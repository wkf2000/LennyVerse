# TODOS

## Post-Challenge Cleanup

### Clean up dead quiz code
- **What:** Remove all quiz-related functions, schemas, and tests from `generate_service.py`, `generate_schemas.py`, `QuizOutput.tsx`, and test files.
- **Why:** ~400 lines of dead code (quiz normalization, retry, repair) that's skipped at runtime after the playbook revamp. Adds cognitive load for future contributors.
- **Effort:** human: ~30 min / CC: ~15 min
- **Depends on:** Challenge submission complete.
- **Files:** `generate_service.py` (functions: `_normalize_quiz_mc_item`, `_coerce_quiz_payload`, `_build_quiz_retry_system_prompt`, `_build_quiz_strict_json_repair_prompt`, `_quiz_int_counts_for_retry`, `_normalize_quiz_sa_item`), `generate_schemas.py` (QuizOption, MultipleChoiceQuestion, ShortAnswerQuestion, GeneratedQuiz), `QuizOutput.tsx`, `types/generate.ts` (quiz types)

### Add OG meta tags for shared playbook URLs
- **What:** Server-side inject Open Graph meta tags when serving `/playbook/:slug` so Twitter/LinkedIn show rich previews.
- **Why:** Shared playbooks currently show generic `index.html` meta tags on social media. Rich previews ("My Growth Playbook — Built with Lenny's Second Brain") would drive organic traffic and viral loop.
- **Effort:** human: ~3 hours / CC: ~20 min
- **Depends on:** Shareable playbook feature working.
- **Files:** `main.py` (intercept `/playbook/{slug}` before SPA catch-all, read playbook data, template OG tags into `index.html`)

### DRY refactor — extract shared embed_query
- **What:** Extract the duplicated `_default_embed_query` function from `rag_service.py` and `generate_service.py` into a shared module (e.g., `llm_client.py` or new `embeddings.py`).
- **Why:** Identical 10-line function in two files. Future embedding provider changes require updating both.
- **Effort:** human: ~30 min / CC: ~5 min
- **Depends on:** Nothing.
- **Files:** `rag_service.py:83`, `generate_service.py:317` → extract to `llm_client.py` or `embeddings.py`
