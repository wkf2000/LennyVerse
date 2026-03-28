from pathlib import Path
from unittest.mock import MagicMock, patch
import sys


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
        sys.argv = ["summarize", "--limit", "1"]
        main()

    assert mock_summarizer.summarize.call_count == 1
    mock_db.update_summary.assert_called_once()
