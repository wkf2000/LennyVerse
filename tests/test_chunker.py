from data_pipeline.chunker import chunk_document
from data_pipeline.models import ParsedDocument


def test_chunk_document_respects_overlap() -> None:
    doc = ParsedDocument(
        id="doc-1",
        type="newsletter",
        title="Doc",
        filename="newsletters/doc-1.md",
        body="A" * 1200,
    )
    chunks = chunk_document(doc, chunk_size=1000, overlap=100)
    assert len(chunks) == 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    # The second chunk should start before 1000 due to overlap.
    assert len(chunks[1].text) >= 200
