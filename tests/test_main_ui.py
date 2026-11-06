"""Shared chat, source browsing, news, and tax UI state/dispatch checks."""

from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "src/finnie/ui.py"


class MainUiTests(unittest.TestCase):
    def test_chat_and_topic_filtered_qa_send_separate_history(self):
        workflow = Mock()
        workflow.invoke.return_value = dict(intent="finance_qa", answer="A source-backed example costs $100 [1].")
        with patch("finnie.workflow.build_workflow", return_value=workflow):
            app = AppTest.from_file(str(APP), default_timeout=20).run()
            app.chat_input[0].set_value("Explain budgeting").run()
            self.assertTrue(workflow.invoke.call_args.args[0]["auto_route"])
            app.chat_input[0].set_value("How does that work?").run()
            self.assertEqual(len(workflow.invoke.call_args.args[0]["history"]), 2)
            app.run()
            self.assertTrue(any("\\$100" in m.value for m in app.markdown))
            app.sidebar.radio[0].set_value("Finance Q&A").run()
            app.selectbox(key="qa_category").set_value("Saving")
            app.chat_input[0].set_value("Explain emergency savings").run()
            request = workflow.invoke.call_args.args[0]
            self.assertFalse(request["auto_route"])
            self.assertEqual(request["category"], "Saving")
            self.assertEqual(request["history"], [])
            self.assertFalse(app.exception)

    def test_tax_view_can_change_topics_and_reset_history(self):
        workflow = Mock()
        workflow.invoke.return_value = dict(intent="tax_education", answer="A general tax explanation.")
        with patch("finnie.workflow.build_workflow", return_value=workflow):
            app = AppTest.from_file(str(APP), default_timeout=20).run()
            app.sidebar.radio[0].set_value("Tax Education").run()
            app.chat_input[0].set_value("Explain traditional 401(k)").run()
            app.run()
            workflow.invoke.return_value = dict(intent="market_analysis", answer="A test market response.")
            app.chat_input[0].set_value("Get the latest trade for AAPL").run()
            request = workflow.invoke.call_args.args[0]
            self.assertTrue(request["auto_route"])
            self.assertEqual(len(request["history"]), 2)
            self.assertTrue(any("market_analysis" in c.value for c in app.caption))
            next(b for b in app.button if "Clear conversation" in b.label).click().run()
            self.assertEqual(app.session_state["tax_messages"], [])
            self.assertFalse(app.exception)

    def test_news_blank_success_and_error_display(self):
        workflow = Mock()
        workflow.invoke.return_value = dict(intent="news_synthesis", answer="A test release.\nSources: https://example.org/release")
        with patch("finnie.workflow.build_workflow", return_value=workflow):
            app = AppTest.from_file(str(APP), default_timeout=20).run()
            app.sidebar.radio[0].set_value("News").run()
            submit = lambda: next(b for b in app.button if b.label == "Search and summarize").click().run()
            submit()
            self.assertTrue(app.error)
            workflow.invoke.assert_not_called()
            app.text_input[0].set_value("Latest US financial news")
            submit()
            self.assertEqual(workflow.invoke.call_args.args[0]["news_query"], "Latest US financial news")
            self.assertTrue(any("test release" in m.value for m in app.markdown))
            workflow.invoke.return_value = dict(intent="news_synthesis", answer="Could not synthesize current news: offline")
            submit()
            self.assertTrue(any("offline" in e.value for e in app.error))
            self.assertFalse(app.exception)

    def test_knowledge_source_count_search_category_and_glossary(self):
        app = AppTest.from_file(str(APP), default_timeout=20).run()
        app.sidebar.radio[0].set_value("Knowledge").run()
        self.assertTrue(any("50 captured" in c.value for c in app.caption))
        app.selectbox(key="knowledge_category").set_value("Saving")
        app.text_input[0].set_value("emergency").run()
        self.assertEqual(len(app.expander), 1)
        app.text_input[0].set_value("no-such-source").run()
        self.assertTrue(app.info)
        next(r for r in app.radio if r.label == "Browse").set_value("Glossary").run()
        app.text_input(key="glossary_search").set_value("APR").run()
        self.assertEqual(len(app.expander), 1)
        app.selectbox(key="glossary_category").set_value("Investing").run()
        self.assertFalse(app.expander)
        self.assertTrue(app.info)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
