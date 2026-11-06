# Finnie demo video — target 8–9 minutes

This is a recording/rehearsal guide, not a claim that a video has been recorded. Use illustrative inputs. Show the route labels, source links, timestamps, charts and assumptions so the evaluator can connect the interface to the implementation. Expected numeric results below refer to the supplied fixed calculator examples; market/news results change.

## Before recording

1. Start the project with `python -m streamlit run src/finnie/ui.py` in the activated project environment.
2. Rehearse a cited question to build/reuse the knowledge index and verify model access. Check one market request and one news search. Rehearsal results are not substitutes for showing real labels during recording.
3. Open the GitHub README with its architecture diagram, the Streamlit app, and a terminal at the project folder. Prepare samples/portfolio.csv.
4. Close .env and any account/key screens. Capture the app window and your narration; no credentials are needed on screen.
5. Use Clear conversation and results to start with a clean visible session. Cached source/provider data can remain; describe cache labels honestly.

## 0:00–0:35 — Introduce the project

Show: app title and sidebar.

Say: “Finnie is my Agentic AI capstone. It provides general finance education through six specialists: Finance Q&A, Tax Education, Portfolio Analysis, Market Analysis, Goal Planning and News Synthesis. It combines source retrieval and model responses with deterministic calculations and live provider data.”

Do not describe it as a production investment adviser, guaranteed predictor, or autonomous trading platform.

## 0:35–1:10 — Architecture and knowledge

Show: rendered README architecture diagram, then Knowledge in Streamlit.

Say: “LangGraph routes each request to the relevant specialist. Education uses a curated source library and FAISS search; calculators run in Python. Alpaca supplies IEX market data, and news uses a search tool.”

In Knowledge, show the 50 captured source summaries and 26 glossary entries. Switch Browse to Glossary and search `compound`. Open its definition and source link. Explain that these are selected source summaries, not 50 full downloaded articles.

## 1:10–2:05 — Multi-turn finance conversation

Open Chat. Ask exactly:

> Explain how 100 earning 5% annual compound interest becomes 110.25 after two years.

Show: route finance_qa, first-year/second-year explanation, and SEC citation. Expected example is 100 → 105 → 110.25; second-year interest is 5.25.

Follow up in the same Chat:

> How much of that second-year interest is interest on interest?

Expected: 0.25, supported by the compound-interest source. Point out the reference “that” and retained context. Describe what the actual answer says; if it reports insufficient evidence, do not pretend it answered correctly.

## 2:05–2:50 — Switch topics to the tax specialist

Still in Chat, ask:

> Explain traditional IRA vs Roth IRA.

Show: route tax_education and IRS links. Explain that changing topic changes the selected specialist.

Then ask:

> Calculate exactly how much federal tax I owe on a salary of 85000 after a traditional 401(k) contribution of 5000.

Expected: declines a personal tax-bill calculation and explains only the general pretax contribution rule with IRS guidance. This is an educational boundary, not a tax calculator failure.

## 2:50–3:40 — Portfolio dashboard

Open Portfolio → Upload CSV. Choose samples/portfolio.csv and click Analyze uploaded portfolio.

Show:

- Total value $1,466.00.
- VTI 85.3%, BND 14.7%.
- Supplied asset classes STOCKS/BONDS.
- Estimated annual fund expenses $0.44.
- Both allocation charts and the positions table.

Say: “These numbers come from Python calculations on supplied quantities, prices and fees. ETF is a fund structure; asset class is a separate user label. The concentration measure describes supplied instruments, not the underlying holdings of the funds.”

Optional if time permits: mention duplicated ticker lots combine before concentration.

## 3:40–4:40 — Actual market data, history and cache

Open Market. Enter `AAPL`, keep Include daily price history enabled, select `90`, and click Get market overview.

Show: route market_analysis, price, trade timestamp, retrieval timestamp, feed/freshness labels, daily-close/SMA chart and observation dates. Use the actual values shown; do not rehearse a fixed market price.

Say: “The latest available trade and the historical daily bars are separate requests. IEX is one exchange. Daily history is split-adjusted and excludes the current UTC date. The moving average and drawdown describe the observed window; they are not predictions.”

Submit again promptly to show the cached-history label. Then uncheck Include daily price history and submit once to show quote-only output without the earlier chart. This also completes two outstanding manual acceptance checks.

If the response says stale or simulated, explain that status. A $100 SIMULATED fallback must not be presented as a real quote. Rehearse provider access before recording if you need to demonstrate successful market retrieval.

## 4:40–5:40 — Goal planning and assumptions

Open Goals and enter:

| Field | Value |
| --- | --- |
| Target amount | 20000 |
| Current savings | 5000 |
| Years | 5 |
| Assumed annual return (%) | 5 |
| Comfort with losses | Low |

Click Project savings goal. Show $199.74 monthly, $20,000.33 projected, the three-line chart and monthly table. The same contribution at 0% ends at $16,984.40, a $3,015.60 shortfall.

Say: “This uses a nominal annual rate divided by 12 with month-end contributions. Loss comfort adds context without choosing a return or investment. The zero-return line illustrates assumption sensitivity; it is not a guaranteed downside floor.”

Change return to `0` and submit: expect $250.00 monthly and overlapping balance paths. Point out the overlap. Return to 5% if desired.

## 5:40–6:25 — Explicit multi-agent orchestration

Return to Chat. Ask exactly:

> Explain compounding in investing, and separately calculate the monthly contribution for a target of 20000 with 5000 saved over five years at an assumed 5% nominal annual return.

Show: route multi_agent, Finance Q&A and Goal Planning sections, source citation and $199.74 monthly result.

Say: “The router creates two independent tasks. LangGraph executes them sequentially, clears task-specific payloads between specialists, and combines their results. The model does not perform the savings arithmetic.”

Do not call this parallel execution; the implementation is sequential and supports at most three independent tasks.

## 6:25–7:05 — News specialist

Open News and ask:

> Find recent U.S. mutual fund news from the last 30 days. State publication dates and cite direct sources.

Show: route news_synthesis, actual dates and links. Open one cited source briefly if possible and check that the story and date correspond.

Say: “News uses current search and provider citations. Fixed topic-specific releases were removed. Source links and prompt instructions improve traceability, but they do not guarantee every generated claim is correct.”

If no cited reporting can be confirmed, show the unavailable response honestly. Do not substitute fabricated headlines or market claims. Use the rehearsal to confirm the search is functioning before recording.

## 7:05–7:45 — Tests, evidence and reset

In the terminal, run:

```bash
python scripts/check_quality.py
```

Show the final result: 97 passing tests and 96.53% combined coverage at the current checkpoint. Explain that these are offline tests with controlled provider responses; coverage measures execution, not answer accuracy.

Point briefly to evaluation/results.json or the README evaluation summary: 12 retrieval questions and 10 router cases in a small development set. Mention that testing found and fixed a goal-defaulting bug, rather than claiming universal accuracy.

Return to the app, click Clear conversation and results, and show that visible chats/calculation results clear. Caches have separate lifecycles.

## 7:45–8:15 — Close

Say: “This prototype demonstrates all six specialists, source-backed education, multi-turn routing, independent multi-agent plans, deterministic portfolio/goal calculations, provider caching and failure handling, and charts. The repository includes setup instructions, a credential-free environment template, tests and evaluation evidence. Limitations include source-summary depth, model/citation errors, single-exchange data, and no production hosting or personalized advice.”

End with the GitHub repository and demo link visible in the README once the recording is uploaded. No need to show every source file, pip installation, or the entire test log.

## After recording

1. Keep the video between 5 and 10 minutes; review audio and readability.
2. Upload it to a location the evaluator can view without requesting access, such as an unlisted video or link-accessible file.
3. Add the actual video URL to README.md. Do not leave a placeholder presented as a completed video.
4. Commit/push the final files to GitHub. Confirm repository/video access using a signed-out/private browser where applicable.
5. Download the final repository ZIP from GitHub after that commit and use that ZIP in the submission form. If the form requests a separate video upload or link, supply it there too.
