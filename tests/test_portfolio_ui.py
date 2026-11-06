"""Exercise portfolio forms, chart snapshots, invalid input, CSV flow, and reset."""

from io import BytesIO
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from finnie.portfolio_import import CSV_TEMPLATE


APP = Path(__file__).resolve().parents[1] / "src/finnie/ui.py"


def button(app, label):
    return next(item for item in app.button if item.label == label)


def radio(app, label):
    return next(item for item in app.radio if item.label == label)


class PortfolioUiTests(unittest.TestCase):
    def open_portfolio(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.sidebar.radio[0].set_value("Portfolio").run()
        self.assertFalse(app.exception)
        return app

    def test_manual_results_charts_error_and_reset(self):
        app = self.open_portfolio()
        app.text_input(key="portfolio_symbol_0").set_value("VTI")
        app.number_input(key="portfolio_quantity_0").set_value(5.)
        app.number_input(key="portfolio_price_0").set_value(250.)
        app.selectbox(key="portfolio_class_0").set_value("STOCKS")
        app.text_input(key="portfolio_ratio_0").set_value("0.03")
        app.text_input(key="portfolio_symbol_1").set_value("BND")
        app.number_input(key="portfolio_quantity_1").set_value(3.)
        app.number_input(key="portfolio_price_1").set_value(72.)
        app.text_input(key="portfolio_type_1").set_value("Bond ETF")
        app.selectbox(key="portfolio_class_1").set_value("BONDS")
        app.text_input(key="portfolio_ratio_1").set_value("0.03")
        button(app, "Analyze portfolio").click().run()
        self.assertFalse(app.exception)
        self.assertIn("$1,466.00", app.text[0].value)
        self.assertIn("$0.44", app.text[0].value)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        self.assertEqual(len(app.dataframe), 1)
        app.run()
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        app.text_input(key="portfolio_symbol_0").set_value("")
        button(app, "Analyze portfolio").click().run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        clear = next(b for b in app.button if "Clear conversation" in b.label)
        clear.click().run()
        self.assertFalse(app.error)
        self.assertFalse(app.exception)

    def test_csv_missing_file_success_and_invalid_replacement(self):
        app = self.open_portfolio()
        radio(app, "Holdings input").set_value("Upload CSV").run()
        button(app, "Analyze uploaded portfolio").click().run()
        self.assertIn("choose a CSV", app.error[0].value)
        # AppTest cannot select a browser file: inject the uploaded bytes at the widget boundary.
        with patch("finnie.portfolio_ui.st.file_uploader", return_value=BytesIO(CSV_TEMPLATE.encode())):
            button(app, "Analyze uploaded portfolio").click().run()
        self.assertFalse(app.exception)
        self.assertIn("$1,466.00", app.text[0].value)
        self.assertEqual(len(app.get("vega_lite_chart")), 2)
        bad = b'symbol,quantity,price,asset_type\nA,no,2,ETF'
        with patch("finnie.portfolio_ui.st.file_uploader", return_value=BytesIO(bad)):
            button(app, "Analyze uploaded portfolio").click().run()
        self.assertTrue(app.error)
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
