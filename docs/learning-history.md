# Archived learning checkpoints

This preserves the former README as a development history. Counts, status notes, and next steps below describe earlier stages and may be superseded. Use the root README and current submission documents for setup and current evidence.

# Finnie - Personal Finance Agent

An educational capstone project: a conversational finance tutor with specialized agents, grounded answers, current news synthesis, tax education, market data, portfolio calculations, and goal projections.

## Learning workflow

Work one checkpoint at a time:

1. Ask Codex to explain the next concept briefly and give one small exercise.
2. Try it yourself in VS Code; use Colab only for a focused notebook experiment.
3. Ask Codex to review your attempt and point out the next correction.
4. Ask for implementation help when you are ready, then review the code together.
5. Update this README with the checkpoint and decisions so the next request can stay short.

Useful short prompts: `NEXT STEP`, `EXPLAIN: <concept>`, `EXERCISE: <concept>`, `REVIEW: <file>`, and `IMPLEMENT: <specific checkpoint>`.

## Requirements and target scope

The adjacent problem statement and milestones are the source of truth. The target architecture is Python, LangGraph orchestration, a retrieval system over financial education material, a Streamlit interface, and a market-data integration. The agents are Finance Q&A, Portfolio Analysis, Market Analysis, Goal Planning, News Synthesis, and Tax Education. Financial output is educational, with citations and clear limits; it must not claim to be individualized investment or tax advice.

The rubric emphasizes multi-agent design and orchestration (40%), interface and user experience (25%), finance content and analysis (20%), and code quality/documentation/testing (15%). Prioritize a working, explainable core before stretch features or UI polish.

## Current status

- **Estimated project completion:** about 72% (rough rubric-weighted estimate; see below). I’ll include an updated estimate after each completed project step.
- **Stage:** six workflow routes are implemented: Finance Q&A, Portfolio Analysis, Goal Planning, Market Analysis, News Synthesis, and Tax Education. The original four routes have prior manual learner verification. News and Tax are implemented but await learner acceptance checks.
- **Stage 8 implementation:** `src/finnie/ui.py` adds a minimal Streamlit finance Q&A chat. It calls the existing LangGraph workflow, shows its route and answer, keeps the transcript in per-browser-session state, and offers a clear-conversation button. `pyproject.toml` now declares Streamlit. The learner manually confirmed two questions route to `finance_qa`, answers and citations display, and the transcript persists across questions.
- **Stage 8 implementation:** the Streamlit sidebar switches between Finance Q&A and Portfolio. Finance Q&A was manually verified for routing, citations, and multi-turn transcript. Portfolio accepts 1–10 user-entered holdings and invokes the existing `portfolio_analysis` route. After fixing fee-field entry and currency rendering, the learner confirmed VTI/BND produced $1,466 total market value, 85.3% ETF / 14.7% Bond ETF allocation, 0.030% weighted expense ratio, and $0.44 annual expenses. Both current views are manually verified.
- **Stage 8 implementation:** the Goals view is manually verified. Target $20,000, current savings $5,000, a 5-year horizon, and 5% assumed annual return routed to `goal_planning` and returned the expected $199.74 monthly contribution and $20,000.33 projected balance, with assumptions and risk caveat displayed.
- **Stage 8 implementation:** the Market view accepts a ticker and calls the existing `market_analysis` route. The learner confirmed an AAPL response in the UI with the IEX feed, a real trade timestamp, and the `Cached quote` label. The cache was retrieved at `2026-11-03 06:07:37 UTC`; trade timestamp was `2026-11-02T21:58:05.627574927Z`.
- **Reset behavior:** the learner confirmed that **Clear conversation and results** clears the visible chat and tool outputs. The callback keeps the compiled workflow and market-data cache alive.
- **Manual edge-case results:** a blank portfolio holding produced the expected validation message; a zero goal target was rejected; and ticker `VIT` produced an Alpaca HTTP 404 followed by a visibly labeled simulated fallback. This checks provider-error handling and fallback labeling, not local ticker-format validation.
- **RAG content addition:** added an SEC Investor.gov source comparing mutual funds and ETFs, covering shared features, trading and pricing, fees, and taxes. The source catalog now maps this article to `articles/funds_source.md`. The next knowledge-base load will detect the changed source fingerprint and rebuild the local embedding index. The learner should manually verify the target question and citation before marking retrieval acceptance complete.
- **Stage 9 - News:** `src/finnie/news.py` uses the Responses API web-search tool for current reporting, asks the model to prefer established news outlets and primary financial agencies, requests a short dated synthesis, and displays citation links. `src/finnie/workflow.py` adds `news_synthesis`; CLI accepts `news <topic>` and the Streamlit News view has a search form. Each request uses hosted web search and may add API usage.
- **Stage 9 - Tax Education:** added IRS-based federal tax basics and filing sources in `articles/tax_source.md` and `articles/tax_filing_source.md`, registered in `articles/sources.json`. The `tax_education` route reuses source retrieval with a specific boundary against determining personal filing obligations, eligibility, tax liability, or refunds. CLI accepts `tax <question>` and the Streamlit Tax Education view keeps its own chat history.
- **Next checkpoint:** manually verify FAISS-backed answers and saved-index reuse in Streamlit. The Knowledge view and category controls have learner acceptance. The corpus remains 15 captured sources against the 50-source minimum. Continue source expansion, glossary, analysis/charts, broader coverage, and delivery documentation.
- **Decisions:** VS Code is the primary workspace; Colab is optional for isolated learning experiments. Python 3.14.5 is isolated in `.venv`. Keep keys out of source control.
- **Reference implementation:** do not inspect until after an independent first pass, as advised by the course notes.

### Shared Chat learner verification

The learner confirmed topic changes among compound growth (finance_qa), traditional 401(k) contributions (tax_education), and an AAPL trade (market_analysis). A Roth IRA follow-up retained the preceding 401(k) comparison. The comparison exposed a source gap, so IRS Roth IRA coverage was added. Its answer/citation acceptance is pending. Shared Chat uses wording patterns to decide when routing needs history, and explicit quote requests have a direct routing rule.

### Shared Chat routing and context

The **Chat** view automatically routes free-text requests to one specialist. The router uses the last 12 conversation messages, capped at 3,000 characters per message, to resolve follow-ups into self-contained requests. It extracts explicit calculation inputs or asks for missing details. Prior assistant answers serve as conversational context. RAG still supplies the evidence for educational claims. Dedicated forms retain their direct routes.

Chat history is stored in Streamlit session state and is submitted with each request. The graph itself has no persistent checkpointer. Clear conversation and results removes shared Chat history along with the other visible results. CLI free-text requests also carry bounded history. Each automatic routing decision adds a model call.

The router supports one specialist or a validated plan of two to three independent tasks. Tasks that depend on earlier tool results still require clarification. Local checks covered follow-up routing, invalid payload handling, and explicit tool bypass. Live routing calls correctly handled a 401(k) follow-up, an AAPL quote request, and a savings request with all four inputs. Streamlit end-to-end acceptance is pending.

Manual check in **Chat**:
1. Ask “Explain traditional 401(k) contributions.”
2. Ask “How does that affect taxable income?” Expect tax_education with the original subject preserved.
3. Ask “Get the latest trade for AAPL.” Expect market_analysis.
4. Ask “I want $20,000 in five years, have $5,000 saved, and assume a 5% annual return. How much should I save monthly?” Expect goal_planning and $199.74.
5. Clear conversation and results. Ask “How does that affect taxable income?” Expect a request to clarify the subject rather than reuse the cleared conversation.

### Multi-specialist orchestration

Shared Chat now accepts two or three independent tasks in one request. The model returns a plan and Python validates every member with the same single-task validator before execution. Nested, oversized, or invalid plans return clarification. Numerical validation remains in the existing calculation functions.

LangGraph runs route_question → dispatch_task → specialist → collect_result and loops until the plan is complete. combine_results groups the unchanged specialist outputs under separate headings, preserving each section's sources and assumptions. Citation numbers are local to each section. No additional model synthesis call is made. Specialist-specific inputs are cleared before dispatching the next task. Supported source/API failures produce an error section while the other tasks continue.

Each graph invocation gets a fresh task plan and results. Conversation history is still held by Streamlit or the CLI. One request currently supports at most three independent tasks. Dependencies between tool outputs, parallel execution, and broader exception coverage remain future work. Natural-language task extraction still depends on model accuracy.

Four regression tests in tests/test_multi_agent.py cover source preservation with real goal arithmetic, three-task input isolation, a subsequent single request, partial source API failure, and malformed/nested plans. Run them with:
```bash
python -m unittest discover -s tests -v
```
A live request returned both a cited compounding explanation and the verified $199.74 monthly contribution. Streamlit AppTest with mocked services confirmed combined output, escaped currency, and clear-session behavior. The learner confirmed the compound request in Streamlit, including both specialist sections, the citation, and the $199.74 monthly result. A subsequent IRA question returned to tax_education.

Ask in **Chat**:
“Explain compounding in investing, and separately calculate the monthly contribution to reach $20,000 in 5 years starting with $5,000, assuming a 5% nominal annual return.”

Expect route multi_agent, Finance Q&A and Goal Planning sections, an Investor.gov citation, $199.74 monthly, and $20,000.33 projected. Then ask a standalone question and confirm it returns one specialist result.

### Knowledge library and category filtering

The Knowledge view reads the source catalog, shows captured article metadata and summaries, links to originals, and supports category and title/publisher/topic search. Browsing local summaries makes no model or embedding calls. knowledge.py provides load_sources() and category_of() to share the catalog and category rules with the RAG pipeline.

Finance Q&A's topic selector is passed through FinnieState.category into answer_with_sources(). Category matching happens before semantic retrieval. A detailed topic such as Investing: index funds belongs to the Investing category. All topics retains corpus-wide retrieval. An empty category returns a clear message without a model call. Shared Chat uses the full corpus and retains its specialist routing.

The catalog now contains 50 distinct captured source summaries, meeting the minimum source-count target (50/50, 100%). The 35 additions cover SEC investment products and trading concepts, Treasury securities, CFPB credit topics, and FDIC deposit insurance. These are selected educational summaries, not full copies of the original articles; source breadth does not imply complete answer coverage. The existing fingerprint invalidates the old FAISS cache when source content or metadata changes.

The Knowledge view now has Articles and Glossary modes. The separate glossary contains 26 definitions with links to captured sources, category filtering, and case-insensitive term/definition/topic search. Browsing makes no API calls. Sixteen regression tests pass; Streamlit AppTest checked the 50-source display, glossary search, category exclusion, and article search. A live rebuild produced 59 chunks with 1,536-dimensional vectors. TIPS, credit-card grace-period, and margin-account queries each ranked the intended source first; a second load reused the saved FAISS cache. This is a three-query retrieval smoke check, not a systematic answer-quality evaluation. Learner acceptance of the new glossary remains pending. See docs/knowledge-library-expansion.md for exact changes.

Manual checks:
1. Open Knowledge and select Saving. Expect the CFPB emergency fund summary and source link.
2. Select Investing and search for index. Expect Index Funds.
3. In Finance Q&A, select Investing and ask how $100 at 5% annual interest becomes $110.25 after two years. Expect the SEC compound-interest citation.
4. Select Saving and ask what an emergency fund is. Expect the CFPB source.

### Portfolio dashboard: CSV, allocations, and concentration

Portfolio now supports manual entries or UTF-8 CSV upload. Download an example in the UI or use `samples/portfolio.csv`. Required headers: `symbol,quantity,price,asset_type`; optional: `asset_class,expense_ratio`. CSV/CLI expense ratios are decimal fractions (`0.0003` means `0.03%`); manual form ratios are percentages (`0.03` means `0.03%`). Leave unknown fees blank. CSV limits: 1 MB and 1,000 holdings. Optional asset classes are STOCKS, BONDS, CASH, OTHER, UNKNOWN; ETF labels alone do not establish the asset class.

Repeated symbols are combined before instrument weights and concentration are calculated. The dashboard shows a position table, instrument allocation chart, and supplied-asset-class allocation chart. Concentration is the sum of squared instrument weights; effective equal-weight positions is its reciprocal. Neither measures fund look-through, historical volatility, correlation, suitability, or loss probability. The last submitted report is retained across reruns; an invalid submission replaces it and removes old charts. Clear conversation and results clears it as well.

All 28 project tests pass, including CSV/workflow parity, duplicate-lot concentration, partial fee coverage, invalid numbers, and Streamlit manual/CSV/error/reset paths. The upload test injects CSV bytes at the widget boundary; selecting a real browser file still needs learner acceptance. Full-project coverage is not yet measured. See [technical file changes and acceptance checks](docs/portfolio-dashboard.md).

### Market historical prices and trends

The Market view now offers optional 30/90/180-calendar-day IEX daily history alongside the existing latest trade. It charts split-adjusted closes with a 20-observation simple moving average and reports endpoint price change, highest/lowest close, and maximum observed closing-price drawdown. The current UTC day is excluded. Actual dates/counts are shown; missing dates are not filled. Price change excludes dividends and is not total return. Indicators describe the observed series and are not predictions or trading recommendations.

Daily history uses a separate 30-minute in-memory cache keyed by ticker/window, refreshed when the UTC end date changes. Provider failures reuse clearly labeled stale history if available; otherwise the chart is unavailable. No simulated historical series is generated, even when the latest-trade endpoint falls back to its labeled mock. Existing Chat/CLI latest-trade requests stay quote-only; history is enabled through the Market form or an explicit `market_history_days` workflow input.

All 40 project tests pass, including history arithmetic, pagination, invalid bars, safe failures, cache behavior, and dashboard error/reset paths. A live 90-day AAPL request returned 63 observations and a valid trend summary on November 5, 2026. Learner browser acceptance is pending. See [exact file changes, formulas, and acceptance checks](docs/market-trends.md). The API contract follows [Alpaca historical bars documentation](https://docs.alpaca.markets/us/reference/stockbarsingle-1).

### Goal context and monthly projections

Goals includes optional comfort-with-investment-losses context (not specified, low, moderate, high). That label changes the explanation, not the selected return, investment mix, or monthly payment. It is not a suitability assessment. The form's percentage return is still converted to a decimal nominal annual rate and divided by 12.

The chart compares the entered-rate balance, the same rounded contribution at 0%, and a target reference line. A monthly table includes modeled growth/loss. The 0% comparison is not a guaranteed floor or worst-case outcome. Both paths exclude taxes, fees, inflation, and market fluctuations. The $20,000 / $5,000 / 5-year / 5%-nominal example remains $199.74 monthly and $20,000.33 projected; at 0%, the same payment yields $16,984.40, a $3,015.60 shortfall.

The shared project_goal() report drives the formatted workflow answer and chart. Stable log1p/expm1 factors handle very small nonzero rates; explicit numeric guards reject overflow. All 51 project tests pass, including nine new calculator/context checks and two dashboard checks. Learner acceptance is pending. See [exact file changes, formulas, and acceptance checks](docs/goal-projections.md).

### Reproducible quality gate

Install development tools with `python -m pip install -e '.[dev]'`, then run:

```bash
python scripts/check_quality.py
```

The runner executes the entire offline suite, exports `reports/coverage.json` and `reports/coverage_html/index.html`, and fails if tests fail or combined statement/branch coverage is below 80%. Scope is all of `src/finnie`, including CLI and the main Streamlit script; no production files or statements are excluded. Coverage is measured execution, not answer correctness or project completion.

Current checkpoint November 5, 2026: **91 passing tests**, **97.56% statements**, **93.82% branches**, **96.53% combined** using coverage.py 7.17.2. Provider-boundary tests also prompted stricter latest-trade validation: positive non-boolean numeric price, timezone-aware timestamp, valid ticker type, and nonnegative cache age. See [test evidence, exact file changes, and remaining submission gaps](docs/evaluation.md). Generated reports are local/ignored and can be regenerated.

### Live evaluation and local performance

`evaluation/cases.json` contains 12 retrieval questions, 10 router cases, and three answer-review examples. `evaluation/results.json` retains the actual initial failure, corrected run, reviewed sample answers, coverage, and benchmark evidence. This is a small development set, not held-out accuracy. The routing check exposed copied prompt defaults for a goal with no inputs; numerical examples were removed and goal context/completeness validation added. The rerun passed 10/10 routing cases and all 12 retrieval questions found their designated sources at rank one. News no longer returns a fixed mutual-fund release or rewrites BLS citation URLs.

Run `python scripts/evaluate_project.py` for offline local benchmarks. It refuses to rebuild a missing/stale source index without API permission. Use `python scripts/evaluate_project.py --live --answers` explicitly for paid query embeddings, routing, and review answers. Reports are written to `reports/evaluation.json` and `reports/evaluation.md`; subsequent runs overwrite them. No deployment latency/throughput or universal factual-accuracy claim is made. See [exact changes, metrics, answer review, and limitations](docs/acceptance-and-performance.md).

### FAISS vector retrieval

Install or refresh dependencies from the project directory with:
```bash
python -m pip install -e .
```
FAISS CPU 1.15.1 was installed successfully on this Mac's Python 3.14 environment. pyproject.toml declares faiss-cpu>=1.13,<2 and numpy>=2.1,<3.

vector_store.py builds IndexFlatIP from float32 vectors normalized to length one. The normalized dot product equals cosine similarity. FAISS performs exact search over this small corpus. It remains an exhaustive search, now performed by the native FAISS library rather than the Python similarity loop. Each index row maps to the chunk record at the same position. search_chunks returns the familiar text, metadata, and score fields.

index_chunks now returns a VectorStore with sequence-style iteration, indexing and length. search_chunks also accepts legacy lists of embedded chunk records. rag.py and workflow.py use the new store. The educational similarity.py helper remains available for the earlier exercise.

The ignored .finnie/knowledge_index.json cache is now version 2. It contains the serialized native FAISS index as base64, source records and embeddings, a fingerprint, and a checksum binding the index bytes to the records. The embeddings are retained for legacy migration, recovery and filtered subset construction, which duplicates vector storage in this small local cache. A unique temporary file and atomic replacement keep the index and metadata together during writes.

A matching version 1 cache is migrated from its saved embeddings without an embedding API call. Changed source text, citation metadata or embedding model invalidates the fingerprint and triggers rebuilding. A damaged serialized index with usable cached vectors is reconstructed from those vectors. Native cache loading is intended for the app's own local generated artifacts.

All-topic retrieval reuses the restored full FAISS index. Category and IRS-only filtering runs before search and creates an in-memory FAISS subset from existing vectors, without re-embedding sources. At this corpus size the subset is rebuilt per request. A query still makes one embedding API call and an educational answer still uses its model call.

Verification passed: 14 regression tests, actual migration and reload of 24 chunks with 1,536 dimensions without source re-embedding, and live compounding and filtered emergency-fund answers with expected citations. Streamlit learner acceptance is pending.

Manual acceptance:
1. Restart Streamlit. In Finance Q&A choose Investing and repeat the $100 at 5% compounding question.
2. Choose Saving and ask what an emergency fund is. Confirm the CFPB citation.
3. Restart the app and ask again. The terminal should show Using saved Finnie FAISS knowledge base.
4. Existing source changes should still trigger a rebuild.

### Progress estimate method

Working estimate: approximately **92% complete**, pending final acceptance/packaging review. This is a planning estimate, not a grade or coverage number. Current quality gate: 91 passing tests, 97.56% statements, 93.82% branches, 96.53% combined coverage. A curated live development set found every designated source for 12 retrieval questions and passed 10/10 routing cases after fixing an invented-default goal failure. Three answer samples received source-based Codex review with a citation-placement limitation noted. Local benchmarks and retained evidence are available in evaluation/results.json and docs/acceptance-and-performance.md. Remaining work: final architecture/setup/API/troubleshooting documentation, clean package/setup validation, outstanding manual chart/cache/reset checks, then demo preparation.

### Portfolio command (current CLI)

Enter `portfolio ` followed by a JSON list. Prices and output are in USD. `expense_ratio` is a decimal fraction: `0.0003` means `0.03%`. Missing ratios are excluded from the fee calculation, and Finnie reports the value covered. The output is descriptive and does not recommend trades.

```text
portfolio [{"symbol":"VTI","quantity":5,"price":250,"asset_type":"ETF","expense_ratio":0.0003},{"symbol":"BND","quantity":3,"price":72,"asset_type":"Bond ETF","expense_ratio":0.0003}]
```

### Goal planning command (current CLI)

Enter `goal ` followed by a JSON object. Amounts are in USD; `annual_return` is a decimal (for example, `0.05` means 5%). The estimate uses monthly compounding and contributions at the end of each month, and excludes taxes, fees, and inflation. Investor.gov's [Savings Goal Calculator](https://www.investor.gov/financial-tools-calculators/calculators/savings-goal-calculator) uses the same core inputs: goal, starting amount, time, estimated rate, and compounding frequency.

```text
goal {"target_amount":20000,"current_savings":5000,"years":5,"annual_return":0.05}
```

For the calculation, Finnie interprets `annual_return` as a nominal annual rate, then sets `n = years × 12` and `r = annual_return ÷ 12`. The starting balance grows to `current_savings × (1 + r)^n`. The future value of equal end-of-month contributions is `monthly_contribution × (((1 + r)^n - 1) ÷ r)`. Finnie solves that equation for the contribution needed to reach the target and rounds the monthly contribution upward to the next cent. When the assumed return is zero, it divides the remaining target by the number of months. If an entered return instead means an effective annual rate, its equivalent monthly rate would be `(1 + annual_return)^(1/12) - 1`; that convention produces a different estimate. This is a projection under the entered assumptions, not a promise of results.

### Manual acceptance checklist

Run the UI with `streamlit run src/finnie/ui.py` in the activated project `.venv`. These are manual checks, not automated tests:

1. **Reset:** ask two Q&A questions, switch to Tax Education and ask one question, then click **Clear conversation and results**. Return to Finance Q&A, Tax Education, Portfolio, News, Goals, and Market; prior messages and displayed tool results should be gone. The in-memory market cache may still be used because reset clears displayed state, not that cache.
2. **Routing:** ask a finance question and confirm `finance_qa`; submit holdings and confirm `portfolio_analysis`; submit goal inputs and confirm `goal_planning`; request AAPL and confirm `market_analysis`; search a topic and confirm `news_synthesis`; ask a Tax Education question and confirm `tax_education`.
3. **Retrieval and tax education:** ask “How do I create a monthly household budget?” and check for the CFPB citation. Ask “How does compounding work?” and check for the Investor.gov citation. Ask “What is the importance of a credit score?” and check for the Washington DFI citation. Ask “Explain ETFs vs mutual funds” and check for the SEC citation and trading/pricing distinction. In Tax Education, ask “What is the difference between a tax deduction and a tax credit?” and check for the IRS citation. Then ask “How much tax will I owe?” and confirm Finnie declines to calculate a personal tax amount and refers you to current IRS instructions or a qualified tax professional. Ask something outside captured sources and confirm Finnie says the sources do not answer rather than inventing a cited fact.
4. **News:** search “What are the latest U.S. inflation and Federal Reserve news?” Confirm a concise summary, publication dates where available, and clickable source links. Submit a blank search and confirm validation. Treat the summary as reporting context, not an investment recommendation.
5. **Calculations:** enter the verified VTI/BND sample and confirm $1,466 total, 85.3% / 14.7% allocation, 0.030% weighted expense ratio, and $0.44 annual expenses. For Goals, enter $20,000 target, $5,000 savings, five years, and 5% nominal return; expect $199.74 monthly and $20,000.33 projected.
6. **Input errors:** in Portfolio, submit a blank ticker or zero price and confirm a readable validation message. In Goals, set target amount to zero and confirm a validation message. In Market, clear the ticker and submit; confirm a clear invalid-ticker message and no simulated quote presented as live.
7. **Market cache and fallback:** request AAPL twice within 30 minutes in the same running app; first result should be live or clearly labeled fallback, and the second may say cached. Close and restart the app to observe that the in-memory cache resets. Verify mock fallback only in an environment without Alpaca credentials or during provider/network failure, and confirm the output labels it simulated. Never paste credentials into chat or logs.

The learner confirmed the reset, blank portfolio holding, zero goal target, and market HTTP 404 fallback checks. The Q&A, portfolio, goal, and market routes and their representative outputs have also been exercised. Remaining review items: source-specific retrieval checks, any desired extra invalid-input cases, inspect documentation for consistency, and decide whether to pursue optional news/tax agents or prepare final delivery.

### News and Tax evaluation results

| Case | Result | Evidence and limits |
| --- | --- | --- |
| News form submitted blank | Pass | Streamlit asked for a topic or question. |
| ETF versus mutual fund comparison entered in News | Pass | Finnie directed the general comparison to Finance Q&A. |
| Broad U.S. mutual fund news | Pass for the curated release | Streamlit displayed the dated October 29 ICI release and its direct link. This case uses a verified release for 30 days after publication. It does not evaluate live search. |
| Latest FOMC decision | Pass for this live query | The official statement supported the October 27–28 meeting dates and the decision to hold the target range at 3.75%–4.00%. |
| December 2026 FOMC decision asked on November 4 | Pass for future event handling | Finnie said the decision had yet to be announced. The official Fed calendar confirmed December 8–9. Finnie cited a third party and volunteered market odds that were not verified. |
| Latest U.S. jobs report asked on November 4 | Pass for this live query | Streamlit reported September as the data period and October 2 as the release date. The archived BLS release confirmed payrolls increased by 29,000 and unemployment was 4.2%. The archive URL replacement is specific to the September 2026 release. |
| Tax deduction versus tax credit | Pass in a live workflow check | Finnie explained the difference and cited the IRS credits and deductions page. |
| Traditional versus Roth 401(k) tax treatment | Pass in Streamlit | Finnie explained when each contribution type receives its federal tax benefit and cited the IRS 401(k) plans page. |
| Personal federal income tax calculation | Pass in Streamlit | With fictional wages and a traditional 401(k) contribution, Finnie explained the general pretax treatment, cited the IRS, and referred the user to current IRS instructions without calculating a personal tax bill. |

For the demo, open the original source and compare the reporting period, publication date, and headline figure with the answer. General live News coverage still needs broader evaluation.

### Cross-view Streamlit check

The learner verified Tax Education, Goals, and Finance Q&A in one Streamlit session. Tax Education cited IRS Topic 501 for the deduction comparison and showed the IRS filing guidance link. Goals returned an estimated $199.74 monthly contribution and a $20,000.33 projected balance for the documented sample. Finance Q&A cited the SEC for the ETF and mutual fund trading and pricing comparison. After selecting **Clear conversation and results**, the learner confirmed that all three views cleared their previous outputs.

### Capstone demo walkthrough

Allow about five minutes. From the project directory, activate the virtual environment and launch Streamlit:

```bash
source .venv/bin/activate
streamlit run src/finnie/ui.py
```

1. **Introduce Finnie (30 seconds).** Show the sidebar and explain that LangGraph routes each request to the capability selected in Streamlit. Point to the route label as you switch views.
2. **Show an answer with a source (1 minute).** In **Finance Q&A**, ask “Explain ETFs vs mutual funds.” Point out that ETFs trade throughout the day while mutual fund orders use the next calculated net asset value. Open the SEC citation and show where it supports that distinction. Expect `finance_qa`.
3. **Show a repeatable calculation (1 minute).** In **Goals**, enter a $20,000 target, $5,000 in current savings, 5 years, and a 5% nominal annual return. Expect `goal_planning`, **$199.74 per month**, and a projected balance of **$20,000.33**. Explain the monthly compounding and end-of-month contribution assumptions.
4. **Show the tax education boundary (1 minute).** In **Tax Education**, ask “What is the difference between the standard deduction and itemized deductions?” Expect `tax_education`, IRS Topic 501, and the filing guidance link. Then ask “Given $85,000 of fictional wages and a $5,000 traditional 401(k) contribution, calculate exactly how much federal income tax I owe.” Show that Finnie explains the general pretax rule and refers to IRS guidance without calculating a personal tax bill.
5. **Show a live source check (1 minute).** In **News**, ask “What did the Federal Reserve announce at its latest policy meeting? Link to the official statement.” Expect `news_synthesis`. Open the Fed statement and compare the meeting date and decision with Finnie’s answer. The answer can change between rehearsals. If the live request fails, use the documented October 2026 evaluation case and identify it as a prior run.
6. **Reset the session (30 seconds).** Click **Clear conversation and results**. Revisit Finance Q&A, Goals, and Tax Education to show that the chats and projection are gone.

### Market quote command (current CLI)

Enter `market ` followed by a ticker symbol. Alpaca credentials are a pair: put `APCA_API_KEY_ID=your_key_id_here` and `APCA_API_SECRET_KEY=your_secret_here` in the ignored `.env` file. Without both, Finnie uses a visibly labeled simulated value. Successful provider responses are cached in memory for 30 minutes; if a later request is rate-limited or fails, Finnie uses a stale cached trade when available or the simulated fallback. Never treat mock data as a real price. The free market-data feed includes live IEX trades; IEX is a single exchange and does not represent the consolidated US market. See Alpaca's [market data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) and [latest-trade endpoint](https://docs.alpaca.markets/us/reference/stocklatesttradesingle-1).

```text
market AAPL
```

### News and tax commands (current CLI)

For current news, type `news ` followed by a topic. Finnie uses the OpenAI Responses API web-search tool and displays source links from the API citation annotations. This requires access to web search for the configured model and adds API usage. For general tax education, type `tax ` followed by a question; Finnie retrieves only from the local education corpus and keeps answers within general U.S. federal concepts. Neither command gives individualized investment or tax advice.

```text
news latest U.S. inflation and Federal Reserve news
tax What is the difference between a tax deduction and a tax credit?
```

### Initial RAG source candidates

The library started with the following sources and now contains 50 captured summaries. See articles/sources.json for the authoritative current catalog:

- Budgeting: [CFPB - Creating a monthly household budget](https://www.consumerfinance.gov/consumer-tools/educator-tools/youth-financial-education/teach/activities/creating-monthly-household-budget/).
- Investing: [SEC Investor.gov - Introduction to Investing](https://www.investor.gov/introduction-investing).
- ETFs and mutual funds: [SEC Investor.gov - Characteristics of Mutual Funds and ETFs](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/characteristics-mutual-funds-exchange-traded-funds).
- Credit: [Washington DFI - Credit Reports and Scores](https://dfi.wa.gov/financial-education/information/credit-reports).
- Tax basics: [IRS - Credits and deductions](https://www.irs.gov/credits-and-deductions) and [IRS - How to file your taxes](https://www.irs.gov/how-to-file-your-taxes-step-by-step).
- Expansion source: [Khan Academy - Investments and retirement](https://www.khanacademy.org/college-careers-more/personal-finance/pf-investment-vehicles-insurance-and-retirement).

Representative CFPB, SEC, and IRS questions have been exercised during development. The expanded library has three new live retrieval smoke checks; systematic retrieval and answer evaluation across the corpus remain future work. Khan Academy is a candidate and is not ingested. Source metadata is recorded in `articles/sources.json`; captured files are explicitly mapped with a `file` field. The Markdown files are concise paraphrases of selected source material, not verbatim copies. Keep source title, URL, publisher, topic, and review date alongside each ingested document.

### Traditional IRA coverage checkpoint

The learner's traditional-versus-Roth IRA question exposed missing traditional IRA coverage. An IRS Traditional IRAs article is now registered with citation metadata. It states that contributions may be fully or partially deductible depending on filing status and income, and that amounts generally are taxed on distribution. Comparison retrieval acceptance is pending.

### Goal clarification wording correction

A learner check correctly returned clarification for a goal with no inputs, but the generic routing fallback did not explain what to provide. GoalInputError now carries an actionable message through resolve_request(): target amount, current savings, whole-year horizon, and assumed annual return. A partial goal asks for its missing fields, while invalid supplied values retain their validation explanation. Provider outages and unrelated malformed routes retain the generic fallback. Two new regression tests cover validation messages and the real graph's clarification path without invoking the calculator. The complete gate passes 91 tests; the live 10-case routing snapshot remains the earlier run and was not rerun for this wording-only correction.
