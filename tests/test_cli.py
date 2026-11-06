"""Exercise CLI input validation and multi-turn dispatch without external APIs."""

from contextlib import redirect_stdout
from io import StringIO
import json
import unittest
from unittest.mock import patch

from finnie.app import main


class CliTests(unittest.TestCase):
    def test_blank_invalid_json_commands_history_and_quit(self):
        valid_portfolio = json.dumps([dict(symbol="VTI", quantity=1, price=100, asset_type="ETF")])
        valid_goal = json.dumps(dict(target_amount=20000, current_savings=5000, years=5, annual_return=.05))
        entries = ["", "portfolio invalid", "portfolio {}", "portfolio [1]", "goal invalid", "goal []", "news", "tax",
                   "portfolio " + valid_portfolio, "goal " + valid_goal, "market AAPL", "news Federal Reserve news",
                   "tax Explain a deduction", "Explain compounding", "quit"]
        snapshots = []
        def invoke(request):
            snapshots.append(dict(request, history=list(request["history"])))
            return dict(intent="test", answer="educational answer")
        output = StringIO()
        with patch("finnie.app.get_settings", return_value=dict(environment="test", provider="demo")), patch("finnie.app.build_workflow") as factory, patch("builtins.input", side_effect=entries), redirect_stdout(output):
            factory.return_value.invoke.side_effect = invoke
            main()
        factory.assert_called_once()
        self.assertEqual(len(snapshots), 6)
        self.assertEqual(snapshots[0]["portfolio"][0]["symbol"], "VTI")
        self.assertEqual(snapshots[1]["goal"]["years"], 5)
        self.assertEqual(snapshots[2]["market_symbol"], "AAPL")
        self.assertEqual(snapshots[3]["news_query"], "Federal Reserve news")
        self.assertEqual(snapshots[4]["tax_question"], "Explain a deduction")
        self.assertEqual(len(snapshots[-1]["history"]), 10)
        for fragment in ("Please enter", "JSON list", "JSON object", "topic after", "tax education question", "Goodbye!"):
            self.assertIn(fragment, output.getvalue())


if __name__ == "__main__":
    unittest.main()
