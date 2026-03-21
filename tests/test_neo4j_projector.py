from __future__ import annotations

from ingest import neo4j_projector as np


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
