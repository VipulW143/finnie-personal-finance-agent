"""News intent, citation extraction, missing evidence, and provider failures.

These tests validate software behavior, not the accuracy of live news facts.
"""

from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from openai import OpenAIError

from finnie.news import _citation_links, NewsSearchError, synthesize_financial_news


def response(text="A dated news summary.", annotations=None):
    annotations = annotations if annotations is not None else [dict(type="url_citation", title="Primary [release]", url="https://example.org/release")]
    return SimpleNamespace(output_text=text, model_dump=lambda: {"output": [
        dict(type="web_search_call"), dict(type="message", content=[
            dict(type="other"), dict(type="output_text", annotations=annotations)])]})


class NewsTests(unittest.TestCase):
    def test_citations_support_both_shapes_and_deduplicate_safe_urls(self):
        annotations = [dict(type="other"), dict(type="url_citation", url="http://insecure.example"),
                       dict(type="url_citation", url="https://example.org/one", title="One"),
                       dict(type="url_citation", url_citation=dict(url="https://example.org/one", title="Duplicate")),
                       dict(type="url_citation", url_citation=dict(url="https://example.org/two", title=""))]
        self.assertEqual(_citation_links(response(annotations=annotations)), [("One", "https://example.org/one"), ("Source", "https://example.org/two")])
        self.assertEqual(_citation_links(object()), [])

    def test_blank_and_background_requests_avoid_provider(self):
        with patch("finnie.news.OpenAI") as client:
            with self.assertRaises(ValueError):
                synthesize_financial_news(" ")
            self.assertIn("Finance Q&A", synthesize_financial_news("Explain ETFs vs mutual funds"))
            client.assert_not_called()

    def test_live_search_contract_citations_and_missing_evidence(self):
        with patch("finnie.news.OpenAI") as client, patch("finnie.news.get_settings", return_value={"model": "test-model"}), patch("finnie.news.date", wraps=date) as clock:
            clock.today.return_value = date(2027, 1, 1)
            for result, expected in ((response(), "Sources:"), (response(annotations=[]), "couldn't confirm")):
                client.return_value.responses.create.return_value = result
                answer = synthesize_financial_news("Latest US financial news")
                self.assertIn(expected, answer)
            client.return_value.responses.create.return_value = response()
            answer = synthesize_financial_news("Latest Fed news")
            self.assertIn("Primary \\[release\\]", answer)
            arguments = client.return_value.responses.create.call_args.kwargs
            self.assertEqual(arguments["tool_choice"], "required")
            self.assertEqual(arguments["tools"][0]["type"], "web_search")
            self.assertIn("2027-01-01", arguments["input"])
            self.assertIn("Latest Fed news", arguments["input"])
            client.return_value.responses.create.return_value = response(text=" ")
            with self.assertRaises(NewsSearchError):
                synthesize_financial_news("Latest news")
            client.return_value.responses.create.side_effect = OpenAIError("offline")
            with self.assertRaises(NewsSearchError):
                synthesize_financial_news("Latest news")

    def test_broad_topics_search_and_provider_citations_are_not_rewritten(self):
        rolling = "https://www.bls.gov/news.release/empsit.nr0.htm"
        with patch("finnie.news.date", wraps=date) as clock, patch("finnie.news.OpenAI") as client, patch("finnie.news.get_settings", return_value={"model": "test-model"}):
            clock.today.return_value = date(2026, 11, 5)
            client.return_value.responses.create.return_value = response(
                text="A test release with its actual provider link.",
                annotations=[dict(type="url_citation", title="2026 M09 Results", url=rolling)])
            answer = synthesize_financial_news("recent news about mutual funds")
            client.assert_called_once()
            self.assertIn(rolling, answer)
            self.assertNotIn("empsit_10022026", answer)
            self.assertNotIn("$32.70 trillion", answer)
            self.assertIn("last 30 days", client.return_value.responses.create.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
