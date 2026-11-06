# Interfaces and usage

This document describes local Python functions and CLI commands. Finnie does not expose a public HTTP API, REST server, or MCP server. Run from an editable source installation.

## Workflow interface

```python
from finnie.workflow import build_workflow

graph = build_workflow()
result = graph.invoke({
    "question": "Explain compound interest.",
    "auto_route": True,
    "history": [],
})
print(result["intent"])
print(result["answer"])
```

Public inputs include question; optional auto_route/history/category; portfolio holding list; goal object; market_symbol with optional market_history_days; news_query; tax_question. Result has intent and answer, and optionally market_history or multi-agent task_results. Explicit tool fields select their specialist; use one such payload per direct request. Auto-routed natural-language planning is model-dependent. Do not set multiple unrelated payload fields and expect a plan; ask Chat for independent tasks instead.

History items have role user/assistant and string content. Dedicated Finance Q&A can pass category such as Saving or Investing; Tax Education applies IRS filtering. Plans support at most three independent specialist tasks. No external conversation/thread ID or durable memory API is implemented.

## Deterministic functions

| Call | Output and contract |
| --- | --- |
| portfolio.analyze_portfolio(holdings) | Structured values, aggregated positions, allocations, fees/coverage and concentration; raises ValueError on invalid input |
| portfolio.summarize_portfolio(holdings) | Text from the same report |
| portfolio_import.parse_holdings_csv(bytes) | UTF-8/BOM CSV to holding dictionaries; maximum 1 MB/1,000 rows; no file persistence |
| goals.project_goal(goal) | Payment, endpoints, monthly rows, comparison and risk context |
| goals.calculate_monthly_contribution(goal) | Text from the same report |
| knowledge.load_sources(), load_glossary() | Local catalog/definitions |
| knowledge.search_glossary(query, category) | Local case-insensitive term/definition/topic filtering |
| rag.load_knowledge_base(allow_rebuild=True) | Saved VectorStore or rebuild using API. False refuses a rebuild before source embedding calls. |
| retrieval.search_chunks(question, store, top_k=3) | Ranked chunks with text, metadata and cosine-equivalent scores; uses query embedding API |

Holdings require symbol, positive finite quantity, positive finite price, and asset_type. Optional asset_class is STOCKS/BONDS/CASH/OTHER/UNKNOWN. Optional expense_ratio is a decimal fraction in [0,1]. Conflicting classifications for repeated symbols are rejected. CSV requires symbol,quantity,price,asset_type; optional columns asset_class,expense_ratio; unknown/repeated headers are rejected. Missing expense ratio is excluded from fee coverage; zero means a known zero.

Goals require positive target_amount, nonnegative current_savings, integer years 1–100, and decimal nominal annual_return greater than -0.99 and at most 1. Optional risk_tolerance is not_specified/low/moderate/high. Values must be user supplied. The UI converts human percentages into decimal fractions; JSON/Python do not.

Market quote returns symbol, price, trade_at, retrieved_at, data_label. History returns status provider/cached/stale/unavailable, symbol/window, bars, analysis, dates and retrieval labels. Respect status before charting. Stale retrieval timestamps are deliberately preserved. A simulated quote is distinguishable from a real provider value and must not be presented as a live market price.

## CLI

```bash
python -m finnie.app
```

At Finnie's prompt:

```text
Explain ETFs vs mutual funds.
portfolio [{"symbol":"VTI","quantity":5,"price":250,"asset_type":"ETF","asset_class":"STOCKS","expense_ratio":0.0003},{"symbol":"BND","quantity":3,"price":72,"asset_type":"Bond ETF","asset_class":"BONDS","expense_ratio":0.0003}]
goal {"target_amount":20000,"current_savings":5000,"years":5,"annual_return":0.05,"risk_tolerance":"low"}
market AAPL
news recent U.S. mutual fund news
tax Explain traditional IRA vs Roth IRA.
quit
```

Blank questions are skipped; malformed JSON gets a readable message. Regular questions use automatic routing and recent history. CLI market commands are latest-trade-only; historical window selection is in the Market UI or explicit workflow input. Type finance questions at Finnie's prompt, not the shell prompt.

## Samples and errors

samples/portfolio.csv reproduces the $1,466 / $0.44 example. samples/goal.json reproduces $199.74 monthly. All amounts are illustrative USD values, not live holdings or recommendations.

Invalid deterministic inputs raise ValueError; graph/UI wrap these in readable answers. Model routing failures return clarification. News searches without cited evidence return an unable-to-confirm message. Prompt/citation presence alone is not factual verification. Consult setup.md for credential, TLS, model access, cache and resource-path troubleshooting.
