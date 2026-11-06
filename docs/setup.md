# Setup and troubleshooting

## Environment and installation

This is a source distribution. Extract the ZIP and open its finnie-submission folder in VS Code or Terminal. Keep articles/, samples/, evaluation/, and scripts/ alongside src/. Install editable from that folder because resource lookup is relative to the source tree.

Python 3.14.5/macOS arm64 is the exercised environment. Code uses Python 3.11+ syntax/types; other interpreters/platforms are not validated. Use Python 3.14 if reproducing this project on the same Mac. Colab was not used for the final Streamlit/FAISS setup and is not an alternative validated deployment.

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

To reproduce installed third-party versions on the tested platform, use `python -m pip install -r requirements-lock.txt` before the editable install. This is a version snapshot, not a cross-platform hash-locked artifact. Pip/build tooling may resolve build dependencies separately.

On Windows, activate with `.venv\Scripts\activate`; this command is provided for orientation, but Windows installation was not tested. macOS/Linux use `source .venv/bin/activate` in each new terminal. Confirm `python --version` and `which python` point at the intended environment.

## Credentials and configuration

Edit .env locally without sharing it. OPENAI_API_KEY enables routing, answers, embeddings, and news. FINNIE_MODEL must identify a model your project can use; news additionally needs web-search tool access. OPENAI_EMBEDDING_MODEL must be the same for indexing and queries. The sample uses text-embedding-3-small.

Alpaca needs both APCA_API_KEY_ID and APCA_API_SECRET_KEY. They are read directly by the provider adapter, not included in ordinary settings or reports. Without credentials, actual quote/history access is unavailable. The trade fallback is visibly simulated; history has no simulated series.

FINNIE_ENV and FINNIE_PROVIDER are display labels. FINNIE_PROVIDER=demo does not select an offline model. The only implemented model client is OpenAI. Environment variables already exported in the terminal take precedence over .env. Restart the process after configuration changes to avoid retaining old sessions/provider caches.

## Run

```bash
python -m streamlit run src/finnie/ui.py
```

Use the local address printed by Streamlit. For CLI:

```bash
python -m finnie.app
```

The source command `python src/finnie/app.py` also works after editable installation. Deterministic Portfolio/Goals views can be used without a model key; Chat routes through the model. Knowledge browsing is local and needs no API access.

The first Finance Q&A/Tax request loads the knowledge base and may embed all captured source chunks. This costs API usage. The ZIP intentionally does not ship that cache. Later identical source/model configurations reuse it. An unavailable API should give a retry message rather than a fabricated source answer.

## Verify

```bash
python -m pip check
python scripts/check_quality.py
python scripts/evaluate_project.py
```

An offline benchmark without a saved index reports no FAISS measurements rather than creating embeddings. `--live --answers` explicitly permits API use for evaluation. See interfaces.md and acceptance-and-performance.md for examples.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| No module named finnie/streamlit/coverage | Activate the project .venv, then install editable with `.[dev]`; use `python -m ...` to select the same interpreter. |
| Sources.json or articles missing | Run from the extracted source tree; retain sibling data folders and use editable installation. A standalone wheel is not this project's supported distribution. |
| OpenAI 403/model_not_found | Choose a FINNIE_MODEL accessible to your API project. A ChatGPT account/model label does not establish API-project permissions. |
| Chat asks for inputs | Supply the target, current savings, whole-year horizon, and assumed nominal return for Goals; supply complete holdings for Portfolio. Missing inputs are not defaults. |
| Changing .env has no effect | Existing exported environment variables take precedence. Restart the process; check variable names without printing secrets. |
| Alpaca quote is simulated | Read its reason: missing pair, 401/403 permission, 429 limit, HTTP 404, DNS/TLS/timeout, or invalid data. Do not treat SIMULATED as a real price. |
| Historical chart unavailable | History request can fail separately from the latest trade. Check symbol/feed permissions and the explanation. No mock bars are generated. |
| Old quote or chart | Check the trade/bar timestamps and cache labels; TTL is 30 minutes. A stale result retains its original retrieval time. A latest trade can legitimately predate retrieval. |
| Certificate verification failure on python.org macOS Python | Run that Python installation's Install Certificates.command, then retry in the project environment. Keep certificate verification enabled. The learner's original TLS issue was resolved this way. |
| Chart has no moving-average segment | SMA20 needs 20 actual observations. Calendar-day windows include weekends/holidays; missing dates are not filled. |
| Goal value differs from an annual-compounding calculator | Finnie uses nominal annual/12 and monthly end-of-period contributions. The 12% example means 1% monthly, not an effective annual 12%. |
| Fee estimate is too large/small | Manual UI uses percentages; CSV/CLI use fractions. 0.03 in manual equals 0.0003 in CSV. Blank means unknown, not zero. |
| Conversation cleared but cached data still used | Clear removes visible session results; source/provider caches have separate lifecycles. |
| News source/date looks wrong | Inspect the actual cited release. Prompt/citation checks do not prove factual accuracy. General explainers belong in Finance Q&A. |

## Scope and deployment

Run locally for the capstone. Binding to a public interface, adding authentication, Docker, MCP, and production traffic controls are outside the verified deployment. Stop Streamlit with Ctrl+C. No trading/write-to-broker endpoints are used. Do not put .env into a ZIP, repository, video, or screenshot.
