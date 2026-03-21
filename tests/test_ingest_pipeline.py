from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
