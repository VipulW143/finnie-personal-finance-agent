"""Ground Finnie's answers in retrieved financial-education passages."""

import base64
import binascii
import hashlib
import json
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import faiss
import numpy as np

from finnie.chunking import chunk_document
from finnie.config import PROJECT_ROOT, get_settings
from finnie.llm import ask_model
from finnie.retrieval import index_chunks, search_chunks
from finnie.knowledge import category_of, load_sources
from finnie.vector_store import VectorStore


INDEX_CACHE_VERSION = 2
INDEX_CACHE_PATH = PROJECT_ROOT / ".finnie" / "knowledge_index.json"


def _cache_digest(chunks: list[dict], index_bytes: bytes) -> str:
    metadata = json.dumps(chunks, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(metadata + index_bytes).hexdigest()


def _read_cached_index(fingerprint: str) -> tuple[VectorStore, bool] | None:
    """Restore the local index, or migrate valid legacy cached embeddings."""
    try:
        cache = json.loads(INDEX_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(cache, dict) or cache.get("version") not in (1, INDEX_CACHE_VERSION):
        return None
    if cache.get("fingerprint") != fingerprint:
        return None
    chunks = cache.get("chunks")
    if not isinstance(chunks, list):
        return None
    required = ("chunk_id", "text", "title", "url", "publisher", "topic")
    for chunk in chunks:
        if not isinstance(chunk, dict) or not all(
            isinstance(chunk.get(field), str) for field in required
        ):
            return None
        vector = chunk.get("embedding")
        if not isinstance(vector, list) or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for value in vector
        ):
            return None

    if cache.get("version") == INDEX_CACHE_VERSION:
        try:
            raw = base64.b64decode(cache["faiss_index"], validate=True)
            if cache.get("digest") != _cache_digest(chunks, raw):
                raise ValueError("Cache checksum mismatch")
            index = faiss.deserialize_index(np.frombuffer(raw, dtype=np.uint8))
            return VectorStore(chunks, index), False
        except (KeyError, TypeError, ValueError, RuntimeError, binascii.Error):
            # Reconstruct a damaged index from usable cached embeddings.
            pass
    try:
        return VectorStore(chunks), True
    except (KeyError, TypeError, ValueError):
        return None


def _write_cached_index(fingerprint: str, store: VectorStore) -> None:
    """Replace metadata and native FAISS bytes together using a unique temp file."""
    raw = faiss.serialize_index(store.index).tobytes()
    payload = {
        "version": INDEX_CACHE_VERSION, "fingerprint": fingerprint,
        "chunks": store.chunks,
        "faiss_index": base64.b64encode(raw).decode("ascii"),
        "digest": _cache_digest(store.chunks, raw),
    }
    INDEX_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=INDEX_CACHE_PATH.parent,
            prefix="knowledge_index-", suffix=".tmp", delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False)
        temporary_path.replace(INDEX_CACHE_PATH)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def load_knowledge_base(allow_rebuild: bool = True) -> VectorStore:
    """Load the cached index or build it again when source inputs change."""
    articles_dir = PROJECT_ROOT / "articles"
    sources = load_sources()

    chunks: list[dict[str, str]] = []
    fingerprint_sources: list[dict[str, str]] = []
    for source in sources:
        filename = source.get("file")
        if not filename:
            # Catalog entries without a local file are candidates, not ingested sources.
            continue

        document_path = articles_dir / filename
        document = document_path.read_text(encoding="utf-8")
        chunks.extend(chunk_document(document, source))
        fingerprint_sources.append(
            {
                "file": filename,
                "text": document,
                "title": source["title"],
                "url": source["url"],
                "publisher": source["publisher"],
                "topic": source["topic"],
            }
        )

    fingerprint_data = {
        "embedding_model": get_settings()["embedding_model"],
        "sources": fingerprint_sources,
    }
    fingerprint_text = json.dumps(
        fingerprint_data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    fingerprint = hashlib.sha256(fingerprint_text.encode("utf-8")).hexdigest()

    cached = _read_cached_index(fingerprint)
    if cached is not None:
        store, migrated = cached
        if migrated:
            _write_cached_index(fingerprint, store)
            print("Migrated saved embeddings to Finnie's FAISS index.")
        else:
            print("Using saved Finnie FAISS knowledge base.")
        return store

    if not allow_rebuild:
        raise ValueError("No current saved knowledge index; rebuild it with API access first")
    print("Creating Finnie's knowledge base and embedding its sources...")
    store = index_chunks(chunks)
    _write_cached_index(fingerprint, store)
    return store


def answer_with_sources(
    question: str,
    indexed_chunks: VectorStore | list[dict[str, str | list[float]]],
    top_k: int = 3,
    tax_education: bool = False,
    history: list[dict[str, str]] | None = None,
    category: str | None = None,
) -> str:
    """Answer from retrieved passages and append their source links."""
    tax_help = (
        "\n\nIRS guidance: [Federal tax filing instructions]"
        "(https://www.irs.gov/how-to-file-your-taxes-step-by-step)"
        if tax_education else ""
    )
    if tax_education:
        indexed_chunks = [
            chunk for chunk in indexed_chunks
            if chunk["publisher"] == "Internal Revenue Service (IRS)"
        ]
        # Keep the supported rule and its citation together for this common
        # personal calculation request.
        if (
            re.search(r"\b(?:traditional|pre[ -]?tax)\s+401\s*\(?k\)?", question, re.I)
            and re.search(r"\b(?:calculat\w*|how much|exactly)\b", question, re.I)
            and re.search(r"\b(?:tax|owe|refund)\b", question, re.I)
        ):
            source = next(
                (
                    chunk for chunk in indexed_chunks
                    if chunk["url"] == "https://www.irs.gov/retirement-plans/401k-plans"
                ),
                None,
            )
            if source:
                return (
                    "Finnie provides general tax education and cannot calculate "
                    "a personal tax bill.\n\n"
                    "Traditional pretax 401(k) contributions generally reduce "
                    "federal taxable income in the year of contribution [1]."
                    f"\n\nSources:\n[1] {source['title']}: {source['url']}"
                    + tax_help
                )
    if category:
        indexed_chunks = [
            chunk for chunk in indexed_chunks
            if category_of(str(chunk["topic"])) == category
        ]
        if not indexed_chunks:
            return (
                f"No captured source passages are available in {category}. "
                "Choose another topic or All topics." + tax_help
            )
    matches = search_chunks(question, indexed_chunks, top_k=top_k)
    if not matches:
        return (
            "I don't have any indexed source passages to answer from yet. "
            "Please add a source document and build the knowledge base." + tax_help
        )

    context_sections = []
    for number, match in enumerate(matches, start=1):
        context_sections.append(
            f"[{number}] {match['title']} ({match['publisher']})\n"
            f"{match['text']}"
        )

    tax_guidance = ""
    if tax_education:
        tax_guidance = """
For Tax Education requests, answer only general U.S. federal tax concepts
supported by the passages. Do not determine a user's filing obligation,
eligibility, tax liability, or refund, and do not calculate personal tax
amounts. If asked for a personal determination, briefly state that Finnie
provides general tax education and cannot calculate a personal tax bill.
Then explain a relevant general concept if the passages support one, and cite
that passage immediately. For example, if the question mentions a traditional
401(k) and a passage explains pretax contributions, describe their general
effect on federal taxable income without applying it to the user's numbers.
If no passage supports a relevant concept, keep the response brief. The app
will provide a direct IRS guidance link.
"""

    recent_answers = "\n".join(
        turn["content"].split("Sources:", 1)[0].split("IRS guidance:", 1)[0][:3000]
        for turn in (history or [])[-4:]
        if turn.get("role") == "assistant" and isinstance(turn.get("content"), str)
    )
    prompt = f"""You are Finnie, an educational personal-finance assistant.
Treat the source passages below as the complete evidence available. Every
factual sentence must be directly supported by a passage and cite it immediately,
for example [1]. Do not infer causes or effects, explain an unstated mechanism,
or add generic benefits, examples, or finance advice from memory. Even a
plausible or commonly accepted claim must be omitted unless the passages support
it.

Before answering, check each factual sentence against the passages and remove
anything that is not directly supported. If the question asks for more detail
than the passages provide, answer only the supported part and clearly state
what the passages do not explain.
Mention a source limitation only when it prevents answering a part the user
actually requested. If the passages answer the question, finish with the
supported explanation. Do not append a generic statement about missing
step-by-step detail. When a passage includes an example's initial balance,
interest rate, intermediate interest amounts, and final balance, it supports
explaining that calculation; do not claim it gives only the final result.

For questions asking why someone should do something, or asking for reasons or
benefits, include a reason only when a passage explicitly states it. If the
passages do not state a reason, say so directly. You may then report relevant
facts that the passages do state, but do not frame those facts as reasons,
benefits, or implications. Hedging does not make an inference source-supported:
do not write that a fact "may suggest," "could imply," or otherwise hint at an
unstated benefit or conclusion.

If the question asks for a procedure but the passages describe only a goal,
learning objective, or activity, say that the passages do not give step-by-step
instructions. Summarize only the supported goal or activity, and identify the
missing details. Never turn an activity or learning objective into procedural
steps. Keep the answer educational; do not give personalized investment, legal,
or tax advice.
{tax_guidance}

SOURCE PASSAGES:
{chr(10).join(context_sections)}

RECENT ASSISTANT ANSWERS (conversation context only, never source evidence):
{recent_answers}

When following up, focus on the newly requested aspect. Avoid repeating the
full prior overview. For "how does that affect taxable income", explain the
income treatment supported by the passages. Omit withdrawal treatment unless
the current question asks about withdrawals. Do not copy prior source lists
or IRS guidance links into the answer; the app appends links.
Add source-supported detail when
available. If the sources have no further detail, say so briefly.
Write currency with ordinary dollar signs, such as $100. Do not copy stray
backticks around monetary amounts from the user's question.

USER QUESTION:
{question}
"""

    answer = ask_model(prompt).strip()
    if not answer:
        answer = "I couldn't produce an answer from the retrieved passages."

    # Keep only source links for citation markers actually used in the answer.
    cited_numbers = dict.fromkeys(
        int(number) for number in re.findall(r"\[(\d+)\]", answer)
    )
    references_by_url: dict[str, tuple[str, list[int]]] = {}
    for number in cited_numbers:
        if number < 1 or number > len(matches):
            continue

        match = matches[number - 1]
        url = str(match["url"])
        if url not in references_by_url:
            references_by_url[url] = (str(match["title"]), [])
        references_by_url[url][1].append(number)

    reference_lines = [
        f"{', '.join(f'[{number}]' for number in numbers)} {title}: {url}"
        for url, (title, numbers) in references_by_url.items()
    ]
    if not reference_lines and not tax_education:
        reference_lines.append("No retrieved passages were cited.")

    if reference_lines:
        answer += "\n\nSources:\n" + "\n".join(reference_lines)
    return answer + tax_help
