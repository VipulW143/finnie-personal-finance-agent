# Coverage foundation checkpoint — November 5, 2026

This document retains the initial 83-test coverage milestone. Current submission results are 97 tests and 96.53% combined coverage; see submission-verification.md and [the subsequent live evaluation and performance checkpoint](acceptance-and-performance.md).

## Measured outcome

The reproducible quality command passes all 83 tests and the configured 80% coverage gate.

| Measure | Result |
| --- | --- |
| Tests | 83 passed (51 before this milestone; 32 added) |
| Statement coverage | 1,339 / 1,375 = 97.38% |
| Branch coverage | 495 / 528 = 93.75% |
| Combined statement/branch coverage | 1,834 / 1,903 = 96.37% |
| Production scope | All 23 Python files under src/finnie, including the main Streamlit script and CLI |
| Excluded statements | 0 |
| Tool | coverage.py 7.17.2 on the project Python 3.14 environment |

The corrected baseline for the original 51-test suite was 63.08% combined coverage. The first exploratory measurement using a package-name source selector did not credit the dynamically executed main UI script. The final configuration uses the entire source directory; it does not omit UI, CLI, API adapters, or failure paths. The trade-validation fixes added a small number of production statements after the baseline.

Coverage shows execution of statements and decision paths. It does not mean that 96.37% of generated answers are accurate or that the project is 96.37% complete. Tests have assertions for behavior and outputs, but live model quality, provider availability, and news correctness remain separate evaluation questions.

## Reproduce

If setting up a new environment, install the optional development extra from the project directory:

```bash
python -m pip install -e '.[dev]'
```

Then run:

```bash
python scripts/check_quality.py
```

The runner uses the current Python interpreter, sets the project working directory, runs the entire unittest suite under branch-aware coverage, writes JSON and HTML artifacts, and enforces the configured threshold. It stops immediately if tests fail; an old coverage report cannot make failed tests appear successful. JSON/HTML generation permits reports below 80% for diagnosis, but the final coverage report command fails the gate below 80%.

Generated files:

- reports/coverage.json — machine-readable totals, missing lines, and branch details.
- reports/coverage_html/index.html — browsable per-file report.
- .coverage — coverage's local measurement database.

These artifacts are ignored by Git; the committed documentation records the checkpoint and the command regenerates evidence. No source exclusions or reduced source scope were used to reach the target. Quality-tool and test code are outside the production coverage denominator, which covers all of src/finnie.

## Exact implementation changes

### Configuration and runner

- pyproject.toml: added optional dev dependency coverage>=7.10,<8; configured branch=true, source=["src/finnie"], relative paths, visible missing lines, two-decimal precision, and fail_under=80. Runtime dependencies are unchanged.
- .gitignore: added .coverage, .coverage.*, htmlcov/, and reports/ to ignore generated artifacts.
- scripts/check_quality.py: added a standard-library subprocess runner. Every child uses sys.executable and check=True. It runs tests first, then exports coverage JSON/HTML, then applies the report threshold. There are no test skips or shortened test subsets in this command.

### Meaningful production fix: src/finnie/market_data.py

Provider-boundary tests exposed permissive latest-trade validation. The previous float conversion accepted boolean prices; zero/negative finite values were not rejected; a timestamp was converted to text without validating it. The parser now requires a non-boolean numeric positive finite price and an ISO timestamp with an explicit timezone. It accepts Alpaca's nanosecond timestamp strings while retaining the original timestamp for display. Malformed data raise the existing safe MarketDataError and follow existing stale/mock behavior.

A non-string ticker now gives ValueError instead of an AttributeError. Cache freshness requires nonnegative age as well as age below 30 minutes, so a future-dated entry triggers refresh instead of being called fresh. HTTP error objects are closed to release response resources. Existing real/cached/stale/mock labels and the historical-data implementation were not replaced.

### New test files — 32 tests

| File | Tests | Behavior checked |
| --- | --- | --- |
| tests/test_foundations.py | 6 | Chunk size and word/list preservation, metadata/IDs, invalid inputs, environment precedence with temporary dummy credentials, SDK argument boundaries, embedding order, index/search alignment, cosine reference and invalid vectors |
| tests/test_cli.py | 1 | A multi-turn CLI session: blanks, malformed JSON/shape, missing command arguments, valid portfolio/goal/market/news/tax requests, history, lazy graph construction, quit |
| tests/test_market_quotes.py | 5 | Valid/invalid trade payloads, HTTP/DNS/TLS/timeouts/decoding failures, fresh/stale/missing-key/provider-failure branches, cache isolation, future timestamps, invalid symbols |
| tests/test_routing.py | 4 | Bounded reference history, standalone topic changes, six specialist payloads, fenced JSON, malformed plans, provider errors, explicit AAPL trade overriding prior tax context |
| tests/test_rag_pipeline.py | 5 | Actual loader/cache round trips; source/model invalidation; legacy migration; cited-only URL deduplication; empty retrieval/output; IRS-only retrieval; prior answers treated as context; no personal 401(k) tax calculation |
| tests/test_news.py | 4 | Citation formats, HTTPS filtering/deduplication/title escaping, blank/background requests, required search call, missing summary/links, provider failures, date limit on existing fixed mutual-fund shortcut |
| tests/test_main_ui.py | 4 | Chat/Finance Q&A history separation and category dispatch, currency preservation, tax topic change/reset, news success/error, all 50 sources and glossary filtering |
| tests/test_workflow_failures.py | 3 | Real LangGraph specialist dispatch, missing/invalid calculator inputs, RAG outages, IRS mode, news-provider failure |

The 51 existing calculator, FAISS, multi-agent, portfolio, history, and dashboard tests still run. Provider SDK calls and HTTP calls are mocked in this quality suite. Tests do not need paid model calls or live market access. Configuration tests use temporary directories and dummy values rather than printing or modifying the user's .env.

The main UI tests mock the workflow boundary to assert view dispatch/state. Separate tests execute the actual LangGraph with controlled provider boundaries. They test complementary layers; they do not imply full live-browser or model-behavior coverage.

## Original-requirement status and evidence

| Requirement | Current evidence | Remaining check |
| --- | --- | --- |
| Six specialized agents | Explicit graph nodes and specialist routing; routing/workflow tests | Broader live conversation/answer acceptance |
| Multi-agent orchestration/context | Two/three-task graph tests; separate payloads/results; tax-to-market regression | Live router semantic accuracy on a fixed question set |
| 50–100 education articles, attribution, vector retrieval | 50 distinct captured source summaries, FAISS, topic filters, source links, 26-term glossary | Summaries are selected material, not full articles; broader semantic recall and answer-faithfulness evaluation |
| Portfolio analysis/dashboard | CSV/manual values, fees, supplied classes, concentration, charts; learner accepted sample | No historical volatility, fund look-through, or personalized suitability claim |
| Market integration/cache/fallback/trends | Alpaca latest trade and historical IEX bars; provider/cache/error tests; live AAPL integration and learner TSLA chart | Learner cached-repeat/history-toggle checks still unconfirmed; no sustained load/API-limit benchmark |
| Goal planning with risk context | Nominal monthly formula, loss-comfort context, zero-return comparison and chart; user confirmed low/high arithmetic and zero-rate output | Learner chart overlap/error/reset checks unconfirmed; no stochastic risk model claimed |
| Test suite and 80%+ coverage | 83 passing tests, 97.38% statements / 93.75% branches / 96.37% combined | Maintain gate as code changes; live correctness is separate |
| Failure handling | Controlled SDK/HTTP outages, malformed input, stale/mock labels, no fabricated historical chart | Real-world provider failures can differ from mocks |
| Documentation/design/setup/sample data | README, per-milestone notes, runnable package, example portfolio | Final architecture/design/API/troubleshooting consolidation and clean setup check |
| Performance benchmarks | None claimed for application latency or throughput | Measure local calculations/retrieval and separately label external API timings |
| Deployment/package and demo | Local Streamlit operation; demo intentionally deferred | Clean submission package/setup validation; then 5–10 minute video. Docker/MCP remain optional |

## Known limitations that coverage does not resolve

- The dated mutual-fund shortcut and BLS URL rewrite identified at this checkpoint have since been removed. Current-news facts still require source/date review; unit tests do not establish live news accuracy.
- RAG tests confirm metadata, filters, cache validity, and displayed citation selection. They do not judge whether every model sentence is entailed by its source. Invalid citation numbers are skipped when building the source list, but complete answer faithfulness is not enforced by that formatting step.
- Router tests validate structured decisions and explicit overrides with controlled model output. A model can still classify unfamiliar wording incorrectly.
- All remaining uncovered statements/branches remain visible in the generated report. These include some corrupt-cache variants, uncommon input/error paths, and the dated BLS rewrite. No exclusions were added to conceal them.

## Next checkpoint

Build a small, reviewable question set for retrieval/routing/answer quality; address the dated-news shortcuts; collect honest performance evidence; consolidate design/setup documentation and package the prototype. The overall project planning estimate is approximately 88%, not the coverage number. Demo preparation begins after submission readiness is established.
