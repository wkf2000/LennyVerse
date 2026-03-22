# Knowledge Galaxy Runbook (Phase 4)

## Purpose

Operational notes for `VIZ-1 Knowledge Galaxy` covering snapshot generation behavior, degradation modes, and practical limits.

## Backend runtime toggles

- `GALAXY_ENABLE_NEO4J_SOURCE`
  - `1`: build snapshot from Neo4j topology source at request time when no artifact path is configured.
  - `0` (default): do not query Neo4j automatically.
- `GALAXY_SNAPSHOT_PATH`
  - Optional path to a snapshot artifact file. If present and valid, this is loaded first.
- `GALAXY_SNAPSHOT_DIR`
  - Directory for persisted generated snapshots.
  - Current behavior writes both `<version>.json` and `latest.json`.
- `GALAXY_MAX_EDGES`
  - Limits derived edge count for payload control. Default is `6000`.

## API behavior

- `GET /api/v1/galaxy/snapshot`
  - Returns contract payload (`schema_version=1`) with compatibility metadata.
  - Includes diagnostic headers:
    - `X-Galaxy-Snapshot-Source` (`artifact|neo4j|fallback`)
    - `X-Galaxy-Build-Ms` (when source-built)
    - `X-Galaxy-Payload-Bytes`
- `GET /api/v1/galaxy/node/{id}`
  - Returns drawer-ready detail payload with `reader_url`.
  - Returns `404` for missing node ids.

## Degradation and fallback

- If edge derivation fails during source build:
  - Snapshot still returns `200` with valid `nodes[]` and `edges: []`.
  - Node endpoint remains functional.
- If no valid artifact/source data exists:
  - Service returns fallback empty snapshot (feature-level degrade, not app-wide outage).

## Frontend integration notes

- Snapshot fetch rejects incompatible schema versions.
- Detail drawer fetch uses timeout and retry-once semantics.
- Filtering is client-side over preloaded snapshot fields to preserve navigation context.

## Known limits (current)

- Frontend bundle size warning appears due to initial Three.js payload size.
- No LOD controls or edge toggle UI yet (planned hardening).
- No automated perf trace collection in CI.

## Verification commands

- Backend:
  - `uv run pytest backend/tests/services/test_galaxy_build_service.py backend/tests/services/test_galaxy_query_service.py backend/tests/api/test_galaxy_endpoints.py backend/tests/integration/test_galaxy_snapshot_contract.py`
- Frontend:
  - `npm run test -- GalaxyCanvas`
  - `npm run test -- GalaxyFilterPanel`
  - `npm run test -- GalaxyDetailDrawer`
  - `npm run test -- galaxyApi`
  - `npm run build`
