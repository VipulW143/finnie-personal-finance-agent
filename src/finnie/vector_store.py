"""FAISS cosine retrieval with citation records in the same row order."""

from collections.abc import Sequence

import faiss
import numpy as np


class VectorStore(Sequence):
    """Sequence interface over chunk records and their FAISS index."""

    def __init__(self, chunks: list[dict], index=None):
        self.chunks = chunks
        if not chunks:
            self.index = faiss.IndexFlatIP(1)
            return
        matrix = normalized_vectors([chunk["embedding"] for chunk in chunks])
        if index is None:
            index = faiss.IndexFlatIP(matrix.shape[1])
            index.add(matrix)
        elif (
            not isinstance(index, faiss.IndexFlatIP)
            or index.ntotal != len(chunks)
            or index.d != matrix.shape[1]
        ):
            raise ValueError("Cached FAISS index does not match chunk records")
        self.index = index

    def __len__(self):
        return len(self.chunks)

    def __getitem__(self, position):
        return self.chunks[position]

    def search(self, vector: list[float], top_k: int) -> list[dict]:
        if not self.chunks:
            return []
        query = normalized_vectors([vector])
        if query.shape[1] != self.index.d:
            raise ValueError("Query and source embedding dimensions differ")
        scores, positions = self.index.search(query, min(top_k, len(self)))
        return [
            {
                **{key: value for key, value in self.chunks[int(row)].items()
                   if key != "embedding"},
                "score": float(score),
            }
            for score, row in zip(scores[0], positions[0])
            if row >= 0
        ]


def normalized_vectors(vectors: list[list[float]]) -> np.ndarray:
    """Validate and normalize vectors so inner product equals cosine similarity."""
    matrix = np.array(vectors, dtype=np.float32, order="C", copy=True)
    if (
        matrix.ndim != 2 or matrix.shape[1] == 0
        or not np.isfinite(matrix).all()
        or np.any(np.linalg.norm(matrix, axis=1) == 0)
    ):
        raise ValueError("Embeddings must be finite nonzero vectors with equal dimensions")
    faiss.normalize_L2(matrix)
    return matrix
