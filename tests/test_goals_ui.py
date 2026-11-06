"""Goal chart, context, persistence, zero-return overlap, and invalid/reset paths."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src/finnie/ui.py"


def number(app, label):
    return next(n for n in app.number_input if n.label == label)


def submit(app):
    return next(b for b in app.button if b.label == "Project savings goal").click().run()


class GoalsUiTests(unittest.TestCase):
    def open_goals(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.sidebar.radio[0].set_value("Goals").run()
        self.assertFalse(app.exception)
        return app

    def test_sample_context_chart_table_persistence_and_reset(self):
        app = self.open_goals()
        app.selectbox[0].set_value("low")
        submit(app)
        self.assertFalse(app.exception)
        self.assertIn("$199.74", app.text[0].value)
        self.assertIn("$16,984.40", app.text[0].value)
        self.assertIn("low comfort", app.text[0].value)
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        self.assertEqual(len(app.dataframe[0].value), 61)
        app.run()
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        next(b for b in app.button if "Clear conversation" in b.label).click().run()
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        self.assertFalse(app.text)

    def test_zero_return_and_invalid_replace_previous_chart(self):
        app = self.open_goals()
        number(app, "Assumed annual return (%)").set_value(0.)
        submit(app)
        self.assertFalse(app.exception)
        self.assertIn("$250.00", app.text[0].value)
        self.assertEqual(len(app.get("vega_lite_chart")), 1)
        table = app.dataframe[0].value
        self.assertTrue((table["Entered-rate balance ($)"] == table["Same contribution at 0% ($)"]).all())
        number(app, "Target amount ($)").set_value(0.)
        submit(app)
        self.assertTrue(app.error)
        self.assertEqual(len(app.get("vega_lite_chart")), 0)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
