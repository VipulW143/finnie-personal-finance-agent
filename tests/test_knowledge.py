"""Checks for catalog integrity and topic-constrained source retrieval."""

import unittest
from unittest.mock import patch

from finnie.knowledge import (
    ARTICLES_DIR, category_of, load_sources, load_glossary, search_glossary,
)
from finnie.rag import answer_with_sources


class KnowledgeTests(unittest.TestCase):
    def test_captured_sources_are_unique_and_readable(self):
        sources = load_sources()
        self.assertGreaterEqual(len(sources), 50)
        self.assertEqual(len({s["url"] for s in sources}), len(sources))
        self.assertEqual(len({s["file"] for s in sources}), len(sources))
        for source in sources:
            with self.subTest(source=source["title"]):
                self.assertTrue((ARTICLES_DIR / source["file"]).read_text().strip())
                self.assertTrue(source["checked_on"])
                self.assertTrue(source["url"].startswith("https://"))

    def test_glossary_definitions_link_to_captured_sources(self):
        entries = load_glossary()
        urls = {source["url"] for source in load_sources()}
        self.assertGreaterEqual(len(entries), 20)
        self.assertEqual(len({e["term"].casefold() for e in entries}), len(entries))
        for entry in entries:
            with self.subTest(term=entry["term"]):
                self.assertTrue(entry["definition"].strip())
                self.assertIn(entry["source_url"], urls)

    def test_glossary_search_combines_text_and_category(self):
        matches = search_glossary("  APR  ", "Credit")
        self.assertEqual([e["term"] for e in matches], ["Annual percentage rate (APR)"])
        self.assertEqual(search_glossary("APR", "Investing"), [])
        self.assertEqual(search_glossary("no-such-financial-term"), [])
        self.assertTrue(search_glossary("previously earned interest"))
        terms = [e["term"].casefold() for e in search_glossary("")]
        self.assertEqual(terms, sorted(terms))

    def test_detailed_topics_share_a_category(self):
        self.assertEqual(category_of("Tax education: Roth IRA"), "Tax education")
        self.assertEqual(category_of("Investing: fees"), "Investing")

    def test_filter_runs_before_semantic_search(self):
        saving = {"title": "Emergency fund", "topic": "Saving: emergency funds",
                  "publisher": "CFPB", "url": "https://example.org/saving", "text": "A reserve"}
        investing = dict(saving, topic="Investing", url="https://example.org/investing")
        with patch("finnie.rag.search_chunks", return_value=[saving]) as search, patch(
            "finnie.rag.ask_model", return_value="An emergency fund is a reserve [1]."
        ):
            result = answer_with_sources("What is a reserve?", [saving, investing], category="Saving")
        self.assertEqual(search.call_args.args[1], [saving])
        self.assertIn(saving["url"], result)
        self.assertNotIn(investing["url"], result)

    def test_empty_category_avoids_model_and_embedding_calls(self):
        with patch("finnie.rag.search_chunks") as search, patch("finnie.rag.ask_model") as model:
            result = answer_with_sources("Anything?", [], category="Saving")
        self.assertIn("No captured source passages", result)
        search.assert_not_called()
        model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
