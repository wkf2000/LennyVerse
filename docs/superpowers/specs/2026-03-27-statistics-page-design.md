# Design: Statistics Page — Topic Trends Over Time

Branch: main
Status: APPROVED
Date: 2026-03-27

## Problem Statement

Add a statistics page to LennyVerse that shows how topic popularity changes over time across the 638-piece corpus. The primary visualization is a line chart with quarterly time buckets on the x-axis and content occurrence counts on the y-axis, allowing users to see trends like AI becoming more popular after 2023. A row of summary stat cards provides high-level corpus context.

## Approach

**D3.js line chart (Approach A — chosen)**

Build the chart directly with D3, which is already installed for the knowledge graph. Zero new dependencies. Full control over styling to match the existing design system. The chart is straightforward (multi-line with axes, tooltips, legend) and doesn't warrant a dedicated charting library.

Alternatives considered:
- **Recharts**: declarative React charting, but adds ~45KB gzipped for one page.
- **Chart.js**: canvas-based, visually inconsistent with the SVG-based graph view.

## Backend API

### Endpoint

```
GET /api/stats/topic-trends
```

### Response Shape

```json
{
  "trends": [
    { "quarter": "2019-Q1", "topic": "ai", "count": 3 },
    { "quarter": "2019-Q1", "topic": "growth", "count": 7 }
  ],
  "summary": {
    "total_content": 638,
    "total_podcasts": 289,
    "total_newsletters": 349,
    "date_range": { "start": "2019-01-15", "end": "2026-02-28" },
    "top_topics": [
      { "topic": "growth", "count": 210 },
      { "topic": "product-management", "count": 185 }
    ]
  }
}
```

### Implementation

- Query the `content` table, unnest the `tags` array, group by tag and quarter (extracted from `published_at`).
- Summary stats from a second simple aggregation query.
- Both queries are read-only, no auth needed, cacheable.

## Frontend — Page Layout

### Navigation

Add "stats" view at `/stats` with a nav pill in the existing top-right nav bar. Updated order: `["graph", "explore", "generate", "stats", "about"]`.

### Layout (top to bottom)

1. **Header** — same pattern as other views: "LennyVerse" label + title "Corpus statistics at a glance" + subtitle.
2. **Summary cards row** — 4 compact cards: Total Content, Podcasts, Newsletters, Date Range. Rounded white cards with indigo accents matching the existing filter bar aesthetic.
3. **Topic selector** — row of pill toggles (same pattern as node type toggles on graph page). Pre-selects top 5 topics by count. Click to add/remove. Each pill has a colored dot matching its line color.
4. **Line chart** — full-width, ~500px tall. X-axis: quarters. Y-axis: content count. One colored line per selected topic. Smooth curves, subtle grid lines, light background.

## Interactions & Edge Cases

- **Hover tooltip**: vertical crosshair snaps to nearest quarter. Tooltip card shows quarter label and all visible topics with counts, sorted descending. Follows cursor horizontally.
- **Empty state**: "Select at least one topic to see trends." centered in chart area.
- **Loading state**: "Loading statistics..." centered in chart area.
- **Error state**: red banner matching graph page pattern.
- **Zero-count quarters**: plotted as 0 (continuous line, no gaps).
- **NULL `published_at`**: trend query uses `WHERE published_at IS NOT NULL` to exclude undated content.
- **Line colors**: fixed 17-color palette defined in a shared constant, used by both pill dots and chart lines. Each topic always gets the same color regardless of selection order.
- **`top_topics` in response**: returns all 17 topics sorted by count. Frontend uses this for both summary cards (show top N) and the pill selector (render all).

## File Structure

### Backend (new files)

- `backend/src/backend_api/stats_repository.py` — SQL queries for trend aggregation and summary stats.
- `backend/src/backend_api/stats_service.py` — business logic layer (thin, calls repository).
- `backend/src/backend_api/stats_schemas.py` — Pydantic response models.
- Route handler registered in the existing FastAPI app.

### Frontend (new files)

- `frontend/src/views/StatsPage.tsx` — full stats view (summary cards + topic selector + D3 chart).
- `frontend/src/api/statsApi.ts` — fetch function for `/api/stats/topic-trends`.

### Frontend (modified)

- `frontend/src/App.tsx` — add "stats" to VIEWS, NAV_VIEWS, VIEW_PATHS, VIEW_LABELS; import and render StatsPage.

## Success Criteria

1. Stats page loads and displays summary cards with correct aggregate numbers.
2. Line chart renders quarterly topic trends for the pre-selected top 5 topics.
3. Users can add/remove topics and the chart updates immediately.
4. Hover tooltip shows per-topic counts for the hovered quarter.
5. Page matches the existing visual style (indigo accents, white cards, slate text).
