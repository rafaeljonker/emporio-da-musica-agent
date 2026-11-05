import hashlib
import math
from collections.abc import Sequence

from emporio.embeddings import EMBEDDING_DIM


class HashEmbedder:
    """Deterministic fake: unit vector from SHA-256 of the lowercased text."""

    def _vector(self, text: str) -> list[float]:
        seed = hashlib.sha256(text.lower().encode()).digest()
        raw = [seed[i % len(seed)] - 127.5 + (i // len(seed)) for i in range(EMBEDDING_DIM)]
        norm = math.sqrt(sum(x * x for x in raw))
        return [x / norm for x in raw]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]
