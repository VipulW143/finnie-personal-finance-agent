"""Alpaca latest-trade lookup with a short cache and explicit fallbacks."""

import json
import re
import socket
import ssl
from datetime import datetime, timedelta, timezone
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from finnie.config import get_alpaca_credentials


CACHE_TTL = timedelta(minutes=30)
_quote_cache: dict[str, dict[str, object]] = {}
_symbol_pattern = re.compile(r"^[A-Z0-9.^=-]{1,15}$")


class MarketDataError(Exception):
    """An expected provider failure with a safe, short explanation."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")


def _fetch_alpaca_trade(
    symbol: str, credentials: tuple[str, str]
) -> dict[str, object]:
    key_id, secret_key = credentials
    query = urlencode({"feed": "iex"})
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/trades/latest?{query}"
    headers = {
        "APCA-API-KEY-ID": key_id,
        "APCA-API-SECRET-KEY": secret_key,
    }
    try:
        request = Request(url, headers=headers)
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        error.close()
        if error.code == 429:
            raise MarketDataError(
                "Alpaca's market-data rate limit was reached."
            ) from None
        if error.code in (401, 403):
            raise MarketDataError(
                "Alpaca rejected the credentials or data-feed permission."
            ) from None
        raise MarketDataError(
            f"Alpaca returned HTTP {error.code} while requesting the trade."
        ) from None
    except TimeoutError:
        raise MarketDataError("The Alpaca request timed out.") from None
    except URLError as error:
        reason = error.reason
        if isinstance(reason, socket.gaierror):
            detail = "DNS lookup failed"
        elif isinstance(reason, ssl.SSLError):
            detail = "TLS connection failed"
        elif isinstance(reason, TimeoutError):
            detail = "request timed out"
        else:
            detail = "network connection failed"
        raise MarketDataError(f"Alpaca {detail}.") from None
    except json.JSONDecodeError:
        raise MarketDataError("Alpaca returned a non-JSON response.") from None
    except UnicodeDecodeError:
        raise MarketDataError("Alpaca returned text in an unexpected encoding.") from None
    except OSError as error:
        # Report only the exception type; never echo request URLs or credentials.
        raise MarketDataError(
            f"Alpaca network I/O failed ({type(error).__name__})."
        ) from None

    if not isinstance(payload, dict):
        raise MarketDataError("Alpaca returned an invalid response.")

    trade = payload.get("trade")
    if not isinstance(trade, dict) or not trade:
        raise MarketDataError("Alpaca returned no trade for that symbol.")

    try:
        if isinstance(trade["p"], bool) or not isinstance(trade["p"], (int, float)):
            raise ValueError
        price = float(trade["p"])
        trade_at = trade["t"]
        if not isinstance(trade_at, str):
            raise ValueError
        parsed_at = datetime.fromisoformat(trade_at.replace("Z", "+00:00"))
        if parsed_at.tzinfo is None:
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError):
        raise MarketDataError("Alpaca returned an incomplete trade.") from None
    if not isfinite(price) or price <= 0:
        raise MarketDataError("Alpaca returned an invalid trade price.")

    return {
        "symbol": symbol,
        "price": price,
        "trade_at": trade_at,
        "retrieved_at": _utc_now(),
        "data_label": "Alpaca latest trade from the IEX feed",
    }


def _mock_quote(symbol: str, reason: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "price": 100.0,
        "trade_at": "SIMULATED",
        "retrieved_at": _utc_now(),
        "data_label": f"SIMULATED MOCK DATA — not live. {reason}",
    }


def get_market_quote(symbol: str) -> dict[str, object]:
    """Return a quote, cached quote, stale cache, or clearly marked mock value."""
    if not isinstance(symbol, str):
        raise ValueError("use a valid ticker symbol of 1 to 15 letters or numbers")
    normalized_symbol = symbol.strip().upper()
    if not _symbol_pattern.fullmatch(normalized_symbol):
        raise ValueError("use a valid ticker symbol of 1 to 15 letters or numbers")

    now = _utc_now()
    cached_quote = _quote_cache.get(normalized_symbol)
    if cached_quote is not None:
        age = now - cached_quote["retrieved_at"]
        if timedelta(0) <= age < CACHE_TTL:
            fresh_copy = dict(cached_quote)
            fresh_copy["data_label"] = (
                f"Cached quote (retrieved {_timestamp(cached_quote['retrieved_at'])}; "
                "30-minute cache window)"
            )
            return fresh_copy

    credentials = get_alpaca_credentials()
    if not credentials:
        if cached_quote is not None:
            stale_copy = dict(cached_quote)
            stale_copy["data_label"] = (
                f"STALE cached quote (retrieved "
                f"{_timestamp(cached_quote['retrieved_at'])}); "
                "Alpaca key ID and secret are not both configured"
            )
            return stale_copy
        return _mock_quote(
            normalized_symbol, "Alpaca key ID and secret are not both configured."
        )

    try:
        quote = _fetch_alpaca_trade(normalized_symbol, credentials)
    except MarketDataError as error:
        if cached_quote is not None:
            stale_copy = dict(cached_quote)
            stale_copy["data_label"] = (
                f"STALE cached quote (retrieved "
                f"{_timestamp(cached_quote['retrieved_at'])}); {error}"
            )
            return stale_copy
        return _mock_quote(normalized_symbol, str(error))

    _quote_cache[normalized_symbol] = quote
    return dict(quote)


def format_market_quote(quote: dict[str, object]) -> str:
    """Format provider data while making simulated and cached data obvious."""
    symbol = str(quote["symbol"])
    price = float(quote["price"])
    trade_at = str(quote["trade_at"])
    retrieved_at = _timestamp(quote["retrieved_at"])
    label = str(quote["data_label"])

    return "\n".join(
        [
            f"Latest IEX trade for {symbol}:",
            f"- Trade price: ${price:,.2f}",
            f"- Trade timestamp: {trade_at}",
            f"- Data freshness: {label}",
            f"- Retrieved: {retrieved_at}",
            (
                "Feed: IEX (one exchange, not the consolidated US market). "
                "Market data only; not an investment recommendation."
            ),
        ]
    )
