"""History calculations, provider parsing, pagination, and explicit fallbacks."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import math
import socket
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from finnie import market_history as mh
from finnie.workflow import build_workflow


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
END = NOW.replace(hour=0)
START = END - timedelta(days=30)


def bars(prices):
    return [{"date": (START + timedelta(days=i)).date().isoformat(), "close": c}
            for i, c in enumerate(prices)]


def response(payload):
    return BytesIO(json.dumps(payload).encode())


class MarketHistoryTests(unittest.TestCase):
    def setUp(self):
        mh._history_cache.clear()

    def test_price_change_drawdown_and_moving_average(self):
        result = mh.analyze_history(bars([100, 120, 90, 60, 110]))
        self.assertAlmostEqual(result["price_change"], .1)
        self.assertAlmostEqual(result["max_drawdown"], -.5)
        self.assertEqual(result["highest_close"], 120)
        self.assertEqual(result["lowest_close"], 60)
        result = mh.analyze_history(bars(list(range(1, 22))))
        self.assertIsNone(result["rows"][18]["sma20"])
        self.assertAlmostEqual(result["rows"][19]["sma20"], 10.5)
        self.assertAlmostEqual(result["sma20"], 11.5)

    def test_short_history_and_invalid_prices(self):
        report = mh.analyze_history(bars([100]))
        self.assertIsNone(report["price_change"])
        self.assertIsNone(report["sma20"])
        self.assertEqual(report["max_drawdown"], 0)
        for data in ([], bars([0]), bars([-1]), bars([math.nan]), bars([math.inf]), bars([True])):
            with self.subTest(data=data), self.assertRaises(ValueError):
                mh.analyze_history(data)

    def test_pagination_sorting_and_query_contract(self):
        pages = [response({"bars": [{"t": "2026-10-08T04:00:00Z", "c": 102}], "next_page_token": "next"}),
                 response({"bars": [{"t": "2026-10-07T04:00:00Z", "c": 100}], "next_page_token": None})]
        with patch.object(mh, "urlopen", side_effect=pages) as fetch:
            result = mh._fetch_history("AAPL", ("test-id", "test-secret"), START, END)
        self.assertEqual([b["close"] for b in result], [100, 102])
        first = fetch.call_args_list[0].args[0].full_url
        second = fetch.call_args_list[1].args[0].full_url
        for fragment in ("timeframe=1Day", "feed=iex", "adjustment=split", "sort=asc", "start=", "end="):
            self.assertIn(fragment, first)
        self.assertIn("page_token=next", second)
        self.assertNotIn("test-secret", first)

    def test_invalid_duplicate_and_out_of_window_bars(self):
        good = {"t": "2026-10-07T04:00:00Z", "c": 100}
        cases = [[], [good, good], [dict(good, c=True)], [dict(good, c=0)],
                 [dict(good, c="100")], [dict(good, c=math.inf)],
                 [dict(good, t="2026-10-07")], [dict(good, t="2026-10-01T04:00:00Z")], [None]]
        for records in cases:
            with self.subTest(records=records), patch.object(mh, "urlopen", return_value=response({"bars": records})), self.assertRaises(mh.MarketDataError):
                mh._fetch_history("AAPL", ("id", "secret"), START, END)
        with patch.object(mh, "urlopen", return_value=response({"bars": [good, dict(good, t=END.isoformat())]})):
            self.assertEqual(len(mh._fetch_history("AAPL", ("id", "secret"), START, END)), 1)

    def test_bad_responses_and_repeated_page_token(self):
        for data in ([], {}, {"bars": None}, {"bars": [], "next_page_token": 3}):
            with self.subTest(data=data), patch.object(mh, "urlopen", return_value=response(data)), self.assertRaises(mh.MarketDataError):
                mh._fetch_history("A", ("id", "secret"), START, END)
        pages = [response({"bars": [], "next_page_token": "same"}) for _ in range(2)]
        with patch.object(mh, "urlopen", side_effect=pages), self.assertRaisesRegex(mh.MarketDataError, "pagination"):
            mh._fetch_history("A", ("id", "secret"), START, END)

    def test_safe_provider_errors(self):
        errors = [HTTPError("https://example.org", code, "provider secret detail", {}, None) for code in (429, 401, 403, 404)]
        errors += [URLError(socket.gaierror("secret detail")), TimeoutError(), OSError("secret detail")]
        for error in errors:
            with self.subTest(error=type(error)), patch.object(mh, "urlopen", side_effect=error), self.assertRaises(mh.MarketDataError) as caught:
                mh._fetch_history("A", ("id", "secret"), START, END)
            self.assertNotIn("secret", str(caught.exception))
        with patch.object(mh, "urlopen", return_value=BytesIO(b'not JSON')), self.assertRaises(mh.MarketDataError):
            mh._fetch_history("A", ("id", "secret"), START, END)

    def test_fresh_cache_stale_fallback_and_copy_isolation(self):
        with patch.object(mh, "_utc_now", return_value=NOW), patch.object(mh, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(mh, "_fetch_history", return_value=bars([100, 110])) as fetch:
            first = mh.get_market_history(" aapl ", 30)
            first["bars"][0]["close"] = 999
            second = mh.get_market_history("AAPL", 30)
            self.assertEqual(second["status"], "cached")
            self.assertEqual(second["bars"][0]["close"], 100)
            self.assertEqual(fetch.call_count, 1)
        with patch.object(mh, "_utc_now", return_value=NOW + timedelta(hours=1)), patch.object(mh, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(mh, "_fetch_history", side_effect=mh.MarketDataError("rate limit")):
            stale = mh.get_market_history("AAPL", 30)
        self.assertEqual(stale["status"], "stale")
        self.assertIn("rate limit", stale["data_label"])
        self.assertEqual(stale["retrieved_at"], NOW)
        self.assertEqual(stale["analysis"]["price_change"], second["analysis"]["price_change"])

    def test_cache_separates_windows_symbols_and_refreshes_at_day_boundary(self):
        with patch.object(mh, "_utc_now", return_value=NOW), patch.object(mh, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(mh, "_fetch_history", return_value=bars([100, 110])) as fetch:
            for symbol, days in (("AAPL", 30), ("AAPL", 90), ("MSFT", 30)):
                mh.get_market_history(symbol, days)
            self.assertEqual(fetch.call_count, 3)
        with patch.object(mh, "_utc_now", return_value=NOW + timedelta(days=1)), patch.object(mh, "get_alpaca_credentials", return_value=None):
            result = mh.get_market_history("AAPL", 30)
        self.assertEqual(result["status"], "stale")

    def test_unavailable_never_fabricates_bars(self):
        with patch.object(mh, "get_alpaca_credentials", return_value=None):
            result = mh.get_market_history("AAPL")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["bars"], [])
        self.assertIsNone(result["analysis"])
        self.assertIn("unavailable", mh.format_market_history(result))
        for symbol, days in (("", 30), ("bad symbol", 30), ("A", True), ("A", 90.), ("A", 10)):
            with self.subTest(symbol=symbol, days=days), self.assertRaises(ValueError):
                mh.get_market_history(symbol, days)

    def test_workflow_history_is_explicit_and_quote_only_does_not_fetch_it(self):
        quote = dict(symbol="AAPL", price=100, trade_at="2026-11-04T20:00:00Z", retrieved_at=NOW, data_label="test quote")
        with patch("finnie.workflow.get_market_quote", return_value=quote), patch("finnie.workflow.get_market_history") as history:
            graph = build_workflow()
            graph.invoke({"question": "Market", "market_symbol": "AAPL"})
            history.assert_not_called()
        with patch.object(mh, "get_alpaca_credentials", return_value=None):
            unavailable = mh.get_market_history("AAPL")
        with patch("finnie.workflow.get_market_quote", return_value=quote), patch("finnie.workflow.get_market_history", return_value=unavailable) as history:
            result = graph.invoke({"question": "Market", "market_symbol": "AAPL", "market_history_days": 90})
        self.assertEqual(result["intent"], "market_analysis")
        self.assertIn("$100.00", result["answer"])
        self.assertIn("history unavailable", result["answer"])
        history.assert_called_once_with("AAPL", 90)


if __name__ == "__main__":
    unittest.main()
