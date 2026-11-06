"""Vector similarity helpers for Finnie's retrieval pipeline."""

from math import sqrt


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity for two equally sized, non-zero vectors."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    if not a:
        raise ValueError("vectors must not be empty")

    length_a = sqrt(sum(value * value for value in a))
    length_b = sqrt(sum(value * value for value in b))
    if length_a == 0 or length_b == 0:
        raise ValueError("vectors must not be zero vectors")

    dot_product = sum(value_a * value_b for value_a, value_b in zip(a, b))
    return dot_product / (length_a * length_b)
