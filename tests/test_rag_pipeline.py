"""Full cache invalidation, source attribution, tax restriction, and abstention."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from finnie.rag import answer_with_sources, load_knowledge_base


def source(url="https://example.org/one", publisher="SEC"):
    return dict(title="Test source", url=url, publisher=publisher, topic="Investing", file="source.md")


def passage(url="https://example.org/one", publisher="SEC"):
    return dict(source(url, publisher), text="An educational fact", chunk_id="one")


class RagPipelineTests(unittest.TestCase):
    def test_loader_reuses_cache_and_rebuilds_after_source_or_model_changes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"articles").mkdir()
            doc = root/"articles/source.md"
            doc.write_text("A first educational paragraph.")
            path = root/"cache/index.json"
            with patch("finnie.rag.PROJECT_ROOT", root), patch("finnie.rag.INDEX_CACHE_PATH", path), patch("finnie.rag.load_sources", return_value=[source()]), patch("finnie.rag.get_settings", return_value={"embedding_model": "test-A"}) as settings, patch("finnie.retrieval.embed_texts", side_effect=lambda texts: [[1., 0.] for text in texts]) as embed:
                first = load_knowledge_base()
                self.assertEqual(len(first), 1)
                self.assertEqual(load_knowledge_base()[0]["text"], first[0]["text"])
                self.assertEqual(embed.call_count, 1)
                doc.write_text("A changed educational paragraph.")
                with self.assertRaisesRegex(ValueError, "No current saved"):
                    load_knowledge_base(allow_rebuild=False)
                self.assertEqual(embed.call_count, 1)
                self.assertIn("changed", load_knowledge_base()[0]["text"])
                self.assertEqual(embed.call_count, 2)
                settings.return_value = {"embedding_model": "test-B"}
                load_knowledge_base()
                self.assertEqual(embed.call_count, 3)
                legacy = json.loads(path.read_text())
                legacy["version"] = 1
                path.write_text(json.dumps(legacy))
                load_knowledge_base()
                self.assertEqual(embed.call_count, 3)
                self.assertEqual(json.loads(path.read_text())["version"], 2)

    def test_only_cited_sources_appear_and_duplicate_urls_are_grouped(self):
        matches = [passage(), passage("https://example.org/unused"), passage()]
        with patch("finnie.rag.search_chunks", return_value=matches), patch("finnie.rag.ask_model", return_value="An explanation [3], [1]."):
            answer = answer_with_sources("Explain", matches)
        self.assertIn("[3], [1] Test source", answer)
        self.assertEqual(answer.count("https://example.org/one"), 1)
        self.assertNotIn("https://example.org/unused", answer)

    def test_empty_search_and_empty_model_output_are_explicit(self):
        with patch("finnie.rag.search_chunks", return_value=[]), patch("finnie.rag.ask_model") as model:
            answer = answer_with_sources("Explain", [])
            model.assert_not_called()
        self.assertIn("don't have any indexed", answer)
        with patch("finnie.rag.search_chunks", return_value=[passage()]), patch("finnie.rag.ask_model", return_value=" "):
            self.assertIn("couldn't produce", answer_with_sources("Explain", [passage()]))

    def test_tax_retrieval_uses_only_irs_and_prior_answers_are_context(self):
        irs = passage("https://www.irs.gov/credits-and-deductions", "Internal Revenue Service (IRS)")
        with patch("finnie.rag.search_chunks", return_value=[irs]) as search, patch("finnie.rag.ask_model", return_value="A general rule [1].") as model:
            answer = answer_with_sources("Explain deductions", [passage(), irs], tax_education=True,
                history=[dict(role="assistant", content="Earlier answer.\nSources: old source list\nIRS guidance: old link")])
        self.assertEqual(search.call_args.args[1], [irs])
        self.assertIn("general U.S. federal", model.call_args.args[0])
        self.assertNotIn("old source list", model.call_args.args[0])
        self.assertIn("IRS guidance:", answer)

    def test_personal_401k_tax_bill_is_not_calculated_or_sent_to_model(self):
        irs = passage("https://www.irs.gov/retirement-plans/401k-plans", "Internal Revenue Service (IRS)")
        with patch("finnie.rag.search_chunks") as search, patch("finnie.rag.ask_model") as model:
            answer = answer_with_sources("Calculate exactly how much tax I owe after traditional 401(k) contributions", [irs], tax_education=True)
        self.assertIn("cannot calculate a personal tax bill", answer)
        self.assertIn("[1]", answer)
        self.assertIn(irs["url"], answer)
        search.assert_not_called()
        model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
