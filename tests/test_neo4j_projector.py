from __future__ import annotations


def test_projector_module_imports() -> None:
    import ingest.neo4j_projector as mod

    assert mod is not None
