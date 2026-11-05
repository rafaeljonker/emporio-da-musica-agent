import math
from collections.abc import Iterable

import numpy as np

from emporio.embeddings import EMBEDDING_DIM, E5Embedder
from tests.fakes.hash_embedder import HashEmbedder


class RecordingModel:
    def __init__(self) -> None:
        self.inputs: list[str] = []

    def embed(self, documents: Iterable[str]) -> Iterable[np.ndarray]:
        for doc in documents:
            self.inputs.append(doc)
            yield np.ones(EMBEDDING_DIM, dtype=np.float32)


def test_e5_adds_prefixes() -> None:
    model = RecordingModel()
    embedder = E5Embedder(model=model)

    query_vector = embedder.embed_query("posso devolver?")
    passage_vectors = embedder.embed_passages(["a", "b"])

    assert model.inputs == ["query: posso devolver?", "passage: a", "passage: b"]
    assert len(query_vector) == EMBEDDING_DIM
    assert all(isinstance(x, float) for x in query_vector)
    assert len(passage_vectors) == 2


def test_hash_embedder_is_deterministic_unit_384() -> None:
    embedder = HashEmbedder()

    first = embedder.embed_query("Troca")
    assert first == embedder.embed_passages(["troca"])[0]
    assert first != embedder.embed_query("devolucao")
    assert len(first) == EMBEDDING_DIM == 384
    assert math.isclose(math.sqrt(sum(x * x for x in first)), 1.0)
