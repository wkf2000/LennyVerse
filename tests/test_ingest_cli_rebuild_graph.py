from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from ingest import cli
from ingest.neo4j_projector import ProjectionPayload, projection_identity_node_keys, projection_identity_relationship_keys

import tests.test_neo4j_projector as neo4j_projector_tests


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


def test_rebuild_graph_ignored_output_flag_still_succeeds(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["ingest", "rebuild-graph", "--output", "/legacy/ingest-output"],
    )
    payload = _minimal_payload()
    projection_stats = {"documents": 1, "chunks": 0, "elapsed_ms": 7}

    with (
        patch("ingest.cli.fetch_projection_inputs", return_value=payload) as mock_fetch,
        patch("ingest.cli.project_to_neo4j", return_value=projection_stats) as mock_project,
    ):
        rc = cli.main()

    assert rc == 0
    mock_fetch.assert_called_once_with()
    mock_project.assert_called_once_with(payload, clear_first=True)
    captured = capsys.readouterr()
    assert "--output is ignored for rebuild-graph" in captured.err
    out = captured.out.strip()
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


def test_backfill_exits_nonzero_on_projection_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Backfill must signal failure when Neo4j projection raises (same contract as rebuild-graph)."""
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "post.md").write_text(
        "\n".join(
            [
                "---",
                "source_type: newsletter",
                "source_slug: bf-proj-fail",
                "title: BF",
                "published_at: 2026-03-20T00:00:00+00:00",
                "description: x",
                "---",
                "hello world " * 20,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest",
            "backfill",
            "--source",
            "newsletter",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--stages",
            "parse,chunk,project",
        ],
    )
    with patch("ingest.pipeline.project_to_neo4j", side_effect=RuntimeError("projection failed")):
        rc = cli.main()

    assert rc == 1


def _assert_cli_run_exits_nonzero_on_projection_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    *,
    source_slug: str = "run-proj-fail",
) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "post.md").write_text(
        "\n".join(
            [
                "---",
                "source_type: newsletter",
                f"source_slug: {source_slug}",
                "title: Run",
                "published_at: 2026-03-20T00:00:00+00:00",
                "description: x",
                "---",
                "hello world " * 20,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest",
            "run",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--stages",
            "parse,chunk,project",
        ],
    )
    with patch("ingest.pipeline.project_to_neo4j", side_effect=RuntimeError("projection failed")):
        rc = cli.main()

    assert rc == 1


def test_run_exits_nonzero_on_projection_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Run must return exit code 1 when the pipeline raises (aligned with backfill)."""
    _assert_cli_run_exits_nonzero_on_projection_failure(monkeypatch, tmp_path)


def test_identity_sets_run_exits_nonzero_on_projection_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Task 6 -k identity_sets: ``run`` exits non-zero when projection fails (selector alias)."""
    _assert_cli_run_exits_nonzero_on_projection_failure(
        monkeypatch, tmp_path, source_slug="run-proj-fail-identity-sets"
    )


def test_cli_pipeline_projection_failure_logs_one_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI owns stack traces; pipeline projection must not emit a second exception traceback."""
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "post.md").write_text(
        "\n".join(
            [
                "---",
                "source_type: newsletter",
                "source_slug: tb-once",
                "title: TB",
                "published_at: 2026-03-20T00:00:00+00:00",
                "description: x",
                "---",
                "hello world " * 20,
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ingest",
            "run",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
            "--stages",
            "parse,chunk,project",
        ],
    )
    with patch("ingest.pipeline.project_to_neo4j", side_effect=RuntimeError("projection failed")):
        rc = cli.main()

    assert rc == 1
    err = capsys.readouterr().err
    assert err.count("Traceback (most recent call last)") == 1


def _rich_rebuild_payload() -> ProjectionPayload:
    return {
        "documents": [
            {
                "id": "doc:a",
                "source_type": "newsletter",
                "source_slug": "a",
                "title": "A",
                "published_at": None,
                "word_count": 1,
                "description": "",
                "checksum": "x",
                "ingested_at": "t",
                "updated_at": "t",
                "path": "/p",
            }
        ],
        "chunks": [
            {
                "id": "chunk:a:0",
                "document_id": "doc:a",
                "chunk_index": 0,
                "content": "c",
                "token_count": 1,
                "metadata": {},
                "embedding": None,
            }
        ],
        "guests": [{"id": "guest:g1", "name": "G1", "profile": {}}],
        "tags": [{"id": "tag:t1", "name": "t1"}],
        "concepts": [
            {
                "id": "concept:c1",
                "name": "c1",
                "normalized_name": "c1",
                "description": "d",
            }
        ],
        "frameworks": [
            {"id": "framework:f1", "name": "f1", "summary": "s", "confidence": 0.5}
        ],
        "document_guests": [
            {"document_id": "doc:a", "guest_id": "guest:g1", "role": "", "confidence": 1.0}
        ],
        "document_tags": [{"document_id": "doc:a", "tag_id": "tag:t1"}],
        "chunk_concepts": [
            {
                "chunk_id": "chunk:a:0",
                "concept_id": "concept:c1",
                "confidence": 0.4,
                "evidence_span": "e",
            }
        ],
        "chunk_frameworks": [
            {
                "chunk_id": "chunk:a:0",
                "framework_id": "framework:f1",
                "confidence": 0.6,
                "evidence_span": "x",
            }
        ],
    }


def test_rebuild_graph_cli_clear_first_removes_stale_in_scope_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rebuild-graph uses the same clear+project contract as ``project_to_neo4j(..., clear_first=True)``."""
    import ingest.neo4j_projector as np

    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "50")
    monkeypatch.setattr("sys.argv", ["ingest", "rebuild-graph"])
    emu = neo4j_projector_tests._ProjectionGraphEmulator()
    emu.nodes[("Document", "doc:stale")] = {"id": "doc:stale"}
    emu.rels.add(
        ("HAS_TAG", "doc:stale", "tag:orphan", np.projection_rel_props_key({}))
    )
    emu.nodes[("Tag", "tag:orphan")] = {"id": "tag:orphan"}
    payload = _rich_rebuild_payload()

    def real_project(p: ProjectionPayload, *, clear_first: bool = False) -> dict[str, int]:
        with patch.object(np, "_connect_driver", return_value=neo4j_projector_tests._emulator_driver(emu)):
            return np.project_to_neo4j(p, clear_first=clear_first)

    with (
        patch("ingest.cli.fetch_projection_inputs", return_value=payload),
        patch("ingest.cli.project_to_neo4j", side_effect=real_project),
    ):
        rc = cli.main()

    assert rc == 0
    assert ("Document", "doc:stale") not in emu.nodes
    assert ("Tag", "tag:orphan") not in emu.nodes


def test_rebuild_graph_cli_identity_sets_match_canonical_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """rebuild-graph: emulated graph node/rel identity_sets match canonical projection input."""
    import ingest.neo4j_projector as np

    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "50")
    monkeypatch.setattr("sys.argv", ["ingest", "rebuild-graph"])
    emu = neo4j_projector_tests._ProjectionGraphEmulator()
    payload = _rich_rebuild_payload()
    expected_nodes = projection_identity_node_keys(payload)
    expected_rels = projection_identity_relationship_keys(payload)

    def real_project(p: ProjectionPayload, *, clear_first: bool = False) -> dict[str, int]:
        with patch.object(np, "_connect_driver", return_value=neo4j_projector_tests._emulator_driver(emu)):
            return np.project_to_neo4j(p, clear_first=clear_first)

    with (
        patch("ingest.cli.fetch_projection_inputs", return_value=payload),
        patch("ingest.cli.project_to_neo4j", side_effect=real_project),
    ):
        rc = cli.main()

    assert rc == 0
    assert set(emu.nodes.keys()) == expected_nodes
    assert emu.rels == expected_rels
    assert json.loads(capsys.readouterr().out.strip())["elapsed_ms"] >= 0
