from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingest.extractor import ChunkExtractionResult
from ingest.pipeline import (
    build_chunks,
    normalize_entity_name,
    parse_document,
    run_pipeline,
    stable_concept_id,
    stable_framework_id,
    stable_guest_id,
    stable_tag_id,
)


def _write_fixture(path: Path, body_word_count: int = 35) -> None:
    words = " ".join(f"w{i}" for i in range(body_word_count))
    path.write_text(
        "\n".join(
            [
                "---",
                "source_type: newsletter",
                "source_slug: lenny-test-post",
                "title: Lenny Test Post",
                "published_at: 2026-03-20T00:00:00+00:00",
                "description: fixture",
                "---",
                words,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_and_chunk_are_deterministic(tmp_path: Path) -> None:
    doc_path = tmp_path / "post.md"
    _write_fixture(doc_path, body_word_count=35)

    parsed_a = parse_document(doc_path)
    parsed_b = parse_document(doc_path)
    assert parsed_a.id == parsed_b.id == "doc:lenny-test-post"
    assert parsed_a.checksum == parsed_b.checksum

    chunks_a = build_chunks(parsed_a, chunk_size=30, chunk_overlap=0)
    chunks_b = build_chunks(parsed_b, chunk_size=30, chunk_overlap=0)
    assert len(chunks_a) > 0
    assert [c.id for c in chunks_a] == [c.id for c in chunks_b]


def test_build_chunks_overlap_increases_windows(tmp_path: Path) -> None:
    doc_path = tmp_path / "post.md"
    _write_fixture(doc_path, body_word_count=25)

    parsed = parse_document(doc_path)
    no_overlap = build_chunks(parsed, chunk_size=30, chunk_overlap=0)
    with_overlap = build_chunks(parsed, chunk_size=30, chunk_overlap=10)
    assert len(with_overlap) >= len(no_overlap)


def test_rerun_skips_unchanged_documents(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=50)

    first_run = run_pipeline(input_dir=input_dir, output_dir=output_dir, stages=("parse", "chunk"))
    assert first_run["counts"]["processed_documents"] == 1
    assert first_run["counts"]["chunks_created"] > 0

    second_run = run_pipeline(input_dir=input_dir, output_dir=output_dir, stages=("parse", "chunk"))
    assert second_run["counts"]["processed_documents"] == 0
    assert second_run["stage_stats"]["chunk"]["skipped"] == 1

    checkpoint = json.loads((output_dir / "checkpoint_state.json").read_text(encoding="utf-8"))
    assert "lenny-test-post" in checkpoint["documents"]


def test_force_rerun_reprocesses_unchanged_documents(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=20)

    run_pipeline(input_dir=input_dir, output_dir=output_dir, stages=("parse", "chunk"))
    forced = run_pipeline(input_dir=input_dir, output_dir=output_dir, stages=("parse", "chunk"), force=True)
    assert forced["counts"]["processed_documents"] == 1


def test_build_chunks_uses_markdown_splitter(tmp_path: Path) -> None:
    """MarkdownTextSplitter respects markdown structure in split boundaries."""
    md = "\n".join([
        "---",
        "source_type: newsletter",
        "source_slug: md-split-test",
        "title: Markdown Split Test",
        "published_at: 2026-03-20T00:00:00+00:00",
        "description: fixture",
        "---",
        "# Section One",
        "",
        "First section content that is long enough to matter. " * 10,
        "",
        "# Section Two",
        "",
        "Second section content that is also long enough. " * 10,
    ])
    doc_path = tmp_path / "post.md"
    doc_path.write_text(md, encoding="utf-8")

    parsed = parse_document(doc_path)
    chunks = build_chunks(parsed, chunk_size=200, chunk_overlap=0)

    assert len(chunks) >= 2
    assert all(c.id.startswith("chunk:md-split-test:") for c in chunks)
    assert chunks[0].document_id == "doc:md-split-test"
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_embed_texts_calls_ollama_embed_documents() -> None:
    """embed_texts delegates to OllamaEmbeddings.embed_documents."""
    import ingest.embedder as mod

    mod._embeddings = None  # reset singleton

    fake_embeddings = MagicMock()
    fake_embeddings.embed_documents.return_value = [[0.1, 0.2], [0.3, 0.4]]

    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_texts(["hello", "world"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    fake_embeddings.embed_documents.assert_called_once_with(["hello", "world"])


def test_embed_text_calls_ollama_embed_query() -> None:
    """embed_text delegates to OllamaEmbeddings.embed_query."""
    import ingest.embedder as mod

    mod._embeddings = None  # reset singleton

    fake_embeddings = MagicMock()
    fake_embeddings.embed_query.return_value = [0.5, 0.6]

    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_text("hello")

    assert result == [0.5, 0.6]
    fake_embeddings.embed_query.assert_called_once_with("hello")


def test_embed_texts_empty_input_returns_empty() -> None:
    """embed_texts returns [] for empty input without calling the model."""
    import ingest.embedder as mod

    mod._embeddings = None

    fake_embeddings = MagicMock()
    with patch.object(mod, "_load_embeddings", return_value=fake_embeddings):
        result = mod.embed_texts([])

    assert result == []
    fake_embeddings.embed_documents.assert_not_called()


def test_entity_id_normalization_is_stable() -> None:
    assert normalize_entity_name("  Design   Partner  ") == "Design Partner"
    assert stable_guest_id("Lenny Rachitsky") == "guest:lenny-rachitsky"
    assert stable_tag_id("market research") == "tag:market-research"
    assert stable_concept_id("distribution moat") == "concept:distribution-moat"
    assert stable_framework_id("build trap") == "framework:build-trap"


def test_extract_stage_writes_entity_artifacts(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    (input_dir / "post.md").write_text(
        "\n".join(
            [
                "---",
                "source_type: newsletter",
                "source_slug: lenny-entities",
                "title: Entity Test",
                "published_at: 2026-03-20T00:00:00+00:00",
                "description: fixture",
                "guests: Jane Doe, John Roe",
                "tags: Product, AI",
                "---",
                "A chunk describing jobs-to-be-done and RICE prioritization.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fake_load = MagicMock(return_value={"ok": 1})
    fake_extract = ChunkExtractionResult(
        concepts=[
            {
                "name": "Jobs To Be Done",
                "confidence": 0.9,
                "evidence_span": "jobs-to-be-done",
                "description": "Outcome-driven product framing.",
            }
        ],
        frameworks=[
            {
                "name": "RICE",
                "confidence": 0.8,
                "evidence_span": "RICE prioritization",
                "summary": "Reach, impact, confidence, effort.",
            }
        ],
    )

    with (
        patch("ingest.pipeline.extract_chunk_signals", return_value=fake_extract),
        patch("ingest.pipeline.load_documents_and_chunks", fake_load),
    ):
        run = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "extract", "load"),
        )

    assert run["counts"]["guests_extracted"] == 2
    assert run["counts"]["tags_extracted"] == 2
    assert run["counts"]["concepts_extracted"] == 1
    assert run["counts"]["frameworks_extracted"] == 1
    assert run["counts"]["extraction_errors"] == 0

    assert fake_load.call_count == 1
    kwargs = fake_load.call_args.kwargs
    assert len(kwargs["guests"]) == 2
    assert len(kwargs["tags"]) == 2
    assert len(kwargs["concepts"]) == 1
    assert len(kwargs["frameworks"]) == 1
    assert len(kwargs["chunk_concepts"]) == 1
    assert len(kwargs["chunk_frameworks"]) == 1
    assert len(kwargs["document_guests"]) == 2
    assert len(kwargs["document_tags"]) == 2

    extraction_artifact = json.loads((output_dir / "extractions.json").read_text(encoding="utf-8"))
    assert len(extraction_artifact["guests"]) == 2
    assert len(extraction_artifact["concepts"]) == 1
    assert extraction_artifact["errors"] == []


def test_invalid_extraction_is_recorded_not_fatal(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=30)

    with patch(
        "ingest.pipeline.extract_chunk_signals",
        return_value=ChunkExtractionResult(concepts=[], frameworks=[], error="mock parse failure"),
    ):
        run = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "extract"),
        )

    assert run["counts"]["processed_documents"] == 1
    assert run["counts"]["extraction_errors"] > 0
    extraction_artifact = json.loads((output_dir / "extractions.json").read_text(encoding="utf-8"))
    assert len(extraction_artifact["errors"]) > 0


def test_extract_load_rerun_is_idempotent(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=40)

    fake_extract = ChunkExtractionResult(
        concepts=[{"name": "North Star Metric", "confidence": 0.7, "evidence_span": "", "description": ""}],
        frameworks=[],
    )
    fake_load = MagicMock(return_value={"ok": 1})

    with (
        patch("ingest.pipeline.extract_chunk_signals", return_value=fake_extract),
        patch("ingest.pipeline.load_documents_and_chunks", fake_load),
    ):
        first = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "extract", "load"),
        )
        second = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "extract", "load"),
        )

    assert first["counts"]["processed_documents"] == 1
    assert second["counts"]["processed_documents"] == 0
    assert fake_load.call_count == 1


def test_project_stage_success_adds_projection_result(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=40)

    fake_projection = {"documents": 1, "chunks": 2, "elapsed_ms": 10}

    with patch("ingest.pipeline.project_to_neo4j", return_value=fake_projection) as mock_project:
        run = run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "project"),
        )

    assert run["projection_result"] == fake_projection
    mock_project.assert_called_once()
    assert mock_project.call_args.kwargs.get("clear_first") is False
    last_run = json.loads((output_dir / "last_run.json").read_text(encoding="utf-8"))
    assert last_run["projection_result"] == fake_projection


def test_project_stage_failure_raises_and_preserves_checkpoint(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    post = input_dir / "post.md"
    _write_fixture(post, body_word_count=40)

    with patch("ingest.pipeline.project_to_neo4j", return_value={"ok": 1}):
        run_pipeline(
            input_dir=input_dir,
            output_dir=output_dir,
            stages=("parse", "chunk", "project"),
        )

    checkpoint_after_ok = json.loads((output_dir / "checkpoint_state.json").read_text(encoding="utf-8"))
    checksum_before = checkpoint_after_ok["documents"]["lenny-test-post"]["checksum"]

    post.write_text(
        post.read_text(encoding="utf-8").replace("w39", "w39-edited"),
        encoding="utf-8",
    )

    with patch(
        "ingest.pipeline.project_to_neo4j",
        side_effect=RuntimeError("neo4j connection refused"),
    ):
        with pytest.raises(RuntimeError, match="neo4j connection refused"):
            run_pipeline(
                input_dir=input_dir,
                output_dir=output_dir,
                stages=("parse", "chunk", "project"),
            )

    checkpoint_after_fail = json.loads((output_dir / "checkpoint_state.json").read_text(encoding="utf-8"))
    assert checkpoint_after_fail["documents"]["lenny-test-post"]["checksum"] == checksum_before

    last_run = json.loads((output_dir / "last_run.json").read_text(encoding="utf-8"))
    assert "projection_error" in last_run
    assert last_run["projection_error"]["type"] == "RuntimeError"
    assert "refused" in last_run["projection_error"]["message"]


def test_identity_sets_projection_error_on_project_failure(tmp_path: Path) -> None:
    """On project stage failure, last_run records projection_error and does not claim projection_result."""
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    _write_fixture(input_dir / "post.md", body_word_count=40)

    with patch("ingest.pipeline.project_to_neo4j", side_effect=RuntimeError("neo4j unavailable")):
        with pytest.raises(RuntimeError, match="neo4j unavailable"):
            run_pipeline(
                input_dir=input_dir,
                output_dir=output_dir,
                stages=("parse", "chunk", "project"),
            )

    last_run = json.loads((output_dir / "last_run.json").read_text(encoding="utf-8"))
    assert "projection_error" in last_run
    assert "projection_result" not in last_run
    assert last_run["projection_error"]["type"] == "RuntimeError"
    assert "unavailable" in last_run["projection_error"]["message"]
