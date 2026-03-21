from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from ingest import cli
from ingest.neo4j_projector import ProjectionPayload


def _minimal_payload() -> ProjectionPayload:
    return {
        "documents": [{"id": "doc:a", "title": "T"}],
        "chunks": [],
        "guests": [],
        "tags": [],
        "concepts": [],
        "frameworks": [],
        "document_guests": [],
        "document_tags": [],
        "chunk_concepts": [],
        "chunk_frameworks": [],
    }


def test_rebuild_graph_reads_canonical_and_projects_with_clear_first(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["ingest", "rebuild-graph"])
    payload = _minimal_payload()
    projection_stats = {"documents": 1, "chunks": 0, "elapsed_ms": 42}

    with (
        patch("ingest.cli.fetch_projection_inputs", return_value=payload) as mock_fetch,
        patch("ingest.cli.project_to_neo4j", return_value=projection_stats) as mock_project,
    ):
        rc = cli.main()

    assert rc == 0
    mock_fetch.assert_called_once_with()
    mock_project.assert_called_once_with(payload, clear_first=True)

    out = capsys.readouterr().out.strip()
    assert json.loads(out) == projection_stats


def test_rebuild_graph_exits_nonzero_on_canonical_read_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.argv", ["ingest", "rebuild-graph"])

    with patch(
        "ingest.cli.fetch_projection_inputs",
        side_effect=RuntimeError("canonical read failed"),
    ):
        rc = cli.main()

    assert rc == 1


def test_rebuild_graph_exits_nonzero_on_projection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("sys.argv", ["ingest", "rebuild-graph"])
    payload = _minimal_payload()

    with (
        patch("ingest.cli.fetch_projection_inputs", return_value=payload),
        patch(
            "ingest.cli.project_to_neo4j",
            side_effect=RuntimeError("projection failed"),
        ),
    ):
        rc = cli.main()

    assert rc == 1
