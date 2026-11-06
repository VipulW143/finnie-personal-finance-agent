"""Daily IEX history, explicit availability, and deterministic trend summaries."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from math import isfinite
import socket
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from finnie.config import get_alpaca_credentials
from finnie.market_data import CACHE_TTL, MarketDataError, _symbol_pattern, _timestamp, _utc_now


HISTORY_WINDOWS = (30, 90, 180)
_history_cache = {}


def _fetch_history(symbol, credentials, start, end):
    """Fetch every page; reject invalid or incomplete series rather than chart it."""
    bars = []
    token = None
    seen_tokens = set()
    for _ in range(5):
        query = dict(timeframe="1Day", start=start.isoformat(), end=end.isoformat(),
                     feed="iex", adjustment="split", sort="asc", limit=1000)
        if token:
            query["page_token"] = token
        request = Request(
            f"https://data.alpaca.markets/v2/stocks/{symbol}/bars?{urlencode(query)}",
            headers={"APCA-API-KEY-ID": credentials[0], "APCA-API-SECRET-KEY": credentials[1]},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            reason = ("Alpaca history rate limit was reached." if error.code == 429
                      else "Alpaca rejected history credentials or feed permission." if error.code in (401, 403)
                      else f"Alpaca returned HTTP {error.code} while requesting history.")
            error.close()
            raise MarketDataError(reason) from None
        except TimeoutError:
            raise MarketDataError("Alpaca history request timed out.") from None
        except URLError as error:
            reason = error.reason
            detail = ("DNS lookup failed" if isinstance(reason, socket.gaierror)
                      else "TLS connection failed" if isinstance(reason, ssl.SSLError)
                      else "request timed out" if isinstance(reason, TimeoutError)
                      else "network connection failed")
            raise MarketDataError(f"Alpaca history {detail}.") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise MarketDataError("Alpaca returned unreadable history data.") from None
        except OSError:
            raise MarketDataError("Alpaca history network I/O failed.") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("bars"), list):
            raise MarketDataError("Alpaca returned invalid history data.")
        bars.extend(payload["bars"])
        token = payload.get("next_page_token")
        if token is None:
            break
        if not isinstance(token, str) or not token or token in seen_tokens:
            raise MarketDataError("Alpaca returned invalid history pagination.")
        seen_tokens.add(token)
    else:
        raise MarketDataError("Alpaca history exceeded the pagination limit; no partial chart is shown.")
    if not bars:
        raise MarketDataError("Alpaca returned no daily bars in this window.")
    cleaned = []
    seen_dates = set()
    for bar in bars:
        try:
            raw_close = bar["c"]
            if isinstance(raw_close, bool) or not isinstance(raw_close, (float, int)):
                raise ValueError
            close = float(raw_close)
            at = datetime.fromisoformat(bar["t"].replace("Z", "+00:00"))
            if at.tzinfo is None or not isfinite(close) or close <= 0:
                raise ValueError
            at = at.astimezone(timezone.utc)
            # Exclude the current UTC day, even if the API includes its first bar.
            if at == end:
                continue
            if not start <= at < end or at.date() in seen_dates:
                raise ValueError
            seen_dates.add(at.date())
            cleaned.append({"date": at.date().isoformat(), "close": close})
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            raise MarketDataError("Alpaca returned invalid, duplicate, or out-of-window daily bars.") from None
    if not cleaned:
        raise MarketDataError("No completed daily bars were available in this window.")
    return sorted(cleaned, key=lambda bar: bar["date"])


def analyze_history(bars):
    """Describe the observed series; averages use observations, not calendar days."""
    closes = [bar["close"] for bar in bars]
    if not closes or any(isinstance(c, bool) or not isinstance(c, (int, float))
                         or not isfinite(c) or c <= 0 for c in closes):
        raise ValueError("history requires finite, positive closing prices")
    change = closes[-1] / closes[0] - 1 if len(closes) >= 2 else None
    if change is not None and not isfinite(change):
        raise ValueError("historical price change is outside numeric limits")
    rows = []
    peak = closes[0]
    drawdown = 0.0
    for index, bar in enumerate(bars):
        peak = max(peak, bar["close"])
        drawdown = min(drawdown, bar["close"] / peak - 1)
        # Divide first to avoid overflow when summing large but finite prices.
        average = sum(c / 20 for c in closes[index - 19:index + 1]) if index >= 19 else None
        rows.append(dict(bar, sma20=average))
    return dict(rows=rows, observations=len(rows), price_change=change,
                sma20=rows[-1]["sma20"], max_drawdown=drawdown,
                highest_close=max(closes), lowest_close=min(closes))


def get_market_history(symbol, days=90):
    """Return fresh/cached/stale observed history, or unavailable with no fake bars."""
    if not isinstance(symbol, str) or not _symbol_pattern.fullmatch(symbol.strip().upper()):
        raise ValueError("use a valid ticker symbol of 1 to 15 letters or numbers")
    if isinstance(days, bool) or not isinstance(days, int) or days not in HISTORY_WINDOWS:
        raise ValueError("history window must be 30, 90, or 180 calendar days")
    symbol = symbol.strip().upper()
    now = _utc_now()
    end = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
    key = (symbol, days)
    cached = _history_cache.get(key)
    if cached and cached["requested_end"] == end.isoformat() and timedelta(0) <= now - cached["retrieved_at"] < CACHE_TTL:
        result = deepcopy(cached)
        result.update(status="cached", data_label="Cached IEX daily history (30-minute cache window)")
        return result
    credentials = get_alpaca_credentials()
    try:
        if not credentials:
            raise MarketDataError("Alpaca key ID and secret are not both configured.")
        bars = _fetch_history(symbol, credentials, start, end)
        analysis = analyze_history(bars)
    except (MarketDataError, ValueError) as error:
        if cached:
            result = deepcopy(cached)
            result.update(status="stale", data_label=f"STALE cached IEX daily history. {error}")
            return result
        return dict(symbol=symbol, days=days, status="unavailable", bars=[], analysis=None,
                    requested_start=start.isoformat(), requested_end=end.isoformat(),
                    retrieved_at=None, data_label=str(error))
    result = dict(symbol=symbol, days=days, status="provider", bars=bars, analysis=analysis,
                  requested_start=start.isoformat(), requested_end=end.isoformat(),
                  retrieved_at=now, data_label="Alpaca historical daily bars from the IEX feed")
    _history_cache[key] = deepcopy(result)
    return result


def format_market_history(history):
    """Include provenance, actual date span, and the limits of each metric."""
    if history["status"] == "unavailable":
        return f"Daily price history unavailable: {history['data_label']} No historical chart or trend was fabricated."
    analysis = history["analysis"]
    bars = history["bars"]
    lines = [f"Daily price history for {history['symbol']} ({history['days']}-calendar-day request):",
             f"- Observed dates: {bars[0]['date']} to {bars[-1]['date']} ({len(bars)} observations)",
             f"- Data freshness: {history['data_label']}",
             f"- Retrieved: {_timestamp(history['retrieved_at'])}"]
    if analysis["price_change"] is None:
        lines.append("- Observed close-to-close change: unavailable; at least two observations required")
    else:
        lines.append(f"- Observed close-to-close change: {analysis['price_change']:+.2%}")
    average = analysis["sma20"]
    if average is None:
        lines.append("- 20-observation moving average: unavailable; at least 20 observations required")
    else:
        relationship = "above" if bars[-1]["close"] > average else "below" if bars[-1]["close"] < average else "equal to"
        lines.append(f"- 20-observation moving average: ${average:,.2f}; latest daily close is {relationship} this average")
    lines.extend([f"- Highest / lowest observed close: ${analysis['highest_close']:,.2f} / ${analysis['lowest_close']:,.2f}",
                  f"- Maximum observed closing-price drawdown: {analysis['max_drawdown']:.2%}",
                  "Split-adjusted IEX daily closes; current UTC day excluded. IEX is one exchange, not the consolidated US market.",
                  "Price change excludes dividends and is not total return. Missing dates are not filled; drawdown covers only the observed window.",
                  "Historical descriptions are not forecasts, risk ratings, or buy/sell recommendations."])
    return "\n".join(lines)
