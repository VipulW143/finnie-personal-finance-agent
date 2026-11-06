"""Regression checks for validated plans and sequential specialist execution."""

import json
import unittest
from unittest.mock import patch

from openai import OpenAIError

from finnie.routing import resolve_request
from finnie.workflow import build_workflow


def task(intent, question, payload=None):
    return {"intent": intent, "question": question, "payload": payload}


class MultiAgentTests(unittest.TestCase):
    def test_retirement_comparison_uses_tax_specialist(self):
        decision = task("finance_qa", "Explain traditional IRA vs Roth IRA.")
        with patch("finnie.routing.ask_model", return_value=json.dumps(decision)):
            result = resolve_request(decision["question"], [])
        self.assertEqual(result["intent"], "tax_education")
        self.assertEqual(result["tax_question"], decision["question"])

    def invoke(self, graph, tasks):
        plan = {"intent": "multi_agent", "tasks": tasks}
        with patch("finnie.routing.ask_model", return_value=json.dumps(plan)):
            return graph.invoke({"question": "Explain compounding and calculate for target 20000, saved 5000, 5 years, assumed 5% nominal return", "auto_route": True})

    def test_two_specialists_preserve_sources_and_calculation(self):
        tasks = [
            task("finance_qa", "Explain compounding"),
            task("goal_planning", "Project my savings", {"goal": {
                "target_amount": 20000, "current_savings": 5000,
                "years": 5, "annual_return": 0.05,
            }}),
        ]
        with patch("finnie.workflow.load_knowledge_base", return_value=[]), patch(
            "finnie.workflow.answer_with_sources",
            return_value="Compounding explanation [1].\nSources: [1] https://example.org",
        ):
            result = self.invoke(build_workflow(), tasks)
        self.assertEqual(result["intent"], "multi_agent")
        self.assertEqual(len(result["task_results"]), 2)
        self.assertIn("https://example.org", result["answer"])
        self.assertIn("$199.74", result["answer"])

    def test_three_tasks_clear_payloads_and_next_request_is_independent(self):
        tasks = [
            task("market_analysis", "Quote AAPL", {"market_symbol": "AAPL"}),
            task("tax_education", "Explain deductions"),
            task("finance_qa", "Explain compounding"),
        ]
        with patch("finnie.workflow.load_knowledge_base", return_value=[]), patch(
            "finnie.workflow.get_market_quote", return_value={}
        ), patch("finnie.workflow.format_market_quote", return_value="AAPL quote"), patch(
            "finnie.workflow.answer_with_sources", side_effect=["Tax answer", "Q&A answer", "Single answer"]
        ) as answer:
            graph = build_workflow()
            result = self.invoke(graph, tasks)
            self.assertEqual(
                [r["route"] for r in result["task_results"]],
                ["market_analysis", "tax_education", "finance_qa"],
            )
            self.assertEqual(answer.call_args_list[1].args[0], "Explain compounding")
            single = graph.invoke({"question": "New standalone question"})
            self.assertEqual(single["intent"], "finance_qa")
            self.assertEqual(single["answer"], "Single answer")
            self.assertFalse(single.get("tasks"))

    def test_source_api_failure_preserves_other_task_result(self):
        with patch("finnie.workflow.load_knowledge_base", return_value=[]), patch(
            "finnie.workflow.answer_with_sources", side_effect=OpenAIError("unavailable")
        ), patch("finnie.workflow.get_market_quote", return_value={}), patch(
            "finnie.workflow.format_market_quote", return_value="AAPL quote"
        ):
            result = self.invoke(build_workflow(), [
                task("tax_education", "Explain deductions"),
                task("market_analysis", "Quote AAPL", {"market_symbol": "AAPL"}),
            ])
        self.assertIn("temporarily unavailable", result["answer"])
        self.assertIn("AAPL quote", result["answer"])

    def test_invalid_or_nested_plans_ask_for_clarification(self):
        for tasks in (
            [task("finance_qa", "one")],
            [task("finance_qa", "one")] * 4,
            [task("multi_agent", "nested"), task("finance_qa", "one")],
            [task("goal_planning", "missing payload"), task("finance_qa", "one")],
        ):
            with self.subTest(tasks=tasks), patch(
                "finnie.routing.ask_model",
                return_value=json.dumps({"intent": "multi_agent", "tasks": tasks}),
            ):
                self.assertEqual(resolve_request("request", [])["intent"], "clarification")


if __name__ == "__main__":
    unittest.main()
