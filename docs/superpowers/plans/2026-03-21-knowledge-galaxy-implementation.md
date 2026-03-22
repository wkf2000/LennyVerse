# Knowledge Galaxy Implementation Plan (No Coding Yet)

Date: 2026-03-21  
Related spec: `docs/superpowers/specs/2026-03-21-knowledge-galaxy-design.md`  
Status: Implementation pending user sign-off

## 1) Objective

Deliver `VIZ-1 Knowledge Galaxy` as a production-scale, true-3D exploration experience over all 638 documents using backend-precomputed layout and frontend real-time rendering.

This document is implementation-ready guidance only. No coding is performed in this phase.

## 2) Execution Principles

- Keep canonical ownership model from `docs/data-foundation-layer-design.md` (Neo4j derived from canonical entities; app resilient if specific subsystems degrade).
- Ship vertical slices that are testable end-to-end.
- Favor deterministic backend snapshot generation and stable client rendering.
- Enforce strict API contracts before frontend deep integration.

## 3) Phase Plan

### Phase 1: Backend Snapshot Builder and API Contracts

### Scope

Define and implement the data-precompute pipeline plus read-only FastAPI galaxy endpoints.

### Target modules/files to create

- `backend/app/schemas/galaxy.py` (Pydantic response contracts)
- `backend/app/services/galaxy_build_service.py`
- `backend/app/services/galaxy_query_service.py`
- `backend/app/api/v1/galaxy.py`
- `backend/tests/services/test_galaxy_build_service.py`
- `backend/tests/api/test_galaxy_endpoints.py`

If the backend folder naming differs, map these to the existing FastAPI project layout while preserving boundaries.
If no backend app tree exists yet in this repository, create an equivalent greenfield structure with the same module boundaries.

### Deliverables

- Versioned snapshot artifact generation.
- Endpoints:
  - `GET /api/v1/galaxy/snapshot`
  - `GET /api/v1/galaxy/node/{id}`
- Schema versioning and compatibility metadata in responses.
- `filter_facets` is served from snapshot payload as the single canonical facet source for P0.

### Acceptance criteria

- Snapshot payload validates against schema contracts.
- Full 638-node payload is generated reproducibly from graph source.
- Endpoint latency and payload size are captured and acceptable for frontend startup.
- Failure modes (missing edges/partial data) return graceful fallback payloads or clear errors.

### Verification plan (during implementation)

Use the repo's actual scripts/paths; commands below are canonical examples.

- `uv run pytest backend/tests/services/test_galaxy_build_service.py`
- `uv run pytest backend/tests/api/test_galaxy_endpoints.py`

### Risks and mitigation

- Risk: output too large for fast startup.
  - Mitigation: compression, LOD tiers, compact node fields.
- Risk: nondeterministic layout across runs.
  - Mitigation: deterministic seed and stable sort order.

---

### Phase 2: Frontend Scene Scaffolding and Core Interaction

### Scope

Build the React + Three.js scene shell and wire initial snapshot rendering.

### Target modules/files to create

- `frontend/src/pages/KnowledgeGalaxyPage.tsx`
- `frontend/src/features/galaxy/GalaxyCanvas.tsx`
- `frontend/src/features/galaxy/galaxyScene.ts`
- `frontend/src/features/galaxy/useGalaxyData.ts`
- `frontend/src/features/galaxy/types.ts`
- `frontend/src/features/galaxy/__tests__/GalaxyCanvas.test.tsx`

Adjust path names to current frontend conventions if they differ.
If no frontend tree exists yet, create the equivalent React/Vite structure before phase tasks.

### Deliverables

- Camera controls (orbit/zoom/pan).
- Rendering layers for stars, clusters, and baseline edges.
- Hover + selection behavior wired to internal scene state.

### Acceptance criteria

- Snapshot data renders into stable 3D scene.
- Camera interactions remain smooth on representative hardware.
- Node selection is visually clear and persistent.

### Verification plan (during implementation)

Use the repo's actual scripts/paths; commands below are canonical examples.

- `npm run test -- GalaxyCanvas`
- `npm run build`

### Risks and mitigation

- Risk: frame-rate drops under full dataset.
  - Mitigation: instancing/batching and quality tiers.
- Risk: interaction state drift between React and Three.js.
  - Mitigation: single source-of-truth selection state and controlled event bridge.

---

### Phase 3: Filter/Drawer/Legend UX and Brand Theming

### Scope

Add user-facing controls and information surfaces, fully aligned with brand kit.

### Target modules/files to create

- `frontend/src/features/galaxy/GalaxyFilterPanel.tsx`
- `frontend/src/features/galaxy/GalaxyDetailDrawer.tsx`
- `frontend/src/features/galaxy/GalaxyLegend.tsx`
- `frontend/src/styles/theme/tokens.ts`
- `frontend/src/features/galaxy/__tests__/GalaxyFilterPanel.test.tsx`

### Deliverables

- Filters for tags, guests, date ranges, source types.
- Detail drawer fetched lazily from node endpoint.
- Legend that explains brightness/size/color semantics.
- Theme token mapping for palette and typography.

### Acceptance criteria

- Filtering works without losing navigation context.
- Detail drawer opens/closes reliably and handles API failures gracefully.
- UI uses brand colors and type hierarchy consistently.

### Verification plan (during implementation)

Use the repo's actual scripts/paths; commands below are canonical examples.

- `npm run test -- GalaxyFilterPanel`
- `npm run test -- GalaxyDetailDrawer`
- `npm run build`

### Risks and mitigation

- Risk: overly aggressive filtering disorients users.
  - Mitigation: dim-deemphasize default and clear reset action.
- Risk: theme mismatch with canvas overlays.
  - Mitigation: centralized design tokens used by both UI and scene styling.

---

### Phase 4: Integration, Hardening, and Release Readiness

### Scope

Complete backend/frontend integration and validate reliability/performance against success criteria.

### Target modules/files to create or update

- `frontend/src/features/galaxy/integration/*` (or equivalent integration layer)
- `backend/tests/integration/test_galaxy_snapshot_contract.py`
- `docs/` notes for operational runbook and known limits

### Deliverables

- End-to-end loading and interaction workflow.
- Performance profile across initial load and active navigation.
- Degradation behavior verified (node-only fallback, retry paths).

### Acceptance criteria

- "Whoa" first impression and usable interactivity under full corpus load.
- All core interaction loops work (load, filter, select, inspect, reset).
- Users can open full canonical document content from selected stars (PRD VIZ-1 alignment).
- No critical regressions in API contracts or frontend rendering stability.

### Verification plan (during implementation)

Use the repo's actual scripts/paths; commands below are canonical examples.

- Backend tests: `uv run pytest`
- Frontend tests: `npm run test`
- Build checks: `npm run build`
- Optional performance capture: browser performance traces for baseline scenes

### Risks and mitigation

- Risk: backend contract drift breaks client.
  - Mitigation: strict schema tests and compatibility checks.
- Risk: cross-layer failures are hard to diagnose.
  - Mitigation: structured logs with snapshot version + request correlation ids.

## 4) Dependency and Sequencing

- Phase 1 must complete before deep Phase 2 integration.
- Phase 2 can begin with mock payloads while Phase 1 contracts stabilize.
- Phase 3 depends on stable selection and data-fetch primitives from Phase 2.
- Phase 4 is blocked on completion of previous phases.

## 5) Explicit Non-Goals in This Plan

- No implementation of other visualizations (`VIZ-2`, `VIZ-3`, `VIZ-4`).
- No mobile-optimized custom 3D experience.
- No real-time graph mutation or live collaboration.

## 6) Go/No-Go Checklist for Coding Start

- Design spec approved by user.
- This implementation plan approved by user.
- Backend and frontend target directory structures confirmed.
- Test command baselines confirmed (`uv run` for Python paths).

Once this checklist is green, coding can begin in execution mode.
