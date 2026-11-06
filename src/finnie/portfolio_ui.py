"""Portfolio inputs and visualizations for the Streamlit dashboard."""

from math import isfinite

import streamlit as st

from finnie.portfolio import ASSET_CLASSES, analyze_portfolio
from finnie.portfolio_import import CSV_TEMPLATE, parse_holdings_csv


def _manual_form() -> list[dict] | None:
    count = st.slider("Number of holdings", min_value=1, max_value=10, value=2)
    st.caption(
        "Expense ratios here are percentages: enter 0.03 for 0.03%, or leave blank "
        "if unknown. Asset class is optional; ETF is a structure, not an asset class."
    )
    holdings = []
    ratios = []
    with st.form("portfolio_form"):
        for index in range(count):
            st.markdown(f"**Holding {index + 1}**")
            symbol_col, quantity_col, price_col, type_col = st.columns(4)
            holding = {
                "symbol": symbol_col.text_input("Ticker / name", key=f"portfolio_symbol_{index}"),
                "quantity": quantity_col.number_input("Quantity", min_value=0.0, value=1.0,
                    step=1.0, key=f"portfolio_quantity_{index}"),
                "price": price_col.number_input("Price per unit ($)", min_value=0.0,
                    value=0.0, step=1.0, key=f"portfolio_price_{index}"),
                "asset_type": type_col.text_input("Asset type", value="ETF", key=f"portfolio_type_{index}"),
                "asset_class": st.selectbox("Asset class (optional)", ASSET_CLASSES,
                    index=ASSET_CLASSES.index("UNKNOWN"), key=f"portfolio_class_{index}"),
            }
            ratios.append(st.text_input("Expense ratio (%) — optional", placeholder="Example: 0.03",
                                        key=f"portfolio_ratio_{index}"))
            holdings.append(holding)
        submitted = st.form_submit_button("Analyze portfolio")
    if not submitted:
        return None
    for index, (holding, ratio) in enumerate(zip(holdings, ratios), start=1):
        if ratio.strip():
            try:
                percent = float(ratio)
            except ValueError as error:
                raise ValueError(f"Holding {index}: enter a numeric expense percentage or leave it blank") from error
            if not isfinite(percent) or not 0 <= percent <= 100:
                raise ValueError(f"Holding {index}: expense ratio must be between 0 and 100 percent")
            holding["expense_ratio"] = percent / 100
    return holdings


def render_portfolio_view(get_workflow):
    """Save a result snapshot so reruns and view changes preserve its charts."""
    st.header("Portfolio analysis")
    st.write("Analyze supplied holdings with values, allocations, fees, and concentration measures.")
    st.caption("Prices and classifications are user supplied; this view does not fetch prices or inspect fund holdings.")
    method = st.radio("Holdings input", ["Enter manually", "Upload CSV"], horizontal=True)
    try:
        holdings = None
        if method == "Enter manually":
            holdings = _manual_form()
        else:
            st.caption(
                "CSV expense ratios are decimal fractions: 0.0003 means 0.03%. "
                "Required: symbol, quantity, price, asset_type. Optional: asset_class, expense_ratio. "
                "Leave unknown ratios blank. Maximum 1 MB and 1,000 holdings; UTF-8 encoding."
            )
            st.download_button("Download example CSV", CSV_TEMPLATE,
                               file_name="finnie_portfolio.csv", mime="text/csv")
            upload = st.file_uploader("Holdings CSV", type=["csv"], key="portfolio_csv")
            if st.button("Analyze uploaded portfolio"):
                if upload is None:
                    raise ValueError("choose a CSV file before analyzing")
                holdings = parse_holdings_csv(upload.getvalue())
        if holdings is not None:
            report = analyze_portfolio(holdings)
            result = get_workflow().invoke({"question": "Portfolio analysis", "portfolio": holdings})
            is_error = result["answer"].startswith("Could not analyze")
            st.session_state.portfolio_result = {
                "route": result["intent"], "answer": result["answer"], "is_error": is_error,
                "report": None if is_error else report,
            }
    except ValueError as error:
        # Replace any previous valid report, so invalid input cannot show old charts.
        st.session_state.portfolio_result = {
            "route": "portfolio_analysis", "answer": f"Could not analyze the portfolio: {error}.",
            "is_error": True,
        }
    result = st.session_state.get("portfolio_result")
    if not result:
        return
    st.caption(f"Route: {result['route']}")
    if result.get("is_error"):
        st.error(result["answer"])
        return
    st.text(result["answer"])
    report = result.get("report")
    if not report:
        return
    st.subheader("Last analyzed holdings")
    st.caption("These charts describe the last submitted inputs. Submit again after editing holdings.")
    st.dataframe([
        {"Instrument": p["symbol"], "Asset type": p["asset_type"], "Asset class": p["asset_class"],
         "Value ($)": p["market_value"], "Weight (%)": 100 * p["weight"]}
        for p in report["positions"]
    ], hide_index=True)
    st.subheader("Allocation by instrument")
    st.bar_chart([{"Instrument": p["symbol"], "Allocation (%)": 100 * p["weight"]}
                  for p in report["positions"]], x="Instrument", y="Allocation (%)")
    st.subheader("Allocation by supplied asset class")
    st.bar_chart([{"Asset class": label, "Allocation (%)": 100 * value / report["total_value"]}
                  for label, value in sorted(report["value_by_asset_class"].items())],
                 x="Asset class", y="Allocation (%)")
    st.caption(
        "Concentration measures the supplied instruments only. An ETF can contain many assets; "
        "different ETFs can overlap. This snapshot does not establish volatility, correlation, "
        "suitability, or a risk rating."
    )
