"""OpenAI embedding helpers for Finnie's retrieval pipeline."""

from openai import OpenAI

from finnie.config import get_settings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per text, in the same order as the input."""
    if not texts:
        return []

    clean_texts = [text.strip() for text in texts]
    if any(not text for text in clean_texts):
        raise ValueError("texts must not contain empty or whitespace-only values")

    settings = get_settings()
    client = OpenAI()
    response = client.embeddings.create(
        model=settings["embedding_model"],
        input=clean_texts,
        encoding_format="float",
    )

    # Use each response item's index to keep vectors aligned with input texts.
    ordered_results = sorted(response.data, key=lambda item: item.index)
    return [item.embedding for item in ordered_results]
