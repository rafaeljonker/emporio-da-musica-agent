CREATE TABLE product_embeddings (
    product_id integer PRIMARY KEY,
    embedding vector(384) NOT NULL
);

CREATE INDEX product_embeddings_embedding_idx
    ON product_embeddings USING hnsw (embedding vector_cosine_ops);
