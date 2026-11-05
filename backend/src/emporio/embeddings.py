from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIM = 384

# ponytail: assumes single-threaded construction at startup; add a threading.Lock if
# built concurrently
_registered = False


class TextEmbedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...


class _Model(Protocol):
    def embed(self, documents: Iterable[str]) -> Iterable[np.ndarray]: ...


def _load_model(cache_dir: Path | None) -> _Model:
    global _registered
    if not _registered:
        # HF revision is not pinned (fastembed ModelSource has no revision field). The phase 6
        # image bakes the model at build time; ingest and query must run on the same baked file.
        TextEmbedding.add_custom_model(
            model=EMBEDDING_MODEL,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=EMBEDDING_MODEL),
            dim=EMBEDDING_DIM,
            model_file="onnx/model.onnx",
        )
        _registered = True
    return TextEmbedding(
        model_name=EMBEDDING_MODEL,
        cache_dir=str(cache_dir) if cache_dir is not None else None,
    )


class E5Embedder:
    """Build once per process: loading the model costs about 1 s."""

    def __init__(self, cache_dir: Path | None = None, *, model: _Model | None = None) -> None:
        self._model = model if model is not None else _load_model(cache_dir)

    def _embed(self, prefix: str, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.embed([f"{prefix}{t}" for t in texts])
        return [[float(x) for x in v] for v in vectors]

    def embed_query(self, text: str) -> list[float]:
        return self._embed("query: ", [text])[0]

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed("passage: ", texts)
