from __future__ import annotations

import argparse
from itertools import islice

from data_pipeline.chunker import chunk_documents
from data_pipeline.config import Settings
from data_pipeline.db import Database
from data_pipeline.embeddings import EmbeddingClient
from data_pipeline.graph import build_graph_from_index
from data_pipeline.models import ChunkRecord
from data_pipeline.parser import parse_corpus


def _batched(items: list[ChunkRecord], size: int):
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest corpus content and graph metadata.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and chunk only; no DB writes.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of source documents to ingest for quick testing.",
    )
    args = parser.parse_args()

    settings = Settings()
    documents = parse_corpus(settings)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0.")
        documents = documents[: args.limit]
    chunks = chunk_documents(
        documents,
        chunk_size=settings.ingest_chunk_size_chars,
        overlap=settings.ingest_chunk_overlap_chars,
    )
    graph_nodes, graph_edges = build_graph_from_index(settings.index_path)

    print(
        f"[info] parsed_docs={len(documents)} chunks={len(chunks)} "
        f"graph_nodes={len(graph_nodes)} graph_edges={len(graph_edges)}"
    )
    if args.dry_run:
        return

    db = Database(settings.require_db_url())
    embedding_client = EmbeddingClient(settings)

    db.upsert_contents(documents)
    print(f"[ok] upserted {len(documents)} content rows")

    total_chunks = 0
    for batch in _batched(chunks, settings.embedding_batch_size):
        embeddings = embedding_client.embed_texts([chunk.text for chunk in batch])
        embedded_batch: list[ChunkRecord] = []
        for chunk, embedding in zip(batch, embeddings, strict=True):
            embedded_batch.append(chunk.model_copy(update={"embedding": embedding}))
        db.upsert_chunks(embedded_batch)
        total_chunks += len(embedded_batch)
        print(f"[ok] upserted chunk batch: {len(embedded_batch)} (total={total_chunks})")

    db.upsert_graph_nodes(graph_nodes)
    db.upsert_graph_edges(graph_edges)
    print(f"[ok] upserted graph nodes={len(graph_nodes)} edges={len(graph_edges)}")


if __name__ == "__main__":
    main()
