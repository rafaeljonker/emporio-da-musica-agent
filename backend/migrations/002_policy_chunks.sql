CREATE TABLE policy_chunks (
    section_id text PRIMARY KEY,
    title text NOT NULL,
    parent_title text,
    body text NOT NULL,
    embedding vector(384) NOT NULL,
    tsv tsvector GENERATED ALWAYS AS (
        to_tsvector('portuguese', f_unaccent(coalesce(parent_title, '') || ' ' || title || ' ' || body))
    ) STORED
);

CREATE INDEX policy_chunks_embedding_idx ON policy_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX policy_chunks_tsv_idx ON policy_chunks USING gin (tsv);
