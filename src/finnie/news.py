"""Search for current financial news and return a cited short synthesis."""

from datetime import date
import re

from openai import OpenAI, OpenAIError

from finnie.config import get_settings


NEWS_DOMAINS = [
    "apnews.com",
    "reuters.com",
    "cnbc.com",
    "sec.gov",
    "federalreserve.gov",
    "bls.gov",
    "bea.gov",
    "treasury.gov",
    "irs.gov",
]


class NewsSearchError(RuntimeError):
    """A readable failure from Finnie's current-news lookup."""


def _citation_links(response: object) -> list[tuple[str, str]]:
    """Extract unique clickable citations from Responses API annotations."""
    if not hasattr(response, "model_dump"):
        return []

    payload = response.model_dump()
    citations: list[tuple[str, str]] = []
    seen_urls: set[str] = set()
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") != "output_text":
                continue
            for annotation in content.get("annotations", []):
                if annotation.get("type") != "url_citation":
                    continue
                citation = annotation.get("url_citation", annotation)
                url = str(citation.get("url", "")).strip()
                title = str(citation.get("title", "Source")).strip()
                if url.startswith("https://") and url not in seen_urls:
                    citations.append((title or "Source", url))
                    seen_urls.add(url)
    return citations


def synthesize_financial_news(query: str) -> str:
    """Search current trusted sources and summarize them with source links."""
    query = query.strip()
    if not query:
        raise ValueError("Enter a topic or question for the news search.")

    # Explicit news or event wording takes priority over comparison wording.
    news_intent = re.search(
        r"\b(news|latest|recent\w*|current\w*|today|yesterday|"
        r"this (?:week|month|year)|announc\w*|launch\w*|filings?|"
        r"headlines?|updates?|happened|changed)\b",
        query,
        re.IGNORECASE,
    )
    background_intent = re.search(
        r"\b(vs|versus|compar\w*|differen\w*|explain|define|what (?:is|are))\b",
        query,
        re.IGNORECASE,
    )
    if background_intent and not news_intent:
        return (
            "For a general explanation or comparison, ask Finance Q&A. "
            "For a news brief, include the recent event or timeframe."
        )

    today = date.today()
    prompt = f"""You are Finnie's financial news synthesis agent.
Today's local date is {today}. Search for current, relevant reporting about the
user's topic. Summarize no more than three distinct items. For each item,
separate what the source reports from any brief context. Include publication
dates when available, and say when a date is unclear. Prefer primary sources
and established news organizations, such as {", ".join(NEWS_DOMAINS)}.
Do not make predictions or recommend
buying, selling, or holding an investment. Do not invent details absent from
the retrieved sources. Be concise and educational.

Use dated reporting about concrete recent events or announcements. A recent
publication date alone does not make a general explainer a news story. If the
topic only asks for definitions or comparisons, or search finds no recent
developments, say so and point the user to Finance Q&A for background. Avoid
presenting evergreen explainers as current news.

For broad topics without a named market, default to the United States and
state that scope. Honor any country or region the user specifies.
Prefer direct articles or official releases. Distinguish event dates from
publication dates and label upcoming events as scheduled. A single relevant
development is enough. Unless the user specifies another period, search the
last 30 days relative to today and identify older material as background.
Never substitute a memorized release, invent a dated archive URL, or change
a citation to an archive page unless that page was actually retrieved.

For economic data, explicitly label the reporting period and the original
publication date for each release. For example: "Reporting period: [month
and year]. Released: [full date]." Verify both against the issuing agency.
Use the agency's dated archive link when available so the citation still
points to the same data after the next release. Otherwise cite the specific
release page. Keep any upcoming release date separate and label it scheduled.
For U.S. jobs reports, use the BLS Employment Situation release for payrolls,
unemployment, and nominal hourly earnings. After identifying the reporting
month, search specifically for its archived release under
bls.gov/news.release/archives/ (Employment Situation filenames start with
empsit_). Cite the archived page you found instead of the rolling
empsit.nr0.htm summary. If you include inflation-adjusted
earnings, identify the separate BLS Real Earnings release with its own dates
and direct citation. Use the original release for each figure.

USER TOPIC:
{query}
"""

    settings = get_settings()
    try:
        response = OpenAI().responses.create(
            model=settings["model"],
            tools=[
                {
                    "type": "web_search",
                    "search_context_size": "medium",
                }
            ],
            tool_choice="required",
            input=prompt,
        )
    except OpenAIError as error:
        raise NewsSearchError(
            "Current news search failed. Check the OpenAI API connection, "
            "model access, and account access to web search."
        ) from error

    summary = response.output_text.strip()
    citations = _citation_links(response)
    if not summary:
        raise NewsSearchError(
            "The news search did not return a summary with source links. "
            "Try a more specific topic or try again later."
        )

    if not citations:
        return "I couldn't confirm a news brief with source links. Try a more specific topic."

    source_lines = []
    for title, url in citations[:8]:
        safe_title = title.replace("[", "\\[").replace("]", "\\]")
        source_lines.append(f"- [{safe_title}]({url})")
    return f"{summary}\n\nSources:\n" + "\n".join(source_lines)
