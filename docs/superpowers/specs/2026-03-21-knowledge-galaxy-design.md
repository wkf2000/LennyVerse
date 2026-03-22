# Knowledge Galaxy Design Spec (VIZ-1)

Date: 2026-03-21  
Status: Approved design baseline (implementation pending user sign-off)  
Owners: LennyVerse product + engineering

## 1) Purpose and Outcome

`VIZ-1 Knowledge Galaxy` is the hero visualization for LennyVerse. It turns 638 documents into an explorable 3D knowledge map where:

- each document is a star,
- topic clusters form constellations,
- brightness/size communicates influence,
- users can zoom, filter, and open any document detail.

Primary outcome: create a "whoa" first impression within 5 seconds while remaining practically useful for discovery and navigation.

## 2) Scope and Decisions

Confirmed decisions for this milestone:

- Full corpus at launch: all 638 documents (no curated subset for V1).
- Rendering mode: true 3D scene (Three.js).
- Architecture: backend-precomputed layout, frontend renderer-first.
- Stack direction:
  - Frontend: React + Vite + Tailwind + Three.js
  - Backend: FastAPI
- Visual language: align with `brandkit/brand-specification.md`:
  - Primary `#1B365D` (Gonzaga Navy)
  - Accent `#D77601` (PNNL Orange)
  - Neutral accent `#6A8EAE` (Steel Blue) for subtle borders/dividers
  - Light background `#EBE4D3` (Warm Cream) and `#FFFFFF`
  - Body text `#1A1A2E` (Deep Charcoal)
  - Typography hierarchy inspired by Noto Serif headings and Noto Sans body.
  - Optional numeric/legend micro-labels can use DM Mono for dense data readability.

## 3) Architecture and Boundaries

### 3.1 System boundary

- Neo4j remains topology source (derived from canonical Supabase entities).
- A backend precompute stage materializes galaxy-ready payloads.
- FastAPI serves versioned read endpoints.
- React/Three.js renders and handles interaction.

### 3.2 Why precompute

For 638 documents and non-trivial edge density, browser-side force simulation is too variable for first-load and interaction quality. Precomputing positions and visual metrics in backend provides:

- predictable first paint,
- stable cluster layout across sessions,
- smaller client CPU/GPU spikes,
- easier performance tuning via snapshot versions.

## 4) Core Components

### 4.1 Backend components

- `GalaxyBuildService`
  - pulls graph topology from Neo4j projection,
  - computes cluster assignment and 3D coordinates,
  - derives visual metrics (`influence_score`, `star_size`, `star_brightness`),
  - applies edge thinning and LOD buckets,
  - emits versioned snapshot artifact.

- `GalaxyQueryAPI` (FastAPI)
  - serves snapshot and metadata endpoints,
  - returns filter facets/counts,
  - returns per-node detail payload for drawer views.

### 4.2 Frontend components

- `GalaxyCanvas`
  - Three.js scene and camera controls (orbit/zoom/pan),
  - star, edge, and cluster-halo render layers,
  - hover/select state handling.

- `GalaxyFilterPanel`
  - filters by tags, guest, date range, source type,
  - result counts and active filter chips.

- `GalaxyDetailDrawer`
  - selected document metadata and summary,
  - "open document" navigation action,
  - related context fields.

- `GalaxyLegend`
  - communicates meaning of color/size/brightness and cluster grouping.

## 5) Data Contracts

### 5.1 Snapshot endpoint

`GET /api/v1/galaxy/snapshot`

Response shape (contract-level):

- `version`: string (snapshot version id)
- `generated_at`: iso8601 timestamp
- `schema_version`: integer (start at `1`; increment only on breaking response-shape changes)
- `bounds`: `{ x:[min,max], y:[min,max], z:[min,max] }`
- `nodes[]`:
  - `id`, `title`, `source_type`, `published_at`
  - `tags[]`, `guest_names[]`
  - `cluster_id`
  - `position`: `{ x, y, z }`
  - `influence_score`, `star_size`, `star_brightness`
- `edges[]`:
  - `source`, `target`, `weight`, `edge_tier`
- `clusters[]`:
  - `id`, `label`, `centroid`, `node_count`, `dominant_tags[]`
- `filter_facets`:
  - `tags`, `guests`, `date_min`, `date_max`, `source_types`

### 5.2 Node detail endpoint

`GET /api/v1/galaxy/node/{id}`

Returns compact detail payload used by drawer:

- `id`: string (`doc:{source_slug}`)
- `title`: string
- `source_type`: `newsletter|podcast`
- `published_at`: iso8601 timestamp
- `description`: string | null
- `summary`: string | null
- `tags[]`: string[]
- `guest_names[]`: string[]
- `related_document_ids[]`: string[]
- `reader_url`: string (canonical route to full document content)

### 5.3 Data mapping and ownership rules

- Node identity:
  - `nodes[].id` uses the canonical document id strategy from foundation docs (`doc:{source_slug}`).
  - `edges[].source` and `edges[].target` must reference valid `nodes[].id`.
- Source of truth:
  - topology and relation weights are derived from Neo4j projection,
  - descriptive enrichment fields (for detail drawer/reader entry) are sourced from canonical document metadata (Postgres-origin data).
- Edge mapping for `edges[]`:
  - P0 edge set is derived as document-to-document affinity based on shared `MENTIONS_CONCEPT` and `USES_FRAMEWORK` evidence.
  - each edge stores `weight` and `edge_tier` (`high|medium|low`) from deterministic thresholds.
  - guest/tag relationships remain filter facets and cluster labels, not separate rendered edge types in P0.
- Influence mapping:
  - `influence_score` is a deterministic normalized value (0-1) derived from weighted graph connectivity.
  - `star_brightness` and `star_size` are deterministic visual transforms of `influence_score`.
- Cluster mapping:
  - cluster assignment uses deterministic community detection over document affinity graph.
  - `clusters[].label` is generated by dominant tag composition with tie-breakers by weighted evidence.

## 6) Interaction Model

- Initial load: request snapshot, render immediately with progressive visual layers.
- Camera: smooth orbit/zoom with dampening; preserve state while filtering.
- Filter behavior:
  - client-side filtering over preloaded fields for responsiveness,
  - visual deemphasis (not hard remove) by default to keep spatial context.
- Selection:
  - hover highlight + tooltip,
  - click opens drawer and pins selected node.
  - drawer includes `Open full document` action routing to canonical reader view.
- Reset:
  - one-click reset to baseline camera and filter state.

## 7) Error Handling and Degradation

- Snapshot compatibility check:
  - frontend validates `schema_version`; incompatible payload is rejected with user-visible notice.
- Partial failure fallback:
  - backend should prefer returning `200` with `edges: []` when node payload is valid but edge derivation is unavailable,
  - frontend must render node-only constellation when `edges` are missing/empty/invalid and keep exploration functional.
- Detail fetch reliability:
  - timeout + retry-once policy; non-blocking error toast on failure.
- Density safeguards:
  - enforce max rendered edges and LOD tiers to avoid lockups.
- Snapshot/Neo4j availability behavior:
  - if galaxy snapshot is unavailable, show a feature-level unavailable/empty state with retry,
  - other non-galaxy app flows remain unaffected.

## 8) Performance and Quality Budgets

- First meaningful render target: under 5 seconds on a normal laptop (time to first stars visible after route load).
- Smooth interaction target: stable frame pacing during orbit/zoom on full dataset (target 30+ FPS on baseline hardware profile).
- Payload control:
  - snapshot compressed over network (gzip or brotli),
  - max compressed snapshot payload target: <= 1.5 MB for initial scene load,
  - detail endpoint lazy-loaded on selection.
- Memory and rendering:
  - batched draw strategy for stars/edges,
  - avoid per-node React reconciliation in hot loops.

## 9) Testing Strategy

### Backend

- unit:
  - deterministic layout generation and scoring,
  - schema validation for snapshot payload.
- integration:
  - Neo4j fixture -> build snapshot -> API contract assertions.

### Frontend

- unit:
  - filter state transitions,
  - legend/value mapping,
  - drawer state logic.
- interaction/e2e:
  - orbit/zoom behavior,
  - select node + open drawer,
  - filter + selection coexistence.
- performance checks:
  - verify full-638 snapshot remains responsive within budget.

## 10) Risks and Mitigations

- Over-dense edges reduce readability.
  - Mitigation: edge thinning, tiered rendering, optional edge toggle.
- Layout instability across rebuilds hurts user orientation.
  - Mitigation: deterministic seeding and snapshot versioning.
- Browser variance in 3D performance.
  - Mitigation: adaptive quality modes and conservative defaults.

## 11) Out of Scope for This Milestone

- Mobile-first bespoke 3D experience.
- Real-time graph mutation while user is exploring.
- Advanced social features (sharing snapshots, annotations).

## 12) Access Assumption

- P0 assumes read-only galaxy APIs are available to contest evaluators/visitors via app-level routing policy.
- If auth is introduced later, endpoint contracts stay unchanged and access control is handled at API gateway/app middleware layer.

## 13) Acceptance Criteria

- Full 638 documents are visible and explorable in 3D.
- Users can filter by tag/guest/date/source type.
- Clicking a star opens detail drawer with meaningful metadata.
- From the drawer, users can open the full canonical document reader route for that selected star.
- Scene remains usable under defined performance budgets.
- Visual shell follows brand palette/typography direction from brand kit.
