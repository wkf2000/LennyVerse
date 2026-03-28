# Content Summarization CLI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CLI tool to the data-pipeline that uses a configurable LLM to generate 2-3 sentence summaries for each content item and stores them in the `content` table in Supabase.

**Architecture:** Sequential single-threaded script following the existing ingest pattern. New `SummarizerClient` wraps the OpenAI SDK with separate `SUMMARIZE_*` env vars. DB gets two new methods for fetching unsummarized rows and writing summaries back. A SQL migration adds the `summary` column.

**Tech Stack:** Python, OpenAI SDK, psycopg, pydantic-settings, tenacity, argparse

**Spec:** `docs/superpowers/specs/2026-03-28-content-summarization-cli-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `data-pipeline/sql/migrations/002_add_content_summary.sql` | Create | SQL migration adding `summary` column |
| `data-pipeline/src/data_pipeline/config.py` | Modify | Add `SUMMARIZE_*` fields + `require_summarize_config()` |
| `data-pipeline/src/data_pipeline/db.py` | Modify | Add `fetch_unsummarized_content()` + `update_summary()` |
| `data-pipeline/src/data_pipeline/summarizer.py` | Create | `SummarizerClient` wrapping OpenAI chat completions |
| `data-pipeline/src/data_pipeline/scripts/summarize.py` | Create | CLI entry point |
| `tests/test_summarizer.py` | Create | Unit tests for `SummarizerClient` |
| `tests/test_summarize_script.py` | Create | Unit tests for CLI script logic |
| `.env.example` | Modify | Add `SUMMARIZE_*` vars |
| `Makefile` | Modify | Add `summarize` target |

---

## Chunk 1: Database and Configuration

### Task 1: SQL Migration

**Files:**
- Create: `data-pipeline/sql/migrations/002_add_content_summary.sql`

- [ ] **Step 1: Create migration file**

```sql
ALTER TABLE content ADD COLUMN IF NOT EXISTS summary TEXT;
```

- [ ] **Step 2: Commit**

```bash
git add data-pipeline/sql/migrations/002_add_content_summary.sql
git commit -m "feat(data-pipeline): add migration for content.summary column"
```

---

### Task 2: Config — Add SUMMARIZE_* fields

**Files:**
- Modify: `data-pipeline/src/data_pipeline/config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_summarize_config.py`:

```python
from data_pipeline.config import Settings


def test_summarize_fields_default_to_none() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    assert settings.summarize_api_base is None
    assert settings.summarize_api_key is None
    assert settings.summarize_model is None
    assert settings.summarize_max_chars == 8000


def test_summarize_fields_from_env(monkeypatch) -> None:
    monkeypatch.setenv("SUMMARIZE_API_BASE", "https://api.example.com/v1")
    monkeypatch.setenv("SUMMARIZE_API_KEY", "sk-test")
    monkeypatch.setenv("SUMMARIZE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("SUMMARIZE_MAX_CHARS", "4000")
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    assert settings.summarize_api_base == "https://api.example.com/v1"
    assert settings.summarize_api_key == "sk-test"
    assert settings.summarize_model == "gpt-4o-mini"
    assert settings.summarize_max_chars == 4000


def test_require_summarize_config_raises_when_missing() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
    )
    import pytest
    with pytest.raises(ValueError, match="SUMMARIZE_API_BASE.*SUMMARIZE_API_KEY.*SUMMARIZE_MODEL"):
        settings.require_summarize_config()


def test_require_summarize_config_returns_tuple() -> None:
    settings = Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
        SUMMARIZE_API_BASE="https://api.example.com/v1",
        SUMMARIZE_API_KEY="sk-test",
        SUMMARIZE_MODEL="gpt-4o-mini",
    )
    base, key, model = settings.require_summarize_config()
    assert base == "https://api.example.com/v1"
    assert key == "sk-test"
    assert model == "gpt-4o-mini"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_config.py -v`
Expected: FAIL (fields don't exist yet)

- [ ] **Step 3: Add SUMMARIZE_* fields to Settings**

In `data-pipeline/src/data_pipeline/config.py`, add these fields to the `Settings` class after the existing `ingest_chunk_overlap_chars` field:

```python
    summarize_api_base: str | None = Field(default=None, alias="SUMMARIZE_API_BASE")
    summarize_api_key: str | None = Field(default=None, alias="SUMMARIZE_API_KEY")
    summarize_model: str | None = Field(default=None, alias="SUMMARIZE_MODEL")
    summarize_max_chars: int = Field(default=8000, alias="SUMMARIZE_MAX_CHARS")
```

Add this method after the existing `require_db_url()`:

```python
    def require_summarize_config(self) -> tuple[str, str, str]:
        missing = []
        if not self.summarize_api_base:
            missing.append("SUMMARIZE_API_BASE")
        if not self.summarize_api_key:
            missing.append("SUMMARIZE_API_KEY")
        if not self.summarize_model:
            missing.append("SUMMARIZE_MODEL")
        if missing:
            raise ValueError(f"{', '.join(missing)} required for summarization.")
        return self.summarize_api_base, self.summarize_api_key, self.summarize_model  # type: ignore[return-value]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_config.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add data-pipeline/src/data_pipeline/config.py tests/test_summarize_config.py
git commit -m "feat(data-pipeline): add SUMMARIZE_* config fields to Settings"
```

---

### Task 3: DB Methods — fetch_unsummarized_content and update_summary

**Files:**
- Modify: `data-pipeline/src/data_pipeline/db.py`
- Create: `tests/test_summarize_db.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_summarize_db.py`:

```python
from unittest.mock import MagicMock, patch, call

from data_pipeline.db import Database


def _make_db() -> Database:
    return Database("postgresql://fake/db")


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_fetch_unsummarized_content_default(monkeypatch) -> None:
    db = _make_db()
    rows = [{"id": "abc", "filename": "newsletters/abc.md", "title": "ABC"}]
    fake_cur = FakeCursor(rows=rows)
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    result = db.fetch_unsummarized_content()
    assert result == rows
    sql = fake_cur.executed[0][0]
    assert "summary IS NULL" in sql


def test_fetch_unsummarized_content_force(monkeypatch) -> None:
    db = _make_db()
    rows = [{"id": "abc", "filename": "newsletters/abc.md", "title": "ABC"}]
    fake_cur = FakeCursor(rows=rows)
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    result = db.fetch_unsummarized_content(force=True)
    assert result == rows
    sql = fake_cur.executed[0][0]
    assert "summary IS NULL" not in sql


def test_update_summary(monkeypatch) -> None:
    db = _make_db()
    fake_cur = FakeCursor()
    fake_conn = FakeConnection(fake_cur)
    monkeypatch.setattr(db, "_connect", lambda: fake_conn)

    db.update_summary("abc", "This is a summary.")
    assert len(fake_cur.executed) == 1
    sql, params = fake_cur.executed[0]
    assert "UPDATE content" in sql
    assert params["summary"] == "This is a summary."
    assert params["id"] == "abc"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_db.py -v`
Expected: FAIL (methods don't exist yet)

- [ ] **Step 3: Add methods to Database class**

In `data-pipeline/src/data_pipeline/db.py`, add these methods to the `Database` class after the `sample_similarity` method:

```python
    def fetch_unsummarized_content(self, force: bool = False) -> list[dict]:
        if force:
            sql = "SELECT id, filename, title FROM content ORDER BY id"
        else:
            sql = "SELECT id, filename, title FROM content WHERE summary IS NULL ORDER BY id"
        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchall()

    def update_summary(self, content_id: str, summary: str) -> None:
        sql = "UPDATE content SET summary = %(summary)s, updated_at = now() WHERE id = %(id)s"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"summary": summary, "id": content_id})
            conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_db.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add data-pipeline/src/data_pipeline/db.py tests/test_summarize_db.py
git commit -m "feat(data-pipeline): add fetch_unsummarized_content and update_summary to Database"
```

---

## Chunk 2: SummarizerClient and CLI Script

### Task 4: SummarizerClient

**Files:**
- Create: `data-pipeline/src/data_pipeline/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_summarizer.py`:

```python
from unittest.mock import MagicMock, patch

from data_pipeline.config import Settings
from data_pipeline.summarizer import SummarizerClient

SYSTEM_PROMPT = "Summarize the following content in 2-3 concise sentences. Focus on the key topics, insights, and takeaways."


def _make_settings() -> Settings:
    return Settings(
        SUPABASE_DB_URL="postgresql://localhost/test",
        DATASET_ROOT_DIR="/tmp/fake",
        SUMMARIZE_API_BASE="https://api.example.com/v1",
        SUMMARIZE_API_KEY="sk-test",
        SUMMARIZE_MODEL="gpt-4o-mini",
        SUMMARIZE_MAX_CHARS=100,
    )


def test_summarize_calls_openai_and_returns_text() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a summary."
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("Some long text about product management.")

        assert result == "This is a summary."
        mock_openai_cls.assert_called_once_with(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
        )
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "gpt-4o-mini"
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == SYSTEM_PROMPT
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Some long text about product management."


def test_summarize_strips_whitespace() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "  Summary with whitespace.  \n"
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("text")
        assert result == "Summary with whitespace."


def test_summarize_handles_none_content() -> None:
    settings = _make_settings()
    with patch("data_pipeline.summarizer.OpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        client = SummarizerClient(settings)
        result = client.summarize("text")
        assert result == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarizer.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create SummarizerClient**

Create `data-pipeline/src/data_pipeline/summarizer.py`:

```python
from __future__ import annotations

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from data_pipeline.config import Settings

SYSTEM_PROMPT = (
    "Summarize the following content in 2-3 concise sentences. "
    "Focus on the key topics, insights, and takeaways."
)


class SummarizerClient:
    def __init__(self, settings: Settings) -> None:
        base, key, model = settings.require_summarize_config()
        self._client = OpenAI(base_url=base, api_key=key)
        self._model = model

    @retry(wait=wait_exponential(multiplier=1, min=1, max=15), stop=stop_after_attempt(3), reraise=True)
    def summarize(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarizer.py -v`
Expected: 3 PASSED

- [ ] **Step 5: Commit**

```bash
git add data-pipeline/src/data_pipeline/summarizer.py tests/test_summarizer.py
git commit -m "feat(data-pipeline): add SummarizerClient with OpenAI + tenacity retry"
```

---

### Task 5: CLI Script

**Files:**
- Create: `data-pipeline/src/data_pipeline/scripts/summarize.py`
- Create: `tests/test_summarize_script.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_summarize_script.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _write_sample_md(path: Path, title: str = "Sample", body: str = "Hello world.") -> None:
    path.write_text(
        f'---\ntitle: "{title}"\ntype: "newsletter"\ndate: "2026-01-01"\ntags: []\nword_count: 10\n---\n{body}\n',
        encoding="utf-8",
    )


def test_summarize_dry_run_prints_count(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)

    rows = [
        {"id": "a", "filename": "newsletters/a.md", "title": "A"},
        {"id": "b", "filename": "newsletters/b.md", "title": "B"},
    ]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient"):
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize", "--dry-run"]
        main()

    captured = capsys.readouterr()
    assert "2" in captured.out
    mock_db.update_summary.assert_not_called()


def test_summarize_skips_empty_body(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    _write_sample_md(newsletters / "a.md", title="A", body="")

    rows = [{"id": "a", "filename": "newsletters/a.md", "title": "A"}]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient") as MockSummarizer:
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        mock_summarizer = MagicMock()
        MockSummarizer.return_value = mock_summarizer

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize"]
        main()

    mock_summarizer.summarize.assert_not_called()
    mock_db.update_summary.assert_not_called()
    assert "skip" in capsys.readouterr().out.lower()


def test_summarize_processes_and_writes(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    _write_sample_md(newsletters / "a.md", title="A", body="Long content about growth.")

    rows = [{"id": "a", "filename": "newsletters/a.md", "title": "A"}]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient") as MockSummarizer:
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "A concise summary."
        MockSummarizer.return_value = mock_summarizer

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize"]
        main()

    mock_summarizer.summarize.assert_called_once()
    mock_db.update_summary.assert_called_once_with("a", "A concise summary.")
    assert "1/1" in capsys.readouterr().out


def test_summarize_continues_on_error(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    _write_sample_md(newsletters / "a.md", title="A", body="Content A.")
    _write_sample_md(newsletters / "b.md", title="B", body="Content B.")

    rows = [
        {"id": "a", "filename": "newsletters/a.md", "title": "A"},
        {"id": "b", "filename": "newsletters/b.md", "title": "B"},
    ]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient") as MockSummarizer:
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.side_effect = [RuntimeError("LLM down"), "Summary B."]
        MockSummarizer.return_value = mock_summarizer

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize"]
        main()

    assert mock_summarizer.summarize.call_count == 2
    mock_db.update_summary.assert_called_once_with("b", "Summary B.")
    captured = capsys.readouterr().out
    assert "warn" in captured.lower()


def test_summarize_force_flag_passes_to_db(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)

    rows = []

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient"):
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize", "--force", "--dry-run"]
        main()

    mock_db.fetch_unsummarized_content.assert_called_once_with(force=True)


def test_summarize_continues_on_missing_file(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    _write_sample_md(newsletters / "b.md", title="B", body="Content B.")

    rows = [
        {"id": "a", "filename": "newsletters/missing.md", "title": "Missing"},
        {"id": "b", "filename": "newsletters/b.md", "title": "B"},
    ]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient") as MockSummarizer:
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "Summary B."
        MockSummarizer.return_value = mock_summarizer

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize"]
        main()

    mock_db.update_summary.assert_called_once_with("b", "Summary B.")
    captured = capsys.readouterr().out
    assert "warn" in captured.lower()


def test_summarize_limit_flag(tmp_path, capsys) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    _write_sample_md(newsletters / "a.md", title="A", body="Content A.")
    _write_sample_md(newsletters / "b.md", title="B", body="Content B.")

    rows = [
        {"id": "a", "filename": "newsletters/a.md", "title": "A"},
        {"id": "b", "filename": "newsletters/b.md", "title": "B"},
    ]

    with patch("data_pipeline.scripts.summarize.Settings") as MockSettings, \
         patch("data_pipeline.scripts.summarize.Database") as MockDB, \
         patch("data_pipeline.scripts.summarize.SummarizerClient") as MockSummarizer:
        mock_settings = MagicMock()
        mock_settings.require_db_url.return_value = "postgresql://fake/db"
        mock_settings.data_root = dataset
        mock_settings.summarize_max_chars = 8000
        MockSettings.return_value = mock_settings

        mock_db = MagicMock()
        mock_db.fetch_unsummarized_content.return_value = rows
        MockDB.return_value = mock_db

        mock_summarizer = MagicMock()
        mock_summarizer.summarize.return_value = "Summary."
        MockSummarizer.return_value = mock_summarizer

        from data_pipeline.scripts.summarize import main
        import sys
        sys.argv = ["summarize", "--limit", "1"]
        main()

    assert mock_summarizer.summarize.call_count == 1
    mock_db.update_summary.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_script.py -v`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Create the CLI script**

Create `data-pipeline/src/data_pipeline/scripts/summarize.py`:

```python
from __future__ import annotations

import argparse
from pathlib import Path

from data_pipeline.config import Settings
from data_pipeline.db import Database
from data_pipeline.parser import parse_markdown_file
from data_pipeline.summarizer import SummarizerClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LLM summaries for content items.")
    parser.add_argument("--dry-run", action="store_true", help="Count eligible rows; no LLM calls or DB writes.")
    parser.add_argument("--force", action="store_true", help="Re-summarize rows that already have a summary.")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N eligible rows.")
    args = parser.parse_args()

    settings = Settings()
    db = Database(settings.require_db_url())
    rows = db.fetch_unsummarized_content(force=args.force)

    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0.")
        rows = rows[: args.limit]

    print(f"[info] eligible content rows: {len(rows)}")

    if args.dry_run:
        return

    summarizer = SummarizerClient(settings)
    total = len(rows)
    summarized = 0

    for i, row in enumerate(rows, start=1):
        content_id = row["id"]
        title = row["title"]
        filename = row["filename"]
        file_path = settings.data_root / filename

        try:
            doc = parse_markdown_file(file_path, settings.data_root)
            body = doc.body.strip()
            if not body:
                print(f"[skip] empty body for \"{title}\" ({i}/{total})")
                continue
            truncated = body[: settings.summarize_max_chars]
            summary = summarizer.summarize(truncated)
            db.update_summary(content_id, summary)
            summarized += 1
            print(f"[ok] summarized \"{title}\" ({i}/{total})")
        except Exception as exc:
            print(f"[warn] failed \"{title}\": {exc}")

    print(f"[done] summarized {summarized}/{total} content items")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest tests/test_summarize_script.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add data-pipeline/src/data_pipeline/scripts/summarize.py tests/test_summarize_script.py
git commit -m "feat(data-pipeline): add summarize CLI script"
```

---

## Chunk 3: Wiring and Final Verification

### Task 6: Update .env.example and Makefile

**Files:**
- Modify: `.env.example`
- Modify: `Makefile`

- [ ] **Step 1: Add SUMMARIZE_* vars to .env.example**

Append to the end of `.env.example` (before any trailing newline):

```
########################################
# Content Summarization
########################################
SUMMARIZE_API_BASE=
SUMMARIZE_API_KEY=
SUMMARIZE_MODEL=
SUMMARIZE_MAX_CHARS=8000
```

- [ ] **Step 2: Add summarize target to Makefile**

Add after the existing `verify` target in `Makefile`:

```makefile
summarize:
	PYTHONPATH=$(PYTHONPATH) uv run python -m data_pipeline.scripts.summarize
```

- [ ] **Step 3: Commit**

```bash
git add .env.example Makefile
git commit -m "feat(data-pipeline): add summarize Makefile target and env var template"
```

---

### Task 7: Run Full Test Suite

- [ ] **Step 1: Run all tests**

Run: `PYTHONPATH=backend/src:data-pipeline/src uv run pytest -v`
Expected: All tests pass (existing + new)

- [ ] **Step 2: Fix any failures if needed**

- [ ] **Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: address test failures from summarization feature"
```
