"""Latest-trade provider validation, cache isolation, and labeled fallbacks."""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import socket
import ssl
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from finnie import market_data as md

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
TRADE = {"trade": {"p": 123.45, "t": "2026-11-04T21:00:00.123456789Z"}}


def response(payload):
    return BytesIO(json.dumps(payload).encode())


def quote(symbol="AAPL"):
    return dict(symbol=symbol, price=123.45, trade_at=TRADE["trade"]["t"], retrieved_at=NOW, data_label="IEX provider")


class MarketQuoteTests(unittest.TestCase):
    def setUp(self):
        md._quote_cache.clear()

    def test_provider_accepts_real_trade_and_rejects_invalid_prices_or_dates(self):
        with patch.object(md, "urlopen", return_value=response(TRADE)):
            result = md._fetch_alpaca_trade("AAPL", ("test-id", "test-secret"))
        self.assertEqual(result["price"], 123.45)
        self.assertIn("IEX", md.format_market_quote(result))
        invalid = [[], {}, {"trade": []}, {"trade": {"p": 1}},
                   *[{"trade": dict(TRADE["trade"], p=p)} for p in (True, 0, -1, "123", float("nan"), float("inf"))],
                   *[{"trade": dict(TRADE["trade"], t=t)} for t in (None, "bad", "2026-11-04")]]
        for payload in invalid:
            with self.subTest(payload=payload), patch.object(md, "urlopen", return_value=response(payload)), self.assertRaises(md.MarketDataError):
                md._fetch_alpaca_trade("AAPL", ("test-id", "test-secret"))

    def test_safe_transport_and_decoding_errors(self):
        errors = [HTTPError("https://example.org", code, "private provider body", {}, None) for code in (429, 401, 403, 404)]
        errors += [URLError(socket.gaierror()), URLError(ssl.SSLError()), URLError(TimeoutError()), URLError("private detail"), TimeoutError(), OSError("private detail")]
        for error in errors:
            with self.subTest(error=type(error)), patch.object(md, "urlopen", side_effect=error), self.assertRaises(md.MarketDataError) as caught:
                md._fetch_alpaca_trade("AAPL", ("test-id", "test-secret"))
            self.assertNotIn("private", str(caught.exception))
            self.assertNotIn("test-secret", str(caught.exception))
        for raw in (b'not json', b'\xff'):
            with patch.object(md, "urlopen", return_value=BytesIO(raw)), self.assertRaises(md.MarketDataError):
                md._fetch_alpaca_trade("AAPL", ("id", "secret"))

    def test_fresh_cache_and_symbols_are_independent(self):
        with patch.object(md, "_utc_now", return_value=NOW), patch.object(md, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(md, "_fetch_alpaca_trade", side_effect=lambda symbol, _: quote(symbol)) as fetch:
            first = md.get_market_quote(" aapl ")
            first["price"] = 0
            cached = md.get_market_quote("AAPL")
            self.assertEqual(cached["price"], 123.45)
            self.assertIn("Cached quote", cached["data_label"])
            md.get_market_quote("MSFT")
            self.assertEqual(fetch.call_count, 2)

    def test_missing_keys_provider_failure_and_stale_data_are_labeled(self):
        with patch.object(md, "get_alpaca_credentials", return_value=None):
            mock = md.get_market_quote("AAPL")
        self.assertIn("SIMULATED MOCK DATA", mock["data_label"])
        self.assertEqual(mock["trade_at"], "SIMULATED")
        with patch.object(md, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(md, "_fetch_alpaca_trade", side_effect=md.MarketDataError("rate limit")):
            self.assertIn("rate limit", md.get_market_quote("AAPL")["data_label"])
        md._quote_cache["AAPL"] = quote()
        with patch.object(md, "_utc_now", return_value=NOW + timedelta(hours=1)), patch.object(md, "get_alpaca_credentials", return_value=None):
            stale = md.get_market_quote("AAPL")
        self.assertIn("STALE", stale["data_label"])
        self.assertEqual(stale["retrieved_at"], NOW)
        with patch.object(md, "_utc_now", return_value=NOW + timedelta(hours=1)), patch.object(md, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(md, "_fetch_alpaca_trade", side_effect=md.MarketDataError("rate limit")):
            self.assertIn("STALE", md.get_market_quote("AAPL")["data_label"])
        for symbol in ("", "not a symbol", None):
            with self.assertRaises(ValueError):
                md.get_market_quote(symbol)

    def test_future_dated_cache_is_not_treated_as_fresh(self):
        md._quote_cache["AAPL"] = dict(quote(), retrieved_at=NOW + timedelta(hours=1))
        with patch.object(md, "_utc_now", return_value=NOW), patch.object(md, "get_alpaca_credentials", return_value=("id", "secret")), patch.object(md, "_fetch_alpaca_trade", return_value=quote()) as fetch:
            md.get_market_quote("AAPL")
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
