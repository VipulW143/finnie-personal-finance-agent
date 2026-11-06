"""Latest-trade and historical-trend views with explicit data provenance."""

import streamlit as st

from finnie.market_history import HISTORY_WINDOWS


def render_market_view(get_workflow):
    st.header("Market overview")
    st.write("Look up the latest IEX trade and explore observed daily closing prices.")
    with st.form("market_form"):
        symbol = st.text_input("Ticker symbol", value="AAPL", max_chars=15)
        include_history = st.checkbox("Include daily price history", value=True)
        days = st.selectbox("History window (calendar days)", HISTORY_WINDOWS, index=1)
        submitted = st.form_submit_button("Get market overview")
    if submitted:
        request = {"question": f"Latest trade for {symbol.strip().upper()}", "market_symbol": symbol.strip()}
        if include_history:
            request["market_history_days"] = days
        with st.spinner("Retrieving market data..."):
            result = get_workflow().invoke(request)
        st.session_state.market_result = {
            "route": result["intent"], "answer": result["answer"],
            "history": result.get("market_history"),
        }
    result = st.session_state.get("market_result")
    if not result:
        return
    st.caption(f"Route: {result['route']}")
    answer = result["answer"]
    if answer.startswith("Could not retrieve"):
        st.error(answer)
        return
    if "SIMULATED MOCK DATA" in answer:
        st.warning("The latest-trade value is simulated fallback data, not an Alpaca market quote.")
    elif "STALE cached quote" in answer:
        st.warning("The latest-trade value is stale cached data.")
    st.text(answer)
    history = result.get("history")
    if not history:
        return
    if history["status"] == "unavailable":
        st.info("No historical chart is available for this request. The latest-trade result is shown separately.")
        return
    if history["status"] == "stale":
        st.warning("The chart and trend calculations use stale cached history. Check its retrieval time and observed dates.")
    st.subheader(f"Last requested history: {history['symbol']}")
    st.caption(
        f"{history['days']}-calendar-day request; {len(history['bars'])} observed daily closes. "
        "Split-adjusted IEX data; current UTC day excluded. Edit and submit again to update."
    )
    st.line_chart([
        {"Date": row["date"], "Daily close ($)": row["close"], "20-observation SMA ($)": row["sma20"]}
        for row in history["analysis"]["rows"]
    ], x="Date", y=["Daily close ($)", "20-observation SMA ($)"])
    st.caption(
        "The average starts after 20 observations. Missing dates are not filled. "
        "Historical price changes exclude dividends and do not predict future returns."
    )
    with st.expander("Observed daily prices"):
        st.dataframe(history["analysis"]["rows"], hide_index=True)
