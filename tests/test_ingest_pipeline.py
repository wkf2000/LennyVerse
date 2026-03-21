from __future__ import annotations

import json
from pathlib import Path

from ingest.pipeline import build_chunks, parse_document, run_pipeline


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

    chunks_a = build_chunks(parsed_a, max_words=10)
    chunks_b = build_chunks(parsed_b, max_words=10)
    assert [chunk.id for chunk in chunks_a] == [
        "chunk:lenny-test-post:0",
        "chunk:lenny-test-post:1",
        "chunk:lenny-test-post:2",
        "chunk:lenny-test-post:3",
    ]
    assert [chunk.id for chunk in chunks_a] == [chunk.id for chunk in chunks_b]


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

