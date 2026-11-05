CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
  id          BIGSERIAL PRIMARY KEY,
  path        TEXT NOT NULL,
  content     TEXT NOT NULL,
  embedding   vector(768) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
  ON chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS documents (
  path        TEXT PRIMARY KEY,
  content     TEXT NOT NULL,
  kind        TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS index_meta (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL
);