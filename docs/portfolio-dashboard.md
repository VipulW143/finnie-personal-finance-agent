# Portfolio dashboard checkpoint — November 5, 2026

## Requirement and scope

The problem statement asks for portfolio analysis of user input and a dashboard with visualizations. This milestone adds CSV input, instrument and supplied-asset-class allocation charts, and position concentration metrics. It does not claim to estimate historical volatility, correlations, loss probability, suitability, or the underlying holdings of funds. The original manual and CLI portfolio inputs remain supported.

## Technical file changes

### src/finnie/portfolio.py

- Added optional asset_class to Holding and the allowed labels STOCKS, BONDS, CASH, OTHER, UNKNOWN. Missing labels become UNKNOWN; the code never infers a stock/bond classification from ETF or a ticker name.
- Added analyze_portfolio(holdings), returning a structured dictionary with total_value, input_rows, positions, value_by_asset_type, value_by_asset_class, known_fee_value, annual_fees, weighted_expense_ratio, concentration, and effective_positions.
- Normalized ticker and asset labels by stripping spaces and uppercasing. Repeated tickers are aggregated into one instrument before weights/concentration are calculated. Conflicting type/class labels on repeated tickers are rejected to avoid combining inconsistent classifications silently. Distinct tickers remain separate, even if their funds overlap.
- Preserved fee calculations per supplied row, supporting different lots and partial known-fee coverage. Missing ratios remain absent; a supplied zero is known zero. Weighted fees divide by the value with supplied ratios, not the entire portfolio when coverage is incomplete.
- Validated the outer list, row objects, text labels, positive numeric quantities/prices, finite products/totals, and expense fractions in [0, 1]. Booleans and numeric strings in direct JSON input are rejected. CSV numeric text is converted explicitly by its parser.
- summarize_portfolio() now formats analyze_portfolio() output rather than independently computing a second set of metrics. Existing workflow calls still use the same public summary function, so CLI, Chat, and Portfolio share the backend calculations.
- Added unique-instrument count, supplied asset-class allocation, concentration, effective position count, and explanatory limits to the formatted response. No trading recommendation or risk rating is produced.

### src/finnie/portfolio_import.py (new)

- Defined required CSV columns symbol, quantity, price, asset_type; optional asset_class and expense_ratio.
- Added parse_holdings_csv(bytes) using Python's standard csv module, UTF-8 with optional BOM, and strict quote parsing.
- Rejects duplicate/unknown/missing headers, excess row fields, invalid numbers, invalid encoding, empty input, files over 1 MB, and more than 1,000 nonempty holding rows.
- Ignores empty rows and omits blank optional cells. Converts quantity, price, and expense_ratio to numbers; analyze_portfolio() then performs the shared financial validation.
- CSV expense ratios are fractions, matching backend/CLI JSON: 0.0003 means 0.03%. The manual UI continues accepting percentages: 0.03 means 0.03% and is divided by 100 before analysis.
- Includes CSV_TEMPLATE, also used for the downloadable example. Uploaded files are processed in memory rather than saved to disk.

### src/finnie/portfolio_ui.py (new)

- Extracted the Portfolio interface into render_portfolio_view(get_workflow), keeping the main UI file smaller.
- Manual form retains original keys and adds an optional asset-class selector. Numeric ratio parsing rejects nonfinite values and out-of-range percentages.
- Added manual/CSV input choice, example download, file uploader, and an upload-analysis button.
- Both paths validate using analyze_portfolio(), invoke the existing portfolio LangGraph route, and save answer/report together in portfolio_result. Arithmetic is intentionally revalidated by the existing summary function; this small duplicate calculation avoids changing shared workflow state or multi-agent output contracts in this milestone.
- Added a table of aggregated positions plus bar charts for instrument percentages and supplied asset-class percentages. Charts read the saved report, not current unsent form fields, and are labeled as the last analyzed snapshot.
- Invalid submissions replace the previous result with an error and remove its charts. Existing Clear conversation and results deletes the saved result, including charts. No model or embedding requests are needed for direct Portfolio analysis.

### src/finnie/ui.py

Imported render_portfolio_view and replaced the old inline Portfolio branch with render_portfolio_view(get_workflow). Routing, Chat, Goals, News, Market, Tax, and Knowledge behavior were not otherwise changed.

### Samples, tests, and tracking

- samples/portfolio.csv: two sample holdings, VTI and BND, including asset classes and decimal expense ratios.
- tests/test_portfolio.py: 10 tests covering arithmetic, fees, partial coverage, known zero, missing classes, concentration, duplicate lots, conflicting labels, numeric validation, CSV structure/limits, sample parity, and the real portfolio workflow path.
- tests/test_portfolio_ui.py: two Streamlit AppTest tests exercise manual form success, chart persistence, error replacement, reset, missing upload, CSV success, and invalid CSV replacement. AppTest cannot select a browser file, so CSV bytes are injected at the uploader boundary; actual browser file selection remains a learner acceptance check.
- README.md and .agent/PLAN.md: checkpoint, verification, progress estimate, and remaining work updated. No dependencies or live provider integration changed.

## Formulas

For each row: market_value = quantity * price.

For a repeated symbol: instrument_value = sum of that symbol's row values.

Total = sum of instrument values.

Weight = instrument_value / total.

Annual fund expenses = sum of row market_value * supplied expense_ratio.

Known-fee weighted ratio = annual fund expenses / value covered by supplied ratios.

Position concentration = sum(weight ** 2).

Effective equal-weight positions = 1 / concentration.

For two equal instruments, concentration is 0.5 and effective positions is 2. For one instrument, both measures are 1. These are mathematical descriptions of instrument weights, not counts of underlying investments or safety assessments. A diversified fund still appears as one instrument in this snapshot.

## Verification and acceptance

All 28 project tests pass, including the two dashboard tests. This is a test count, not a measured coverage percentage. Full-project coverage and broad performance evaluation remain pending.

Restart Streamlit from the project directory:

```bash
python -m streamlit run src/finnie/ui.py
```

Open Portfolio, select Upload CSV, and use samples/portfolio.csv or Download example CSV. Submit and expect:

- Total value $1,466.00.
- VTI $1,250.00 (85.3%) and BND $216.00 (14.7%).
- Supplied asset classes STOCKS 85.3%, BONDS 14.7%.
- Weighted expense ratio 0.030%; annual expenses $0.44; coverage $1,466.00.
- Two charts and a position table.
- Concentration 0.749; effective equal-weight positions 1.34.

In manual mode, three rows A/$50, A/$50, B/$100 should produce two unique instruments, 50% each, concentration 0.500, and effective positions 2.00. Blank the symbol and resubmit: expect an error without old charts. Clear results: expect both the text and charts to disappear.

Overall project planning estimate: approximately 78%. Portfolio upload/chart/concentration implementation is complete with learner UI acceptance pending; broader risk modeling is not claimed. Remaining submission work includes market trends/charts, goal risk context/charts, broader evaluation and coverage/performance evidence, final documentation, packaging, and eventually the demo.
