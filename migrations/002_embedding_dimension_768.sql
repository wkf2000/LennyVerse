-- Migration: Decrease embedding dimension from 1024 to 768
-- Requires: re-embedding all chunks after running (ingest backfill --force)

-- Drop the ANN index first
DROP INDEX IF EXISTS chunks_embedding_idx;

-- Alter the column dimension
ALTER TABLE chunks
  ALTER COLUMN embedding TYPE vector(768);

-- Recreate the ANN index
CREATE INDEX chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
