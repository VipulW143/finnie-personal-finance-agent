"""Market dashboard chart, fallback, persistence, and reset checks."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from finnie.market_history import analyze_history


APP = Path(__file__).resolve().parents[1] / "src/finnie/ui.py"
NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
QUOTE = dict(symbol="AAPL", price=125., trade_at="2026-11-04T20:00:00Z", retrieved_at=NOW, data_label="Test IEX quote")


def fixture(status="provider"):
    bars = [{"date": (NOW - timedelta(days=30-i)).date().isoformat(), "close": 100. + i} for i in range(25)]
    return dict(symbol="AAPL", days=90, bars=bars, analysis=analyze_history(bars), status=status,
                retrieved_at=NOW, data_label="STALE test history" if status == "stale" else "Test IEX history")


def submit(app):
    return next(b for b in app.button if b.label == "Get market overview").click().run()


class MarketUiTests(unittest.TestCase):
    def open_market(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.sidebar.radio[0].set_value("Market").run()
        self.assertFalse(app.exception)
        return app

    def test_chart_and_summary_persist_and_reset(self):
        app = self.open_market()
        with patch("finnie.workflow.get_market_quote", return_value=QUOTE), patch("finnie.workflow.get_market_history", return_value=fixture()) as history:
            submit(app)
        self.assertFalse(app.exception)
        history.assert_called_once_with("AAPL", 90)
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        self.assertEqual(len(app.dataframe), 1)
        self.assertIn("+24.00%", app.text[0].value)
        self.assertIn("$114.50", app.text[0].value)
        app.run()
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        next(b for b in app.button if "Clear conversation" in b.label).click().run()
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        self.assertFalse(app.text)

    def test_stale_unavailable_quote_only_and_invalid_replace_previous_chart(self):
        app = self.open_market()
        with patch("finnie.workflow.get_market_quote", return_value=QUOTE), patch("finnie.workflow.get_market_history", return_value=fixture("stale")):
            submit(app)
        self.assertTrue(any("stale cached history" in w.value for w in app.warning))
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        unavailable = dict(symbol="AAPL", status="unavailable", data_label="no bars", bars=[], analysis=None)
        with patch("finnie.workflow.get_market_quote", return_value=QUOTE), patch("finnie.workflow.get_market_history", return_value=unavailable):
            submit(app)
        self.assertIn("$125.00", app.text[0].value)
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        self.assertTrue(app.info)
        app.checkbox[0].uncheck()
        with patch("finnie.workflow.get_market_quote", return_value=QUOTE), patch("finnie.workflow.get_market_history") as history:
            submit(app)
        history.assert_not_called()
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        app.text_input[0].set_value("")
        submit(app)
        self.assertTrue(app.error)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
