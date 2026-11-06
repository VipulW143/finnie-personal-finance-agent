"""Exercise specialist validation and safe provider failures in the real graph."""

import unittest
from unittest.mock import patch
from openai import OpenAIError

from finnie.news import NewsSearchError
from finnie.workflow import build_workflow


class WorkflowFailureTests(unittest.TestCase):
    def test_missing_and_invalid_calculation_inputs(self):
        cases = [({"portfolio": None}, "No portfolio"), ({"portfolio": []}, "Could not analyze"),
                 ({"goal": None}, "No goal"), ({"goal": {}}, "Could not calculate"),
                 ({"market_symbol": None}, "No ticker")]
        for fields, expected in cases:
            with self.subTest(fields=fields):
                self.assertIn(expected, build_workflow().invoke(dict(question="request", **fields))["answer"])

    def test_tax_and_finance_provider_failures_return_retry_messages(self):
        for fields, expected in (({}, "Finance education"), ({"tax_question": "Explain deductions"}, "Tax education")):
            with self.subTest(fields=fields), patch("finnie.workflow.load_knowledge_base", side_effect=OSError("offline")):
                result = build_workflow().invoke(dict(question="Explain", **fields))
            self.assertIn(expected, result["answer"])
            self.assertIn("temporarily unavailable", result["answer"])

    def test_tax_and_news_dispatch_and_news_failure(self):
        with patch("finnie.workflow.load_knowledge_base", return_value=[]), patch("finnie.workflow.answer_with_sources", return_value="General tax explanation.") as answer:
            result = build_workflow().invoke(dict(question="Tax", tax_question="Explain a deduction"))
        self.assertEqual(result["intent"], "tax_education")
        self.assertTrue(answer.call_args.kwargs["tax_education"])
        with patch("finnie.workflow.synthesize_financial_news", side_effect=NewsSearchError("offline")):
            result = build_workflow().invoke(dict(question="News", news_query="Latest news"))
        self.assertIn("Could not synthesize", result["answer"])


if __name__ == "__main__":
    unittest.main()
