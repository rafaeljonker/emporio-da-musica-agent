# 0004. Local CPU embeddings

## Context

Policy chunks and product descriptions need embeddings at ingestion and at query time. Portuguese text is the main input. Anthropic offers no embeddings API, and a key-based embedding service would add a second provider dependency to every setup.

## Decision

Use `intfloat/multilingual-e5-small` through fastembed (ONNX, 384 dimensions, with the `query:` and `passage:` prefixes), running on CPU inside the Python process. There is no torch dependency, no key and no GPU. The model files are baked into the API image, and ingestion runs from that same image, so the image is the version pin (fastembed cannot pin a model revision).

## Consequences

- Works offline and identically for any chat provider.
- The first local run downloads the model; the hosted image already contains it.
- A small model trades some retrieval quality for cost and simplicity; hybrid retrieval ([0003](0003-postgres-pgvector.md)) compensates on exact terms.
- Changing the embedding model means re-ingesting every vector.

## Alternatives

- A hosted embeddings API: better models, but a key, network latency and a second vendor.
- sentence-transformers with torch: same model family, a much heavier install.

Source: [design spec](../superpowers/specs/2026-11-05-emporio-agent-design.md), sections 5, 7.2.2 and 7.2.5.
