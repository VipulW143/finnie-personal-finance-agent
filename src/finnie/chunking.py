"""Small, dependency-free text chunking helpers for Finnie's RAG pipeline."""

import re


SOURCE_FIELDS = ("title", "url", "publisher", "topic")


def _wrap_paragraph(paragraph: str, max_chars: int) -> list[str]:
    """Split one paragraph into pieces that fit the character limit."""
    # Keep Markdown line breaks in short paragraphs (for example, lists).
    if len(paragraph) <= max_chars:
        return [paragraph]

    pieces: list[str] = []
    current = ""

    for word in paragraph.split():
        # A single unusually long token must be split to respect max_chars.
        if len(word) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(
                word[index : index + max_chars]
                for index in range(0, len(word), max_chars)
            )
            continue

        if current and len(current) + 1 + len(word) > max_chars:
            pieces.append(current)
            current = word
        elif current:
            current += f" {word}"
        else:
            current = word

    if current:
        pieces.append(current)

    return pieces


def split_text(text: str, max_chars: int = 1000) -> list[str]:
    """Split text into paragraph-aware chunks no longer than ``max_chars``.

    Short paragraphs are combined while they fit. Longer paragraphs are split
    on word boundaries where possible. This simple character-based baseline
    has no overlap; a later RAG iteration can add token-aware sizing and overlap.
    """
    if max_chars < 1:
        raise ValueError("max_chars must be at least 1")

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_text:
        return []

    paragraphs = [
        paragraph.strip()
        for paragraph in normalized_text.split("\n\n")
        if paragraph.strip()
    ]

    chunks: list[str] = []
    current_chunk = ""

    for paragraph in paragraphs:
        for piece in _wrap_paragraph(paragraph, max_chars):
            candidate = f"{current_chunk}\n\n{piece}" if current_chunk else piece
            if len(candidate) <= max_chars:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = piece

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_document(
    text: str,
    source_metadata: dict[str, str],
    max_chars: int = 1000,
) -> list[dict[str, str]]:
    """Split a source document and attach citation metadata to every chunk."""
    missing_fields = [
        field
        for field in SOURCE_FIELDS
        if not source_metadata.get(field, "").strip()
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"source_metadata is missing required fields: {missing}")

    source_title = source_metadata["title"].strip()
    source_id = re.sub(r"[^a-z0-9]+", "-", source_title.lower()).strip("-")
    source_id = source_id or "source"

    chunk_records = []
    for index, chunk_text in enumerate(split_text(text, max_chars), start=1):
        chunk_records.append(
            {
                "chunk_id": f"{source_id}-{index:03d}",
                "text": chunk_text,
                "title": source_title,
                "url": source_metadata["url"].strip(),
                "publisher": source_metadata["publisher"].strip(),
                "topic": source_metadata["topic"].strip(),
            }
        )

    return chunk_records
