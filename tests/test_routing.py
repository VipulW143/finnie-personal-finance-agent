"""Routing validation, topic changes, context limits, and safe clarification."""

import json
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from openai import OpenAIError

from finnie.routing import resolve_request
from finnie.workflow import build_workflow


class RoutingTests(unittest.TestCase):
    def test_history_is_only_forwarded_for_references_and_is_bounded(self):
        history = [dict(role="assistant", content="prior tax answer "*500) for _ in range(15)]
        decision = dict(intent="finance_qa", question="Explain compounding", payload=None)
        with patch("finnie.routing.ask_model", return_value=json.dumps(decision)) as model:
            resolve_request("Explain compounding", history)
            payload = json.loads(model.call_args.args[0].split("CONVERSATION AND REQUEST:\n")[1])
            self.assertEqual(payload["history"], [])
            resolve_request("How does that work?", history)
            payload = json.loads(model.call_args.args[0].split("CONVERSATION AND REQUEST:\n")[1])
            self.assertEqual(len(payload["history"]), 12)
            self.assertTrue(all(len(t["content"]) <= 3000 for t in payload["history"]))

    def test_six_specialist_payloads_and_fenced_json(self):
        cases = [
            ("finance_qa", None, "question"), ("tax_education", None, "tax_question"),
            ("news_synthesis", None, "news_query"), ("market_analysis", {"market_symbol": "AAPL"}, "market_symbol"),
            ("portfolio_analysis", {"portfolio": []}, "portfolio"),
            ("goal_planning", {"goal": {"target_amount": 20000, "current_savings": 5000, "years": 5, "annual_return": .05, "risk_tolerance": "low"}}, "goal"),
            ("clarification", None, "answer"),
        ]
        for intent, payload, key in cases:
            decision = dict(intent=intent, question="A self-contained request", payload=payload, answer="Which amount?")
            with self.subTest(intent=intent), patch("finnie.routing.ask_model", return_value="```json\n"+json.dumps(decision)+"\n```"):
                result = resolve_request("Goal inputs: target 20000, saved 5000, 5 years at 5% return" if intent == "goal_planning" else "request", [])
            self.assertEqual(result["intent"], intent)
            self.assertIn(key, result)

    def test_malformed_routes_and_provider_errors_request_clarification(self):
        invalid = ["bad JSON", "[]", "null", "```", *[json.dumps(data) for data in (
            dict(intent="unknown", question="q"), dict(intent="finance_qa", question=" "),
            dict(intent="market_analysis", question="q", payload={"market_symbol": 5}),
            dict(intent="goal_planning", question="q", payload={"goal": []}),
            dict(intent="portfolio_analysis", question="q", payload={"portfolio": [1]}),
            dict(intent="clarification", question="q", answer=""),
        )]]
        for raw in invalid:
            with self.subTest(raw=raw), patch("finnie.routing.ask_model", return_value=raw):
                self.assertEqual(resolve_request("q", [])["intent"], "clarification")
        with patch("finnie.routing.ask_model", side_effect=OpenAIError("offline")):
            self.assertEqual(resolve_request("q", [])["intent"], "clarification")

    def test_model_cannot_supply_default_goal_numbers_without_user_context(self):
        decision = dict(intent="goal_planning", question="Calculate a goal", payload={"goal": {
            "target_amount": 10000, "current_savings": 0, "years": 5, "annual_return": .05}})
        with patch("finnie.routing.ask_model", return_value=json.dumps(decision)):
            result = resolve_request("How much should I save monthly for my goal?", [])
            self.assertEqual(result["intent"], "clarification")
            for field in ("target amount", "current savings", "time horizon", "assumed annual return"):
                self.assertIn(field, result["answer"])
            self.assertNotIn("couldn't route", result["answer"])
            result = resolve_request("Do that calculation", [{"role": "assistant", "content": "For example: target 10000, savings 0, 5 years, 5%."}])
            self.assertEqual(result["intent"], "clarification")
            supplied = [{"role": "user", "content": "My target is 10000, savings 0, horizon 5 years, assumed return 5%."}]
            self.assertEqual(resolve_request("Calculate that goal", supplied)["intent"], "goal_planning")
            self.assertEqual(resolve_request("Target ten thousand, savings zero, five years at five percent", [])["intent"], "goal_planning")

    def test_incomplete_goal_payload_requests_clarification(self):
        decision = dict(intent="goal_planning", question="Calculate a goal", payload={"goal": {
            "target_amount": 20000, "current_savings": 5000, "years": 5}})
        with patch("finnie.routing.ask_model", return_value=json.dumps(decision)):
            result = resolve_request("Target 20000, saved 5000, five years", [])
        self.assertEqual(result["intent"], "clarification")
        self.assertIn("missing goal details: assumed annual return", result["answer"])

    def test_goal_validation_errors_explain_required_inputs(self):
        valid = dict(target_amount=20000, current_savings=5000, years=5, annual_return=.05)
        for payload in (None, {}, {"goal": []}, {"goal": dict(valid, years=0)}):
            with self.subTest(payload=payload), patch("finnie.routing.ask_model", return_value=json.dumps(
                dict(intent="goal_planning", question="Calculate my goal", payload=payload))):
                result = resolve_request("Target 20000, saved 5000, 5 years, assumed 5% return", [])
            self.assertEqual(result["intent"], "clarification")
            self.assertIn("target amount", result["answer"])
            self.assertIn("assumed annual return", result["answer"])

    def test_graph_returns_actionable_goal_clarification_without_calculating(self):
        invented = dict(intent="goal_planning", question="Calculate a goal", payload={"goal": {
            "target_amount": 10000, "current_savings": 0, "years": 5, "annual_return": .05}})
        with patch("finnie.routing.ask_model", return_value=json.dumps(invented)), patch("finnie.workflow.calculate_monthly_contribution") as calculator:
            result = build_workflow().invoke({"question": "How much should I save monthly for my goal?", "auto_route": True})
        self.assertEqual(result["intent"], "clarification")
        self.assertIn("please provide your target amount", result["answer"])
        calculator.assert_not_called()

    def test_explicit_quote_overrides_tax_context_without_router_call(self):
        history = [dict(role="user", content="Explain traditional 401(k)")]
        quote = dict(symbol="AAPL", price=1, trade_at="test", retrieved_at=datetime.now(timezone.utc), data_label="mock test")
        with patch("finnie.workflow.resolve_request") as router, patch("finnie.workflow.get_market_quote", return_value=quote):
            result = build_workflow().invoke(dict(question="Get the latest trade for AAPL", history=history, auto_route=True))
        router.assert_not_called()
        self.assertEqual(result["intent"], "market_analysis")


if __name__ == "__main__":
    unittest.main()
