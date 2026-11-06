"""Deterministic portfolio calculations shared by chat, CSV, and the dashboard."""

from collections import defaultdict
from math import isfinite
from typing import TypedDict


ASSET_CLASSES = ("STOCKS", "BONDS", "CASH", "OTHER", "UNKNOWN")


class Holding(TypedDict, total=False):
    symbol: str
    quantity: float
    price: float
    asset_type: str
    asset_class: str
    expense_ratio: float


def _positive_number(holding: dict[str, object], field: str, row: int) -> float:
    value = holding.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"holding {row}: '{field}' must be a number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"holding {row}: '{field}' must be finite") from error
    if not isfinite(number) or number <= 0:
        raise ValueError(f"holding {row}: '{field}' must be finite and greater than zero")
    return number


def analyze_portfolio(holdings: list[dict[str, object]]) -> dict:
    """Return validated values and position concentration, without model calls.

    Repeated symbols represent lots of the same instrument, not diversification.
    Asset classes are user labels, never inferred from ETF names or tickers.
    """
    if not isinstance(holdings, list) or not holdings:
        raise ValueError("provide at least one holding as a list")
    positions = {}
    value_by_asset_type = defaultdict(float)
    value_by_asset_class = defaultdict(float)
    known_fee_value = 0.0
    estimated_annual_fees = 0.0

    for row, holding in enumerate(holdings, start=1):
        if not isinstance(holding, dict):
            raise ValueError(f"holding {row}: each holding must be an object")
        for field in ("symbol", "asset_type"):
            if not isinstance(holding.get(field), str) or not holding[field].strip():
                raise ValueError(f"holding {row}: '{field}' must be a non-empty string")
        symbol = holding["symbol"].strip().upper()
        asset_type = holding["asset_type"].strip().upper()
        asset_class = holding.get("asset_class", "UNKNOWN")
        if not isinstance(asset_class, str) or asset_class.strip().upper() not in ASSET_CLASSES:
            raise ValueError(f"holding {row}: 'asset_class' must be one of {', '.join(ASSET_CLASSES)}")
        asset_class = asset_class.strip().upper()
        quantity = _positive_number(holding, "quantity", row)
        price = _positive_number(holding, "price", row)
        value = quantity * price
        if not isfinite(value) or value <= 0:
            raise ValueError(f"holding {row}: market value must be finite and greater than zero")
        if symbol in positions:
            previous = positions[symbol]
            if (previous["asset_type"], previous["asset_class"]) != (asset_type, asset_class):
                raise ValueError(f"holding {row}: repeated symbol {symbol} has conflicting asset labels")
            previous["market_value"] += value
        else:
            positions[symbol] = dict(symbol=symbol, asset_type=asset_type,
                                     asset_class=asset_class, market_value=value)
        value_by_asset_type[asset_type] += value
        value_by_asset_class[asset_class] += value
        if "expense_ratio" in holding:
            ratio = holding["expense_ratio"]
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
                raise ValueError(f"holding {row}: 'expense_ratio' must be a decimal number")
            try:
                ratio = float(ratio)
            except OverflowError as error:
                raise ValueError(f"holding {row}: 'expense_ratio' must be finite") from error
            if not isfinite(ratio) or not 0 <= ratio <= 1:
                raise ValueError(f"holding {row}: 'expense_ratio' must be between zero and one (decimal fraction)")
            known_fee_value += value
            estimated_annual_fees += value * ratio

    total = sum(p["market_value"] for p in positions.values())
    if not isfinite(total):
        raise ValueError("total market value must be finite")
    ordered = sorted(positions.values(), key=lambda p: (-p["market_value"], p["symbol"]))
    for position in ordered:
        position["weight"] = position["market_value"] / total
    concentration = sum(p["weight"] ** 2 for p in ordered)
    return dict(
        total_value=total, positions=ordered, input_rows=len(holdings),
        value_by_asset_type=dict(value_by_asset_type),
        value_by_asset_class=dict(value_by_asset_class),
        known_fee_value=known_fee_value, annual_fees=estimated_annual_fees,
        weighted_expense_ratio=estimated_annual_fees / known_fee_value if known_fee_value else None,
        concentration=concentration, effective_positions=1 / concentration,
    )


def summarize_portfolio(holdings: list[dict[str, object]]) -> str:
    """Format the same calculation report used by the Portfolio dashboard."""
    report = analyze_portfolio(holdings)
    total = report["total_value"]
    lines = ["Portfolio summary (based only on the holdings provided):",
             f"Total market value: ${total:,.2f}", "Allocation by asset type:"]
    for label, value in sorted(report["value_by_asset_type"].items()):
        lines.append(f"- {label}: ${value:,.2f} ({value / total:.1%})")
    lines.append("Allocation by supplied asset class (not inferred from fund names):")
    for label, value in sorted(report["value_by_asset_class"].items()):
        lines.append(f"- {label}: ${value:,.2f} ({value / total:.1%})")
    if report["known_fee_value"]:
        lines.extend([
            "Expense ratios (holdings with a supplied ratio):",
            f"- Value-weighted average: {report['weighted_expense_ratio']:.3%}",
            f"- Approximate annual fund expenses: ${report['annual_fees']:,.2f}",
            f"- Coverage: ${report['known_fee_value']:,.2f} of ${total:,.2f} in holdings",
        ])
    else:
        lines.append("Expense ratios: not calculated; none were supplied.")
    largest = report["positions"][0]
    largest_type, largest_value = max(report["value_by_asset_type"].items(), key=lambda item: item[1])
    lines.extend([
        "Diversification indicators (descriptive, not a rating):",
        f"- Holdings supplied: {report['input_rows']}",
        f"- Unique instruments: {len(report['positions'])}",
        f"- Asset types supplied: {len(report['value_by_asset_type'])}",
        f"- Largest holding: {largest['symbol']} ({largest['weight']:.1%})",
        f"- Largest asset type: {largest_type} ({largest_value / total:.1%})",
        f"- Position concentration (sum of squared weights): {report['concentration']:.3f}",
        f"- Effective equal-weight positions: {report['effective_positions']:.2f}",
        "Repeated symbols are combined before concentration is calculated.",
        "Concentration describes supplied positions, not underlying fund holdings or investment risk.",
        "Asset-type counts do not establish diversification; funds may hold overlapping assets.",
        "UNKNOWN asset classes remain unclassified. Prices and labels are user supplied.",
        "Historical volatility, correlations, and loss risk are not estimated from this snapshot.",
        "This summary does not assess suitability or recommend investment changes.",
    ])
    return "\n".join(lines)
