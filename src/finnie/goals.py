"""Deterministic savings projections with explicit assumptions and risk context."""

from math import ceil, expm1, isfinite, log1p


RISK_LABELS = {
    "not_specified": "Not specified",
    "low": "Low comfort with investment losses",
    "moderate": "Moderate comfort with investment losses",
    "high": "High comfort with investment losses",
}
RISK_SOURCE = "https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance"


def _number(goal: dict[str, object], field: str) -> float:
    value = goal.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"'{field}' must be a number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"'{field}' must be a finite number") from error
    if not isfinite(number):
        raise ValueError(f"'{field}' must be a finite number")
    return number


def _factors(monthly_rate: float, months: int) -> tuple[float, float]:
    """Return growth and annuity factors without cancellation near zero rates."""
    if monthly_rate == 0:
        return 1.0, float(months)
    gain = expm1(months * log1p(monthly_rate))
    return 1 + gain, gain / monthly_rate


def _finite(value: float) -> float:
    if not isfinite(value):
        raise ValueError("projection exceeds numeric limits; use smaller amounts or assumptions")
    return value


def project_goal(goal: dict[str, object]) -> dict:
    """Return a report for text and charts; loss comfort never selects a rate.

    The comparison uses the same rounded monthly payment at 0% nominal return.
    Neither deterministic path models market fluctuations or probability.
    """
    if not isinstance(goal, dict):
        raise ValueError("provide goal details as an object")
    target = _number(goal, "target_amount")
    current = _number(goal, "current_savings")
    annual = _number(goal, "annual_return")
    years = goal.get("years")
    risk = goal.get("risk_tolerance", "not_specified")
    if target <= 0:
        raise ValueError("'target_amount' must be greater than zero")
    if current < 0:
        raise ValueError("'current_savings' cannot be negative")
    if isinstance(years, bool) or not isinstance(years, int):
        raise ValueError("'years' must be a whole number")
    if not 1 <= years <= 100:
        raise ValueError("'years' must be between 1 and 100")
    if not -0.99 < annual <= 1:
        raise ValueError("'annual_return' must be greater than -0.99 and at most 1")
    if not isinstance(risk, str) or risk not in RISK_LABELS:
        raise ValueError("'risk_tolerance' must be not_specified, low, moderate, or high")
    months = years * 12
    monthly_rate = annual / 12
    growth, annuity = _factors(monthly_rate, months)
    future_start = _finite(current * growth)
    required = max(0.0, (target - future_start) / annuity)
    # Upward cent rounding retains the existing conservative rounding convention.
    payment = ceil(_finite(required * 100)) / 100
    rows = []
    for month in range(months + 1):
        growth, annuity = _factors(monthly_rate, month)
        balance = _finite(current * growth + payment * annuity)
        cash = _finite(current + payment * month)
        rows.append({"month": month, "balance": balance, "zero_return_balance": cash,
                     "target": target, "modeled_growth": _finite(balance - cash)})
    projected = rows[-1]["balance"]
    zero_balance = rows[-1]["zero_return_balance"]
    risk_notes = {
        "not_specified": "No comfort-with-losses context was supplied; this projection does not assess risk tolerance.",
        "low": "You indicated low comfort with investment losses. A positive assumed return is not a promise that savings cannot decline.",
        "moderate": "You indicated moderate comfort with investment losses. This constant-rate model does not show the fluctuations you might experience.",
        "high": "You indicated high comfort with investment losses. Greater willingness to accept losses does not make an assumed return more likely or guaranteed.",
    }
    return dict(target_amount=target, current_savings=current, years=years, months=months,
                annual_return=annual, monthly_rate=monthly_rate, monthly_contribution=payment,
                projected_balance=projected, zero_return_balance=zero_balance,
                zero_return_gap=zero_balance-target, rows=rows,
                risk_tolerance=risk, risk_note=risk_notes[risk])


def calculate_monthly_contribution(goal: dict[str, object]) -> str:
    """Keep the public workflow entry point while formatting the shared report."""
    report = project_goal(goal)
    lines = [
        "Goal projection (educational estimate):",
        f"- Target: ${report['target_amount']:,.2f}",
        f"- Current savings: ${report['current_savings']:,.2f}",
        f"- Time horizon: {report['years']} years ({report['months']} months)",
        f"- Assumed annual return: {report['annual_return']:.2%}",
        (f"- Assumption: nominal annual rate divided by 12 ({report['monthly_rate']:.2%} monthly), "
         "with monthly compounding and contributions at each month end"),
    ]
    if report["monthly_contribution"] == 0:
        lines.append("Under these assumptions, the current savings are projected to meet or exceed the target without additional monthly contributions.")
    lines.extend([
        f"Estimated monthly contribution: ${report['monthly_contribution']:,.2f}",
        f"Projected balance at the end: ${report['projected_balance']:,.2f}",
        f"Same monthly contribution at 0% return: ${report['zero_return_balance']:,.2f}",
    ])
    gap = report["zero_return_gap"]
    if gap < 0:
        lines.append(f"- At 0%, the projected balance is ${-gap:,.2f} below the target.")
    else:
        lines.append(f"- At 0%, the projected balance meets or exceeds the target by ${gap:,.2f}.")
    lines.extend([
        f"- Comfort with losses: {RISK_LABELS[report['risk_tolerance']]}",
        report["risk_note"],
        "The loss-comfort answer does not change the rate or contribution. It is not a suitability assessment.",
        "Money needed soon has less time to recover from declines. Time horizon and ability to bear losses both matter.",
        "The 0% comparison is an illustration, not a guaranteed minimum or worst-case outcome. Actual balances can be lower.",
        "Actual returns vary and are not guaranteed; this estimate excludes taxes, fees, and inflation.",
        f"Risk education source: {RISK_SOURCE}",
    ])
    return "\n".join(lines)
