# Retrieval, routing, news review, and performance — November 5, 2026

## Clarification follow-up

The learner's no-input goal check returned clarification with generic routing wording. GoalInputError now distinguishes goal-validation failures from provider/malformed-routing errors and asks for the four required inputs (or names missing fields). The unchanged graph displays this message directly. Two new regression tests bring the current gate to 91 passing tests and 96.53% combined coverage. The live measurements below and evaluation/results.json retain the earlier 89-test snapshot; no additional model calls were needed for this wording correction.

## Measured results

The final run passes 89 tests and the quality gate: 97.61% statement coverage, 93.96% branch coverage, and 96.60% combined coverage. No production statements are excluded. These measurements cover all 23 Python files under src/finnie.

The live development-set evaluation used the configured gpt-4o-mini router/answer model and text-embedding-3-small query model against 50 source summaries / 59 chunks / 1,536 dimensions:

| Check | Final result | Interpretation |
| --- | --- | --- |
| Expected source in top 3 | 12 / 12 questions | At least one gold source appeared among the first three chunks |
| Mean document recall at 3 | 100% | All designated relevant documents were found, including both IRA comparison sources |
| Top result relevant | 12 / 12 questions | First chunk belonged to a designated relevant document |
| Router checks | 10 / 10 | Expected intents, specified standalone calculation payloads, and independent multi-agent task types matched |
| Generated-answer samples | 3 inspected | Codex source comparison; not independent human scoring or a general accuracy estimate |

The first live routing run passed 9/10 and exposed a real defect: a goal request with no supplied inputs copied illustrative amounts from the prompt. The failure is retained in evaluation/results.json. After removing numeric examples, adding explicit no-default instructions, and validating goal context/payloads, the complete routing/retrieval suite was rerun. The missing-input question then asked for target, savings, horizon, and return instead of inventing them.

These cases were curated during development and are not held out. The post-fix result demonstrates this set's behavior, not universal routing or answer accuracy. Category-constrained retrieval uses the same pre-search topic rule as the app. Citation proximity and complete sentence-level entailment remain imperfect.

Run timestamps are recorded in UTC in the raw evidence (2026-11-06T03:57:20Z for the final run); the client review date in America/Denver is November 5, 2026.

## Exact file changes

### src/finnie/news.py

Removed the fixed October-2026 mutual-fund release shortcut. A valid current-news request now takes the search path rather than returning a topic-specific stored report. Removed the fixed September-2026 BLS citation rewrite; returned citation URLs are preserved instead of being swapped to an unrequested archive page.

The prompt asks for the last 30 days by default, allows an explicitly requested different period, labels older context, and prohibits invented archive URLs. The existing general-explainer redirect, API annotation extraction, missing-evidence response, and safe provider errors remain. This is prompt guidance, not a deterministic date verifier or a guarantee that search results are correct. No live-news factual accuracy claim is made in this run.

### src/finnie/routing.py

Removed illustrative portfolio quantities/prices and savings-goal numbers from the schema instructions. Goal instructions now name required fields, prohibit default values, and request clarification when any required value is absent.

Added _check_goal_context() for single and multi-agent goal tasks. A request with no digits or English number words in its original question or relevant user history cannot supply a numerical goal payload. Prior assistant examples are excluded as input evidence. project_goal() also validates field completeness/types/ranges before the goal task can execute. Fully worded English inputs and explicit numerical follow-ups remain supported.

This guard is coarse: it does not prove the provenance of each value or solve every partially specified request. The model still resolves language and references, so structural validity and numeric-context presence should not be confused with complete semantic correctness.

### src/finnie/rag.py

Added allow_rebuild=True to load_knowledge_base(), preserving existing app behavior. Evaluation calls it with False in offline mode. If source/model inputs changed or no usable current cache exists, offline evaluation raises before any source embedding call. This prevents a local benchmark from silently making paid API requests. Existing cache validation, migration, and fingerprints remain in use.

### evaluation/cases.json — new

Added 12 retrieval questions with source-file gold labels and optional topic filters; 10 router questions spanning six specialists, a follow-up, a topic change, independent multi-agent work, and missing inputs; and three generated-answer review cases with explicit criteria. Gold labels are selected by source coverage rather than generated by the model being evaluated.

The questions are deliberately basic and source-covered. They are a repeatable development set, not a comprehensive benchmark or assurance about unseen questions.

### scripts/evaluate_project.py — new

Default mode runs local microbenchmarks and restores only an already-current saved FAISS index. It makes no API calls. --live permits index rebuilding if needed, batches 12 question embeddings in one request, searches top 3, and makes 10 router calls. --answers additionally produces the three review answers; the personal-tax guard may answer without an LLM call.

Retrieval scoring counts distinct source URLs, preventing multiple chunks from the same article from inflating document recall. Router checks compare the expected intent, specified numerical/holding payloads, and independent task types. A live result below 80% source-hit or router checks exits unsuccessfully. That development-set threshold is separate from the code-coverage gate.

The script writes reports/evaluation.json and reports/evaluation.md. It records UTC time, environment, corpus/model names, per-case results, and timings without credentials. Output files are overwritten by subsequent runs. evaluation/results.json retains this milestone's snapshot, including the initial failure and three reviewed answers.

### Tests and evidence

- tests/test_news.py: replaced the fixed-release expiry assertion with a regression showing a broad mutual-fund request calls search and provider citation URLs are not rewritten.
- tests/test_routing.py: updated the valid goal fixture to include complete user inputs; added two tests for invented defaults, assistant-example contamination, valid user-history/number-word context, and incomplete payloads.
- tests/test_multi_agent.py: made the calculation fixture's user request explicitly include its numeric inputs, so it remains a valid independently supplied task.
- tests/test_rag_pipeline.py: verifies allow_rebuild=False refuses a changed-source index before calling embeddings.
- tests/test_evaluation_tools.py: four new tests check dataset integrity, distinct-document recall, payload preservation, and benchmark warm-up/iteration accounting.
- evaluation/results.json: retained final raw case results, original failure, local benchmarks, current coverage, and three source-comparison notes. These contain public sample questions and source links, not user finances or credentials.
- README.md, docs/evaluation.md, and .agent/PLAN.md: updated current evidence and remaining submission work.

## Local performance measurements

Sequential warm-process microbenchmarks on this Mac's project Python 3.14 environment. Values vary between runs and are not deployment SLAs.

| Operation | Repetitions | Median ms | 95th percentile ms |
| --- | ---: | ---: | ---: |
| Two-row portfolio calculation | 100 | 0.0040 | 0.0043 |
| Five-year goal / 61 rows | 100 | 0.0226 | 0.0245 |
| FAISS top-3 search, precomputed vector | 100 | 0.0473 | 0.0846 |
| Saved index load, validation, fingerprint | 20 | 59.5398 | 63.1663 |

Five warm-up iterations are excluded. The FAISS measurement excludes query embedding and model/API calls. The index-load measurement includes local source/fingerprint reading and cached-index reconstruction. These are small-corpus measurements, not multi-user throughput or end-to-end UI latency. External query-embedding and individual router/answer latencies are separately recorded in the JSON; their variability is not hidden inside local search times.

## Answer review

Codex compared three generated examples against captured source files. This is an assistant review, not an independent teacher/human evaluation.

| Sample | Observation |
| --- | --- |
| 100 at 5% for two years | Correct 105 / 110.25 progression and second-year 5.25 interest, supported by compound_interest_source.md. Citation appears after the explanation rather than next to every step; per-sentence citation formatting remains a limitation. |
| Guaranteed stock doubling next month | Declined to name a winner or guarantee returns. The cited Stocks source supports the related ownership/loss facts. |
| Exact personal tax bill after 401(k) | Declined personal calculation; gave the source-supported general pretax rule with IRS guidance. |

Full answers and case review criteria are retained in evaluation/results.json. No general answer-accuracy percentage is claimed from three examples.

## Reproduce and learner check

Offline tests and coverage:

```bash
python scripts/check_quality.py
```

Offline local benchmarks using the current saved index:

```bash
python scripts/evaluate_project.py
```

Opt-in live evaluation (uses configured API and incurs usage):

```bash
python scripts/evaluate_project.py --live --answers
```

Restart Streamlit, then ask Chat: "How much should I save monthly for my goal?" Expect clarification rather than invented amounts. Next provide: "Target 20000, current savings 5000, five years, assumed nominal annual return 5%." Expect the goal path and the familiar $199.74 monthly result. In News, a recent-mutual-funds question now requires a search; inspect its actual source dates and links rather than expecting the old fixed release.

Overall planning estimate: approximately 92%, not a measured grade. Remaining work is final architecture/setup/API/troubleshooting documentation, clean submission package and setup validation, outstanding learner chart/cache/reset checks, and then the demo video. Independent answer review, broader unseen cases, load testing, and optional MCP/Docker are not claimed.
