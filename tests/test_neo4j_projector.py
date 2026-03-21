from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ingest import neo4j_projector as np


def _minimal_payload(**overrides: object) -> np.ProjectionPayload:
    base: np.ProjectionPayload = {
        "documents": [],
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
    merged = {**base, **overrides}  # type: ignore[arg-type]
    return merged  # type: ignore[return-value]


def _session_context(mock_session: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__enter__.return_value = mock_session
    cm.__exit__.return_value = None
    return cm


@pytest.fixture
def mock_neo4j_driver() -> MagicMock:
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value = _session_context(mock_session)
    return mock_driver


def test_project_to_neo4j_runs_constraints_before_any_unwind_upserts(
    mock_neo4j_driver: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "50")
    mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
    queries: list[str] = []
    mock_session.run.side_effect = lambda q, *a, **k: queries.append(q)

    docs = [
        {
            "id": f"doc:{i}",
            "source_type": "newsletter",
            "source_slug": f"post-{i}",
            "title": f"T{i}",
            "published_at": None,
            "word_count": 10,
            "description": "",
            "checksum": "x",
            "ingested_at": "t",
            "updated_at": "t",
            "path": "/p",
        }
        for i in range(3)
    ]
    chunks = [
        {
            "id": f"chunk:p{i}:0",
            "document_id": f"doc:{i}",
            "chunk_index": 0,
            "content": "hello",
            "token_count": 1,
            "metadata": {},
            "embedding": None,
        }
        for i in range(3)
    ]
    payload = _minimal_payload(documents=docs, chunks=chunks)

    with patch.object(np, "_connect_driver", return_value=mock_neo4j_driver):
        np.project_to_neo4j(payload)

    constraint_indices = [i for i, q in enumerate(queries) if "CONSTRAINT" in q.upper()]
    unwind_indices = [i for i, q in enumerate(queries) if "UNWIND" in q.upper()]
    assert constraint_indices, "expected constraint statements"
    assert unwind_indices, "expected batched UNWIND upserts"
    assert max(constraint_indices) < min(unwind_indices)


def test_project_to_neo4j_batches_node_upserts_by_batch_size(
    mock_neo4j_driver: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "2")
    mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
    queries: list[str] = []
    mock_session.run.side_effect = lambda q, *a, **k: queries.append(q)

    docs = [
        {
            "id": f"doc:{i}",
            "source_type": "newsletter",
            "source_slug": f"post-{i}",
            "title": f"T{i}",
            "published_at": None,
            "word_count": 10,
            "description": "",
            "checksum": "x",
            "ingested_at": "t",
            "updated_at": "t",
            "path": "/p",
        }
        for i in range(5)
    ]
    payload = _minimal_payload(documents=docs)

    with patch.object(np, "_connect_driver", return_value=mock_neo4j_driver):
        np.project_to_neo4j(payload)

    doc_merges = [q for q in queries if "MERGE (n:Document" in q.replace("\n", " ")]
    assert len(doc_merges) == 3


def test_project_to_neo4j_batches_relationship_upserts(
    mock_neo4j_driver: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "2")
    mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
    queries: list[str] = []
    mock_session.run.side_effect = lambda q, *a, **k: queries.append(q)

    payload = _minimal_payload(
        documents=[
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
        chunks=[
            {
                "id": "chunk:a:0",
                "document_id": "doc:a",
                "chunk_index": 0,
                "content": "c",
                "token_count": 1,
                "metadata": {},
                "embedding": None,
            },
            {
                "id": "chunk:a:1",
                "document_id": "doc:a",
                "chunk_index": 1,
                "content": "d",
                "token_count": 1,
                "metadata": {},
                "embedding": None,
            },
            {
                "id": "chunk:a:2",
                "document_id": "doc:a",
                "chunk_index": 2,
                "content": "e",
                "token_count": 1,
                "metadata": {},
                "embedding": None,
            },
        ],
    )

    with patch.object(np, "_connect_driver", return_value=mock_neo4j_driver):
        np.project_to_neo4j(payload)

    part_of = [q for q in queries if "PART_OF" in q and "UNWIND" in q]
    assert len(part_of) == 2


def test_project_to_neo4j_clear_first_runs_after_constraints_before_upserts(
    mock_neo4j_driver: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "50")
    mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
    queries: list[str] = []
    mock_session.run.side_effect = lambda q, *a, **k: queries.append(q)

    payload = _minimal_payload(
        documents=[
            {
                "id": "doc:x",
                "source_type": "newsletter",
                "source_slug": "x",
                "title": "X",
                "published_at": None,
                "word_count": 1,
                "description": "",
                "checksum": "x",
                "ingested_at": "t",
                "updated_at": "t",
                "path": "/p",
            }
        ]
    )

    with patch.object(np, "_connect_driver", return_value=mock_neo4j_driver):
        np.project_to_neo4j(payload, clear_first=True)

    clear_idx = next(i for i, q in enumerate(queries) if "DETACH DELETE" in q)
    last_constraint = max(i for i, q in enumerate(queries) if "CONSTRAINT" in q.upper())
    first_unwind = next(i for i, q in enumerate(queries) if "UNWIND" in q)
    assert last_constraint < clear_idx < first_unwind


def test_project_to_neo4j_returns_counts_and_elapsed_ms(
    mock_neo4j_driver: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NEO4J_PROJECTION_BATCH_SIZE", "50")
    mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
    mock_session.run.return_value = None

    payload = _minimal_payload(
        documents=[
            {
                "id": "doc:z",
                "source_type": "newsletter",
                "source_slug": "z",
                "title": "Z",
                "published_at": None,
                "word_count": 1,
                "description": "",
                "checksum": "x",
                "ingested_at": "t",
                "updated_at": "t",
                "path": "/p",
            }
        ],
        guests=[{"id": "guest:amy", "name": "Amy", "profile": {}}],
        document_guests=[{"document_id": "doc:z", "guest_id": "guest:amy", "role": "", "confidence": 1.0}],
    )

    with patch.object(np, "_connect_driver", return_value=mock_neo4j_driver):
        stats = np.project_to_neo4j(payload)

    assert stats["documents"] == 1
    assert stats["guests"] == 1
    assert stats["rels_features_guest"] == 1
    assert "elapsed_ms" in stats
    assert stats["elapsed_ms"] >= 0


def test_projector_module_imports() -> None:
    import ingest.neo4j_projector as mod

    assert mod is not None


def test_mentions_concept_rollup_sums_confidence_and_distinct_chunks() -> None:
    chunk_to_document = {"chunk-1": "doc-a", "chunk-2": "doc-a"}
    chunk_concepts = [
        {"chunk_id": "chunk-1", "concept_id": "concept:alpha", "confidence": 0.5},
        {"chunk_id": "chunk-1", "concept_id": "concept:alpha", "confidence": 0.2},
        {"chunk_id": "chunk-2", "concept_id": "concept:alpha", "confidence": 0.3},
        {"chunk_id": "chunk-2", "concept_id": "concept:beta", "confidence": None},
    ]
    edges = np.build_mentions_concept_edges(chunk_concepts, chunk_to_document)
    by_pair = {(e["start_id"], e["end_id"]): e for e in edges}
    alpha = by_pair[("doc-a", "concept:alpha")]
    assert alpha["rel_type"] == "MENTIONS_CONCEPT"
    assert alpha["properties"]["weight"] == 1.0
    assert alpha["properties"]["evidence_count"] == 2
    beta = by_pair[("doc-a", "concept:beta")]
    assert beta["properties"]["weight"] == 0.0
    assert beta["properties"]["evidence_count"] == 1


def test_uses_framework_rollup_sums_confidence_and_distinct_chunks() -> None:
    chunk_to_document = {"chunk-1": "doc-b", "chunk-2": "doc-b"}
    chunk_frameworks = [
        {"chunk_id": "chunk-1", "framework_id": "framework:flywheel", "confidence": 0.8},
        {"chunk_id": "chunk-2", "framework_id": "framework:flywheel", "confidence": 0.1},
    ]
    edges = np.build_uses_framework_edges(chunk_frameworks, chunk_to_document)
    assert len(edges) == 1
    e = edges[0]
    assert e["rel_type"] == "USES_FRAMEWORK"
    assert e["start_id"] == "doc-b"
    assert e["end_id"] == "framework:flywheel"
    assert e["properties"]["weight"] == 0.9
    assert e["properties"]["evidence_count"] == 2


def test_related_to_distinct_documents_canonical_direction_and_method() -> None:
    chunk_to_document = {
        "c1": "doc-1",
        "c2": "doc-1",
        "c3": "doc-2",
        "c4": "doc-2",
        "c5": "doc-3",
    }
    chunk_concepts = [
        {"chunk_id": "c1", "concept_id": "concept:zebra"},
        {"chunk_id": "c2", "concept_id": "concept:apple"},
        {"chunk_id": "c3", "concept_id": "concept:zebra"},
        {"chunk_id": "c4", "concept_id": "concept:apple"},
        {"chunk_id": "c5", "concept_id": "concept:zebra"},
    ]
    edges = np.build_related_to_edges(chunk_concepts, chunk_to_document)
    by_endpoints = {(e["start_id"], e["end_id"]): e for e in edges}
    key = ("concept:apple", "concept:zebra")
    assert key in by_endpoints
    e = by_endpoints[key]
    assert e["rel_type"] == "RELATED_TO"
    assert e["properties"]["method"] == "cooccurrence_p0"
    assert e["properties"]["weight"] == 2
    assert ("concept:zebra", "concept:apple") not in by_endpoints


def test_related_to_excludes_self_pairs() -> None:
    chunk_to_document = {"c1": "doc-x"}
    chunk_concepts = [
        {"chunk_id": "c1", "concept_id": "concept:solo"},
        {"chunk_id": "c1", "concept_id": "concept:solo", "confidence": 0.5},
    ]
    assert np.build_related_to_edges(chunk_concepts, chunk_to_document) == []


def test_guest_and_tag_edges_have_stable_shape_and_order() -> None:
    document_guests = [
        {"document_id": "doc:z", "guest_id": "guest:bob", "role": "host"},
        {"document_id": "doc:a", "guest_id": "guest:amy"},
    ]
    document_tags = [
        {"document_id": "doc:z", "tag_id": "tag:beta"},
        {"document_id": "doc:a", "tag_id": "tag:alpha"},
    ]
    guest_edges = np.build_features_guest_edges(document_guests)
    tag_edges = np.build_has_tag_edges(document_tags)
    assert guest_edges == [
        {
            "rel_type": "FEATURES_GUEST",
            "start_id": "doc:a",
            "end_id": "guest:amy",
            "properties": {},
        },
        {
            "rel_type": "FEATURES_GUEST",
            "start_id": "doc:z",
            "end_id": "guest:bob",
            "properties": {},
        },
    ]
    assert tag_edges == [
        {
            "rel_type": "HAS_TAG",
            "start_id": "doc:a",
            "end_id": "tag:alpha",
            "properties": {},
        },
        {
            "rel_type": "HAS_TAG",
            "start_id": "doc:z",
            "end_id": "tag:beta",
            "properties": {},
        },
    ]
