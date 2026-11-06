# Market history and trend checkpoint — November 5, 2026

## Result

The Market view now combines the existing latest-trade lookup with optional 30-, 90-, or 180-calendar-day price history, a daily-close/moving-average chart, and calculated descriptions of the observed series. Latest-trade cache/mock behavior is retained. Historical requests use either provider data, a clearly labeled cached series, or an unavailable result with no fabricated bars.

API contract checked against [Alpaca historical bars, single symbol](https://docs.alpaca.markets/us/reference/stockbarsingle-1): /v2/stocks/{symbol}/bars, 1Day timeframe, IEX feed, split adjustment, ascending order, and next_page_token pagination. Split adjustment does not include dividend reinvestment. These data are single-exchange observations, not consolidated-market prices.

## Exact file changes

### src/finnie/market_history.py — new

- HISTORY_WINDOWS permits 30/90/180 calendar days. _history_cache is independent of the latest-trade cache and keyed by normalized ticker and window.
- _fetch_history() constructs authenticated requests with the existing Alpaca credentials; follows pagination up to five pages; rejects repeated/invalid tokens or excessive pagination rather than showing a partial series. Errors use short safe explanations; credentials, raw request objects, and response bodies are not printed.
- Requests run from midnight UTC minus the chosen window up to the current UTC midnight. The current UTC date is excluded, making a calendar-day request different from a count of trading sessions. This avoids charting today's in-progress daily bar. No exchange-calendar or holiday library is introduced.
- Each bar must have a finite positive numeric close and a timezone-aware timestamp inside the requested interval. Bars are sorted; duplicate dates are rejected. The API's inclusive boundary at the exact end timestamp is discarded. Missing dates are not filled or treated as zero returns.
- analyze_history() computes endpoint price change, trailing 20-observation simple moving averages, highest/lowest observed closes, and maximum peak-to-subsequent-trough closing-price drawdown. Missing SMA values stay None until the twentieth observation. A single-observation series has no endpoint change.
- get_market_history() returns a structured dictionary: symbol, days, status, bars, analysis, requested_start, requested_end, retrieved_at, data_label. Status is provider/cached/stale/unavailable. Fresh history is reused for 30 minutes, provided the requested UTC end date has not changed. Expired/mismatched history is refreshed; failures return stale cached history with its original retrieval date and original observed dates, or unavailable with no bars if no cache exists. Copies prevent a caller from altering cached data. The cache is in memory and resets with the process.
- format_market_history() labels the actual date span, observation count, retrieval time, feed, adjustments, missing-data rules, and metric limits. It reports whether the latest daily close is above/below/equal to its available SMA without interpreting that as a buy/sell signal.
- Reuses the existing market module's ticker pattern, UTC clock, timestamp formatter, cache TTL, and safe error type. src/finnie/market_data.py and the existing latest-trade fallback implementation were not changed.

### src/finnie/workflow.py — changed

- Added market_history_days and market_history to FinnieState.
- analyze_market() still obtains and formats the latest trade. Only when market_history_days is supplied does it request history, append its summary, and return the structured result for charting.
- A history failure does not discard a successfully retrieved quote. An invalid ticker still produces the existing validation error.
- Multi-agent dispatch clears both new request/result fields alongside existing specialist payloads, preventing accidental history reuse between tasks.
- Existing Chat/CLI latest-trade requests remain quote-only. This milestone exposes window selection through the Market view and explicit workflow inputs; it does not add natural-language historical-window extraction to the router.

### src/finnie/market_ui.py — new

- render_market_view(get_workflow) contains the Market interface extracted from ui.py.
- The form accepts a ticker, optional-history checkbox, and calendar-day window. Submitting builds the explicit market workflow state and saves answer plus history in market_result.
- Displays the existing simulated/stale quote warnings. Independently warns when historical data are stale, or displays no chart when unavailable.
- Uses st.line_chart() for observed closes and trailing SMA, plus an expandable price table. The saved report survives reruns; it is labeled as the last requested history. A subsequent invalid/unavailable submission replaces the earlier chart. Existing Clear conversation and results removes it.

### src/finnie/ui.py — changed

Imported render_market_view and replaced the previous inline Market branch with a call to it. Increased workflow_version from 11 to 12 so existing Streamlit sessions build the graph with the new state/output fields. Other views and visible conversation history remain intact.

### Tests and tracking

- tests/test_market_history.py: 10 tests for hand-calculated arithmetic, rolling-window boundaries, short histories, invalid closes/timestamps, pagination/query parameters, provider errors, cache reuse/copy isolation, stale fallback, window/symbol separation, UTC date rollover, missing credentials, invalid input, and explicit workflow integration.
- tests/test_market_ui.py: two AppTest tests cover chart/table rendering, displayed calculations, rerun persistence, reset, stale warning, unavailable history, quote-only behavior, and invalid-input replacement. Provider functions are mocked for deterministic UI tests.
- README.md and .agent/PLAN.md: current capabilities, acceptance steps, live evidence, limits, and remaining work updated.
- No dependencies, credentials, source summaries, or embeddings changed. History parsing and calculation make no model calls.

## Formulas and example

Observed price change = last_close / first_close - 1. The endpoint dates are the first/last available bars, not assumed calendar endpoints. Dividends are excluded, so this is not total return.

SMA20 at observation i = average of closes from i-19 through i. It needs 20 observations, not 20 calendar days. Holidays, weekends, and missing data do not create artificial rows.

Running peak at i = maximum close observed up through i.

Drawdown at i = close_i / running_peak_i - 1.

Maximum observed drawdown = minimum drawdown over the available series. It is displayed as a nonpositive percentage, and covers only closes in this window, excluding intraday lows or earlier peaks.

Example closes 100, 120, 90, 60, 110 produce +10% endpoint change and -50% maximum observed drawdown (120 down to 60). There are fewer than 20 observations, so no SMA20 is reported. This example shows why endpoint growth and drawdown describe different aspects of a price path.

## Verification

All 40 project tests pass. This is a test count, not a coverage percentage. Broader project coverage and performance measurements remain pending.

Live Alpaca AAPL history check, retrieved 2026-11-05 07:50:28 UTC (client date November 5):

- 90-calendar-day request, 63 observations from 2026-08-07 through 2026-11-04.
- Observed endpoint price change +11.58%.
- SMA20 $342.95; latest observed close above the average.
- Highest/lowest observed close $349.56/$302.20.
- Maximum observed closing-price drawdown -4.95%.

These are recorded integration-check results, not fixed expected prices for future runs. The unit tests separately exercise fresh and stale cache branches without a live API. Learner browser acceptance is pending.

## Learner acceptance

Restart Streamlit from the project directory:

```bash
python -m streamlit run src/finnie/ui.py
```

1. Open Market, enter AAPL, leave Include daily price history enabled, choose 90, and press Get market overview.
2. Expect route market_analysis, the latest trade, a separate historical summary, a close/SMA chart, and an expandable daily-price table. Verify actual date range, observation count, feed, and retrieval time.
3. Repeat promptly and expect the historical data freshness label to say cached. Quotes have their own cache.
4. Choose a 30-day window and resubmit. SMA may be unavailable if fewer than 20 observations were returned; no values should be invented to fill it.
5. Disable history and submit: expect just the quote and no previous chart. Submit a blank ticker: expect an error without a previous chart. Clear conversation and results removes the saved overview.

Historical descriptions are educational observations, not forecasts or investment recommendations. They do not establish volatility, probability of loss, or suitability.

Overall planning estimate: approximately 81%, pending full-rubric evaluation. Portfolio dashboard acceptance is confirmed. Market trends/charts implementation and live provider verification are complete, with learner acceptance pending. Goal risk context/charts, systematic evaluation/coverage/performance, final submission documentation/packaging, and eventually demo preparation remain.
