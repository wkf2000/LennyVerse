import json
from pathlib import Path

from data_pipeline.graph import build_graph_from_index


def test_build_graph_from_index_creates_expected_entities(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "podcasts": [
                    {
                        "title": "Ada Chen Rekhi",
                        "filename": "03-podcasts/ada-chen-rekhi.md",
                        "guest": "Ada Chen Rekhi",
                        "tags": ["design", "leadership"],
                        "date": "2023-04-16",
                    }
                ],
                "newsletters": [],
            }
        ),
        encoding="utf-8",
    )

    nodes, edges = build_graph_from_index(index_path)
    assert any(node.type == "content" for node in nodes)
    assert any(node.type == "guest" for node in nodes)
    assert any(node.type == "topic" for node in nodes)
    assert any(edge.relationship_type == "appeared_in" for edge in edges)
    assert any(edge.relationship_type == "tagged_with" for edge in edges)
