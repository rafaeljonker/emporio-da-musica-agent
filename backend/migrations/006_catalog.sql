-- The catalog moves from the CSVs into Postgres; the CSVs only seed it (`emporio.ingest`).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS categories (
    id int PRIMARY KEY,
    name text NOT NULL,
    description text NOT NULL
);

-- Seed rows keep their CSV ids; admin rows take ids from here.
CREATE SEQUENCE IF NOT EXISTS products_admin_id_seq START 100000;

CREATE TABLE IF NOT EXISTS products (
    id int PRIMARY KEY,
    name text NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
    category_id int NOT NULL REFERENCES categories,
    description text NOT NULL CHECK (length(description) <= 2000),
    specs jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(specs) = 'object'),
    price numeric(12, 2) NOT NULL CHECK (price > 0),
    stock int NOT NULL CHECK (stock >= 0),
    status text NOT NULL CHECK (status IN ('active', 'discontinued', 'coming_soon')),
    source text NOT NULL DEFAULT 'seed' CHECK (source IN ('seed', 'admin')),
    owner text,  -- the creating login's lid; NULL exactly for seed rows
    search_doc text NOT NULL,  -- "{name}. {category}. {description} {k: v; ...}", built by the app
    embedding vector(384),  -- NULL until embedded; FTS and trigram still find the row
    embedded_hash text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    tsv tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('portuguese', f_unaccent(name)), 'A')
        || setweight(to_tsvector('portuguese', f_unaccent(search_doc)), 'B')
    ) STORED,
    name_key text GENERATED ALWAYS AS (lower(f_unaccent(name))) STORED,
    code_key text GENERATED ALWAYS AS (
        regexp_replace(lower(f_unaccent(name)), '[^a-z0-9]', '', 'g')
    ) STORED,
    CHECK ((source = 'seed') = (owner IS NULL))
);

CREATE INDEX IF NOT EXISTS products_tsv_idx ON products USING gin (tsv);
CREATE INDEX IF NOT EXISTS products_name_trgm ON products USING gin (name_key gin_trgm_ops);
CREATE INDEX IF NOT EXISTS products_code_trgm ON products USING gin (code_key gin_trgm_ops);
CREATE INDEX IF NOT EXISTS products_embedding_idx
    ON products USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS products_category_idx ON products (category_id);

CREATE TABLE IF NOT EXISTS promotions (
    id int PRIMARY KEY,
    product_id int NOT NULL REFERENCES products,
    percent numeric(5, 2) NOT NULL CHECK (percent > 0 AND percent < 100),
    label text NOT NULL,
    active boolean NOT NULL
);

CREATE INDEX IF NOT EXISTS promotions_active_idx ON promotions (product_id) WHERE active;

-- No FK on product_id: an audit row outlives the product (the reset deletes admin rows).
CREATE TABLE IF NOT EXISTS catalog_audit (
    id bigserial PRIMARY KEY,
    at timestamptz NOT NULL DEFAULT now(),
    actor text NOT NULL,
    action text NOT NULL,
    product_id int NOT NULL,
    after jsonb NOT NULL
);
