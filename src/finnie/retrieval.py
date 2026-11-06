"""In-memory semantic retrieval for Finnie's source chunks."""

from finnie.embeddings import embed_texts
from finnie.vector_store import VectorStore


def index_chunks(
    chunks: list[dict[str, str]],
) -> VectorStore:
    """Embed source chunks once and return copies with vectors attached."""
    if not chunks:
        return VectorStore([])

    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts)
    if len(vectors) != len(chunks):
        raise ValueError("Embedding count does not match chunk count")

    indexed_chunks: list[dict[str, str | list[float]]] = []
    for chunk, vector in zip(chunks, vectors):
        indexed_chunk: dict[str, str | list[float]] = dict(chunk)
        indexed_chunk["embedding"] = vector
        indexed_chunks.append(indexed_chunk)

    return VectorStore(indexed_chunks)


def search_chunks(
    query: str,
    indexed_chunks: VectorStore | list[dict[str, str | list[float]]],
    top_k: int = 3,
) -> list[dict[str, str | float]]:
    """Return the most similar chunks, highest cosine score first."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1")
    if not query.strip():
        raise ValueError("query must not be empty")
    if not indexed_chunks:
        return []

    if any("embedding" not in chunk for chunk in indexed_chunks):
        raise ValueError("chunks must be indexed with index_chunks() first")

    store = (
        indexed_chunks if isinstance(indexed_chunks, VectorStore)
        else VectorStore(indexed_chunks)
    )
    query_vector = embed_texts([query])[0]
    return store.search(query_vector, top_k)
