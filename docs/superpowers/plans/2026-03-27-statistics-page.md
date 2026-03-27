# Statistics Page Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a statistics page with summary stat cards and a D3 line chart showing topic occurrence trends over quarterly time buckets.

**Architecture:** New `GET /api/stats/topic-trends` endpoint queries the `content` table, aggregates by tag and quarter, and returns trends + summary. Frontend renders a new `/stats` view with summary cards, topic pill selector, and a D3 SVG line chart.

**Tech Stack:** Python/FastAPI backend (psycopg, Pydantic), React/TypeScript frontend, D3.js for charting, Tailwind CSS for layout.

**Spec:** `docs/superpowers/specs/2026-03-27-statistics-page-design.md`

---

## File Structure

### Backend (new files)
- `backend/src/backend_api/stats_schemas.py` — Pydantic response models for topic trends and summary
- `backend/src/backend_api/stats_repository.py` — SQL queries for trend aggregation and summary stats
- `backend/src/backend_api/stats_service.py` — Thin service layer calling repository

### Backend (modified files)
- `backend/src/backend_api/main.py` — Register `GET /api/stats/topic-trends` route + DI wiring

### Frontend (new files)
- `frontend/src/api/statsApi.ts` — Fetch function for the stats endpoint
- `frontend/src/views/StatsPage.tsx` — Full stats view (cards + selector + D3 chart)

### Frontend (modified files)
- `frontend/src/App.tsx` — Add "stats" to VIEWS/NAV_VIEWS/VIEW_PATHS/VIEW_LABELS, import StatsPage

### Test files (new)
- `tests/backend_api/test_stats_api.py` — API endpoint tests with fake service
- `tests/backend_api/test_stats_service.py` — Service layer unit tests with fake repository

---

## Chunk 1: Backend

### Task 1: Stats Pydantic Schemas

**Files:**
- Create: `backend/src/backend_api/stats_schemas.py`

- [ ] **Step 1: Create the schema file**

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class TopicTrendItem(BaseModel):
    quarter: str
    topic: str
    count: int


class TopicCount(BaseModel):
    topic: str
    count: int


class DateRange(BaseModel):
    start: str
    end: str


class StatsSummary(BaseModel):
    total_content: int
    total_podcasts: int
    total_newsletters: int
    date_range: DateRange
    top_topics: list[TopicCount] = Field(default_factory=list)


class TopicTrendsResponse(BaseModel):
    trends: list[TopicTrendItem] = Field(default_factory=list)
    summary: StatsSummary
```

- [ ] **Step 2: Commit**

```bash
git add backend/src/backend_api/stats_schemas.py
git commit -m "feat(backend): add stats Pydantic schemas"
```

---

### Task 2: Stats Repository

**Files:**
- Create: `backend/src/backend_api/stats_repository.py`

- [ ] **Step 1: Write the failing test**

Create `tests/backend_api/test_stats_service.py`:

```python
from __future__ import annotations

from backend_api.stats_repository import StatsRepository, TrendRow, SummaryRow


class FakeStatsRepository(StatsRepository):
    """In-memory fake for unit testing the service layer."""

    def __init__(
        self,
        trend_rows: list[TrendRow] | None = None,
        summary_row: SummaryRow | None = None,
    ) -> None:
        self._trend_rows = trend_rows or []
        self._summary_row = summary_row or SummaryRow(
            total_content=0,
            total_podcasts=0,
            total_newsletters=0,
            min_date=None,
            max_date=None,
        )

    def fetch_topic_trends(self) -> list[TrendRow]:
        return self._trend_rows

    def fetch_summary(self) -> SummaryRow:
        return self._summary_row


def test_fake_repository_returns_empty_trends() -> None:
    repo = FakeStatsRepository()
    assert repo.fetch_topic_trends() == []


def test_fake_repository_returns_summary() -> None:
    repo = FakeStatsRepository()
    summary = repo.fetch_summary()
    assert summary.total_content == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run python -m pytest tests/backend_api/test_stats_service.py -v
```

Expected: FAIL (import errors — StatsRepository doesn't exist yet)

- [ ] **Step 3: Create the repository**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg
from psycopg.rows import dict_row


@dataclass(slots=True)
class TrendRow:
    quarter: str
    topic: str
    count: int


@dataclass(slots=True)
class SummaryRow:
    total_content: int
    total_podcasts: int
    total_newsletters: int
    min_date: date | None
    max_date: date | None


class StatsRepository:
    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url

    def _connect(self) -> psycopg.Connection:
        if not self._db_url:
            raise ValueError("db_url is required")
        return psycopg.connect(self._db_url, prepare_threshold=None)

    def fetch_topic_trends(self) -> list[TrendRow]:
        query = """
            SELECT
                EXTRACT(YEAR FROM c.published_at)::int
                    || '-Q' || EXTRACT(QUARTER FROM c.published_at)::int AS quarter_label,
                t.tag AS topic,
                COUNT(*)::int AS cnt
            FROM content c, unnest(c.tags) AS t(tag)
            WHERE c.published_at IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM c.published_at),
                     EXTRACT(QUARTER FROM c.published_at),
                     t.tag
            ORDER BY EXTRACT(YEAR FROM c.published_at),
                     EXTRACT(QUARTER FROM c.published_at),
                     t.tag
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                rows = cur.fetchall()

        return [
            TrendRow(
                quarter=row["quarter_label"],
                topic=row["topic"],
                count=row["cnt"],
            )
            for row in rows
        ]

    def fetch_summary(self) -> SummaryRow:
        query = """
            SELECT
                COUNT(*)::int AS total_content,
                COUNT(*) FILTER (WHERE type = 'podcast')::int AS total_podcasts,
                COUNT(*) FILTER (WHERE type = 'newsletter')::int AS total_newsletters,
                MIN(published_at) AS min_date,
                MAX(published_at) AS max_date
            FROM content
        """
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(query)
                row = cur.fetchone()

        if not row:
            return SummaryRow(
                total_content=0,
                total_podcasts=0,
                total_newsletters=0,
                min_date=None,
                max_date=None,
            )

        return SummaryRow(
            total_content=row["total_content"],
            total_podcasts=row["total_podcasts"],
            total_newsletters=row["total_newsletters"],
            min_date=row.get("min_date"),
            max_date=row.get("max_date"),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/backend_api/test_stats_service.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/backend_api/stats_repository.py tests/backend_api/test_stats_service.py
git commit -m "feat(backend): add stats repository with trend and summary queries"
```

---

### Task 3: Stats Service

**Files:**
- Create: `backend/src/backend_api/stats_service.py`
- Modify: `tests/backend_api/test_stats_service.py`

- [ ] **Step 1: Add service tests to the existing test file**

Append to `tests/backend_api/test_stats_service.py`:

```python
from datetime import date

from backend_api.stats_service import StatsService
from backend_api.stats_schemas import TopicTrendsResponse


def test_service_returns_topic_trends_response() -> None:
    repo = FakeStatsRepository(
        trend_rows=[
            TrendRow(quarter="2023-Q1", topic="ai", count=5),
            TrendRow(quarter="2023-Q1", topic="growth", count=3),
            TrendRow(quarter="2023-Q2", topic="ai", count=8),
        ],
        summary_row=SummaryRow(
            total_content=638,
            total_podcasts=289,
            total_newsletters=349,
            min_date=date(2019, 1, 15),
            max_date=date(2026, 2, 28),
        ),
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    assert isinstance(result, TopicTrendsResponse)
    assert len(result.trends) == 3
    assert result.trends[0].quarter == "2023-Q1"
    assert result.summary.total_content == 638
    assert result.summary.total_podcasts == 289
    assert result.summary.total_newsletters == 349
    assert result.summary.date_range.start == "2019-01-15"
    assert result.summary.date_range.end == "2026-02-28"
    assert len(result.summary.top_topics) > 0


def test_service_handles_none_dates() -> None:
    repo = FakeStatsRepository(
        summary_row=SummaryRow(
            total_content=0,
            total_podcasts=0,
            total_newsletters=0,
            min_date=None,
            max_date=None,
        ),
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    assert result.summary.date_range.start == ""
    assert result.summary.date_range.end == ""


def test_service_computes_top_topics_sorted() -> None:
    repo = FakeStatsRepository(
        trend_rows=[
            TrendRow(quarter="2023-Q1", topic="ai", count=5),
            TrendRow(quarter="2023-Q2", topic="ai", count=8),
            TrendRow(quarter="2023-Q1", topic="growth", count=3),
            TrendRow(quarter="2023-Q1", topic="b2b", count=1),
        ],
    )
    service = StatsService(repo)
    result = service.get_topic_trends()

    topics = result.summary.top_topics
    assert topics[0].topic == "ai"
    assert topics[0].count == 13
    assert topics[1].topic == "growth"
    assert topics[1].count == 3
    assert topics[2].topic == "b2b"
    assert topics[2].count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest tests/backend_api/test_stats_service.py -v
```

Expected: FAIL (StatsService doesn't exist)

- [ ] **Step 3: Create the service**

```python
from __future__ import annotations

from collections import defaultdict

from backend_api.stats_repository import StatsRepository
from backend_api.stats_schemas import (
    DateRange,
    StatsSummary,
    TopicCount,
    TopicTrendItem,
    TopicTrendsResponse,
)


class StatsService:
    def __init__(self, repository: StatsRepository) -> None:
        self._repository = repository

    def get_topic_trends(self) -> TopicTrendsResponse:
        trend_rows = self._repository.fetch_topic_trends()
        summary_row = self._repository.fetch_summary()

        trends = [
            TopicTrendItem(quarter=row.quarter, topic=row.topic, count=row.count)
            for row in trend_rows
        ]

        topic_totals: dict[str, int] = defaultdict(int)
        for row in trend_rows:
            topic_totals[row.topic] += row.count

        top_topics = sorted(
            [TopicCount(topic=t, count=c) for t, c in topic_totals.items()],
            key=lambda x: x.count,
            reverse=True,
        )

        date_range = DateRange(
            start=str(summary_row.min_date) if summary_row.min_date else "",
            end=str(summary_row.max_date) if summary_row.max_date else "",
        )

        summary = StatsSummary(
            total_content=summary_row.total_content,
            total_podcasts=summary_row.total_podcasts,
            total_newsletters=summary_row.total_newsletters,
            date_range=date_range,
            top_topics=top_topics,
        )

        return TopicTrendsResponse(trends=trends, summary=summary)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/backend_api/test_stats_service.py -v
```

Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/src/backend_api/stats_service.py tests/backend_api/test_stats_service.py
git commit -m "feat(backend): add stats service with top topics computation"
```

---

### Task 4: API Route + Endpoint Tests

**Files:**
- Modify: `backend/src/backend_api/main.py`
- Create: `tests/backend_api/test_stats_api.py`

- [ ] **Step 1: Write the failing endpoint test**

Create `tests/backend_api/test_stats_api.py`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from backend_api.main import app, get_stats_service
from backend_api.stats_schemas import (
    DateRange,
    StatsSummary,
    TopicCount,
    TopicTrendItem,
    TopicTrendsResponse,
)


class _FakeStatsService:
    def get_topic_trends(self) -> TopicTrendsResponse:
        return TopicTrendsResponse(
            trends=[
                TopicTrendItem(quarter="2023-Q1", topic="ai", count=5),
                TopicTrendItem(quarter="2023-Q1", topic="growth", count=3),
            ],
            summary=StatsSummary(
                total_content=100,
                total_podcasts=50,
                total_newsletters=50,
                date_range=DateRange(start="2019-01-15", end="2025-12-31"),
                top_topics=[
                    TopicCount(topic="ai", count=5),
                    TopicCount(topic="growth", count=3),
                ],
            ),
        )


def test_stats_topic_trends_returns_200() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/topic-trends")
        assert response.status_code == 200
        payload = response.json()
        assert "trends" in payload
        assert "summary" in payload
        assert len(payload["trends"]) == 2
        assert payload["summary"]["total_content"] == 100
        assert payload["summary"]["total_podcasts"] == 50
        assert len(payload["summary"]["top_topics"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_stats_topic_trends_trend_shape() -> None:
    app.dependency_overrides[get_stats_service] = lambda: _FakeStatsService()
    client = TestClient(app)
    try:
        response = client.get("/api/stats/topic-trends")
        trend = response.json()["trends"][0]
        assert "quarter" in trend
        assert "topic" in trend
        assert "count" in trend
    finally:
        app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run python -m pytest tests/backend_api/test_stats_api.py -v
```

Expected: FAIL (get_stats_service doesn't exist in main.py)

- [ ] **Step 3: Register the route in main.py**

Add these imports near the top of `main.py` (after existing imports):

```python
from backend_api.stats_repository import StatsRepository
from backend_api.stats_schemas import TopicTrendsResponse
from backend_api.stats_service import StatsService
```

Add the DI wiring (after the existing `get_generate_service` function):

```python
def get_stats_repository(
    app_settings: Annotated[Settings, Depends(get_settings)],
) -> StatsRepository:
    return StatsRepository(app_settings.require_db_url())


def get_stats_service(
    repository: Annotated[StatsRepository, Depends(get_stats_repository)],
) -> StatsService:
    return StatsService(repository)
```

Add the route (after the `post_generate_execute` route, before the SPA serving section):

```python
@app.get("/api/stats/topic-trends", response_model=TopicTrendsResponse)
def get_topic_trends(
    service: Annotated[StatsService, Depends(get_stats_service)],
) -> TopicTrendsResponse:
    return service.get_topic_trends()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run python -m pytest tests/backend_api/test_stats_api.py -v
```

Expected: PASS

- [ ] **Step 5: Run all backend tests to check for regressions**

```bash
uv run python -m pytest tests/ -v
```

Expected: All existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/backend_api/main.py tests/backend_api/test_stats_api.py
git commit -m "feat(backend): add GET /api/stats/topic-trends endpoint"
```

---

## Chunk 2: Frontend

### Task 5: Stats API Client

**Files:**
- Create: `frontend/src/api/statsApi.ts`

- [ ] **Step 1: Create the API fetch function**

```typescript
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export interface TopicTrendItem {
  quarter: string;
  topic: string;
  count: number;
}

export interface TopicCount {
  topic: string;
  count: number;
}

export interface DateRange {
  start: string;
  end: string;
}

export interface StatsSummary {
  total_content: number;
  total_podcasts: number;
  total_newsletters: number;
  date_range: DateRange;
  top_topics: TopicCount[];
}

export interface TopicTrendsResponse {
  trends: TopicTrendItem[];
  summary: StatsSummary;
}

export async function fetchTopicTrends(): Promise<TopicTrendsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/stats/topic-trends`);
  if (!response.ok) {
    throw new Error(`Failed to load statistics (${response.status})`);
  }
  return (await response.json()) as TopicTrendsResponse;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/statsApi.ts
git commit -m "feat(frontend): add stats API client"
```

---

### Task 6: Stats Page View

**Files:**
- Create: `frontend/src/views/StatsPage.tsx`

This is the largest task. The file contains: summary cards, topic pill selector, and a D3 SVG line chart with hover tooltip.

- [ ] **Step 1: Create the StatsPage component**

Create `frontend/src/views/StatsPage.tsx` with the following structure:

1. **TOPIC_COLORS constant** — a `Record<string, string>` mapping all 17 tags to fixed hex colors. Use distinguishable colors on a light background:
   - ai: `#6366f1`, analytics: `#f59e0b`, b2b: `#10b981`, b2c: `#ef4444`, career: `#8b5cf6`, design: `#ec4899`, engineering: `#14b8a6`, go-to-market: `#f97316`, growth: `#22c55e`, leadership: `#3b82f6`, newsletter: `#a855f7`, organization: `#78716c`, podcast: `#06b6d4`, pricing: `#eab308`, product-management: `#0ea5e9`, startups: `#e11d48`, strategy: `#64748b`

2. **StatsPage component** using `useState` and `useEffect`:
   - State: `data` (TopicTrendsResponse | null), `loading` (boolean), `error` (string | undefined), `selectedTopics` (Set<string>)
   - On mount: fetch data, then set `selectedTopics` to the top 5 from `data.summary.top_topics`
   - Render order: header, summary cards row, topic pill selector, chart (or loading/error/empty states)

3. **Summary cards** — a `grid grid-cols-2 md:grid-cols-4` of white rounded cards with:
   - Total Content (total_content)
   - Podcasts (total_podcasts)
   - Newsletters (total_newsletters)
   - Date Range (formatted from date_range.start to date_range.end, showing just years)

4. **Topic pill selector** — flex-wrap row of buttons, one per topic from `data.summary.top_topics`. Each pill shows a small colored dot (from TOPIC_COLORS) + the topic label. Active pills get `border-indigo-300 bg-indigo-100` styling (match graph page node type toggles). Click toggles topic in/out of `selectedTopics`.

5. **D3 line chart** using `useRef` for the SVG container and `useEffect` to render/update:
   - Dimensions: full parent width (use ResizeObserver or fixed width), 500px height, margins {top: 20, right: 30, bottom: 50, left: 60}
   - Transform `data.trends` into per-topic series: `Map<string, {quarter: string, count: number}[]>`. Fill missing quarters with count=0 for continuity.
   - X scale: `d3.scalePoint()` with all unique quarters sorted chronologically as domain
   - Y scale: `d3.scaleLinear()` from 0 to max count across selected topics
   - Axes: bottom x-axis (rotate labels -45deg if needed), left y-axis
   - Lines: `d3.line()` with `d3.curveMonotoneX` for smooth curves, colored by TOPIC_COLORS
   - Grid: light horizontal grid lines (`stroke: #e2e8f0`, `stroke-opacity: 0.5`)
   - Tooltip: invisible vertical line + floating div. On `mousemove` over the chart area, find the nearest quarter, show a tooltip card listing all visible topics + counts for that quarter, sorted descending.
   - Clear and re-render on `selectedTopics` or `data` change.

6. **Empty state** (no topics selected): centered text "Select at least one topic to see trends."

7. **Error state**: red border banner matching graph page pattern.

8. **Loading state**: centered "Loading statistics..." text.

- [ ] **Step 2: Verify the component renders without errors**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/StatsPage.tsx
git commit -m "feat(frontend): add StatsPage with summary cards and D3 line chart"
```

---

### Task 7: Wire Stats Page into App Router

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add the stats view to App.tsx**

Add import at the top (near other view imports):

```typescript
import StatsPage from "./views/StatsPage";
```

Update the view constants — insert `"stats"` before `"about"`:

```typescript
const VIEWS = ["graph", "explore", "generate", "stats", "about"] as const;
const NAV_VIEWS = ["graph", "explore", "generate", "stats", "about"] as const;
```

Add to VIEW_PATHS:

```typescript
stats: "/stats",
```

Add to VIEW_LABELS:

```typescript
stats: "stats",
```

Add the rendering branch in the JSX (before the `activeView === "about"` block):

```tsx
) : activeView === "stats" ? (
  <section className="mx-auto max-w-7xl px-4 pb-8 pt-24 sm:px-6 lg:px-8">
    <StatsPage />
  </section>
```

- [ ] **Step 2: Verify the build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm run test
```

Expected: All existing tests pass. (The App.test.tsx may need updating if it asserts on view count or nav items — check and fix if needed.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): wire StatsPage into app router at /stats"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run all backend tests**

```bash
uv run python -m pytest tests/ -v
```

Expected: All pass.

- [ ] **Step 2: Run frontend build and tests**

```bash
cd frontend && npm run build && npm run test
```

Expected: Build succeeds, all tests pass.

- [ ] **Step 3: Verify the quarter label format**

Double-check the SQL quarter format. The query produces `Q1-2023` style labels. Ensure the frontend sorts these chronologically. If the SQL `ORDER BY` is correct (year then quarter), the frontend receives them pre-sorted.

- [ ] **Step 4: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address final verification issues"
```
