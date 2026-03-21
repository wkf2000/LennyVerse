-- Migration: Increase embedding dimension from 768 to 1024
-- Requires: re-embedding all chunks after running (ingest backfill --force)

-- Drop the ANN index first
DROP INDEX IF EXISTS chunks_embedding_idx;

-- Alter the column dimension
ALTER TABLE chunks
  ALTER COLUMN embedding TYPE vector(1024);

-- Recreate the ANN index
CREATE INDEX chunks_embedding_idx
  ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
