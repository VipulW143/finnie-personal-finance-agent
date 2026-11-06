"""Read the source catalog and group captured articles by topic."""

import json

from finnie.config import PROJECT_ROOT


ARTICLES_DIR = PROJECT_ROOT / "articles"


def load_sources() -> list[dict[str, str]]:
    """Return catalog entries with a captured local article."""
    sources = json.loads(
        (ARTICLES_DIR / "sources.json").read_text(encoding="utf-8")
    )
    return [source for source in sources if source.get("file")]


def category_of(topic: str) -> str:
    """Group detailed topics such as 'Investing: index funds' under Investing."""
    return topic.split(":", 1)[0].strip()


def load_glossary() -> list[dict[str, str]]:
    """Load curated definitions; these are not counted as captured articles."""
    return json.loads((ARTICLES_DIR / "glossary.json").read_text(encoding="utf-8"))


def search_glossary(query: str, category: str = "All topics") -> list[dict[str, str]]:
    """Filter local definitions by category and case-insensitive text, without APIs."""
    query = query.strip().casefold()
    return sorted(
        [entry for entry in load_glossary()
         if (category == "All topics" or category_of(entry["topic"]) == category)
         and (not query or query in " ".join(
             entry[field] for field in ("term", "definition", "topic")
         ).casefold())],
        key=lambda entry: entry["term"].casefold(),
    )
