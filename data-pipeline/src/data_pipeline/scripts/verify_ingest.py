from __future__ import annotations

from data_pipeline.config import Settings
from data_pipeline.db import Database
from data_pipeline.embeddings import EmbeddingClient


def main() -> None:
    settings = Settings()
    db = Database(settings.require_db_url())

    counts = db.table_counts()
    print("[info] row counts")
    for key, value in counts.items():
        print(f"  - {key}: {value}")

    embedding_client = EmbeddingClient(settings)
    sample_embedding = embedding_client.embed_texts(["product management leadership growth"])[0]
    nearest = db.sample_similarity(sample_embedding, limit=3)

    print("[info] sample semantic results")
    for row in nearest:
        print(f"  - {row['title']} | {row['filename']} | chunk {row['chunk_index']}")


if __name__ == "__main__":
    main()
