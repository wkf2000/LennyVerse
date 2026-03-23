from pathlib import Path

from data_pipeline.config import Settings
from data_pipeline.parser import parse_corpus


def test_parse_corpus_reads_markdown(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    newsletters = dataset / "newsletters"
    podcasts = dataset / "podcasts"
    newsletters.mkdir(parents=True)
    podcasts.mkdir(parents=True)
    (dataset / "index.json").write_text('{"podcasts":[],"newsletters":[]}', encoding="utf-8")

    (newsletters / "sample-news.md").write_text(
        """---
title: "Sample Newsletter"
type: "newsletter"
date: "2026-01-01"
tags: ["growth", "product-management"]
word_count: 42
---
Hello world.
""",
        encoding="utf-8",
    )

    settings = Settings(DATASET_ROOT_DIR=str(dataset))
    docs = parse_corpus(settings)

    assert len(docs) == 1
    assert docs[0].title == "Sample Newsletter"
    assert docs[0].tags == ["growth", "product-management"]
