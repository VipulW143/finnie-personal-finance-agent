# Submission verification — November 5, 2026

## Package and installation contract

The deliverable is dist/finnie-submission.zip, an editable **source** distribution. It includes src/finnie, the article catalog and summaries, glossary, tests, scripts, evaluation evidence, sample data, documentation, pyproject.toml, requirements files, and a credential-free .env.example. It is not a wheel with bundled package data.

The builder uses an explicit allowlist, rejects included symbolic links and obvious key-like literals, writes a per-file SHA-256/byte-size manifest, tests ZIP CRC integrity, and writes a separate archive SHA-256. These checks reduce accidental packaging mistakes; they are not a general secret-detection guarantee. The actual .env is never traversed or read by the builder. Virtual environments, caches, generated reports, build metadata, and course reference documents are outside the inclusion list.

Rebuild with `python scripts/build_submission.py`. The ZIP extracts into finnie-submission/. Install there with `python -m pip install -e '.[dev]'`; resources are resolved relative to that source tree. Review README.md and docs/setup.md before supplying credentials. Do not upload .env or cached provider/source state.

## Verification record

Verified on this Mac with Python 3.14.5 in a newly created virtual environment, independent of the project's original .venv. The first dependency install populated that disposable environment; after adding the isolation guard, verification was completed with the same isolated dependencies and a new extraction of the ZIP. No original-environment site packages or source index were used.

| Check | Result |
| --- | --- |
| Archive allowlist, CRC and manifest hashes | Passed |
| Third-party snapshot installation | Passed in disposable .venv |
| Editable project installation from extracted source | Passed |
| python -m pip check | No broken requirements |
| Imported package location | Confirmed under extracted src/finnie, not original workspace |
| Catalog and sample goal | 50 sources; expected $199.74 payment |
| Credential/cache isolation | No .env or prebuilt .finnie index in extracted package |
| Offline test/coverage command | 97 tests passed; 97.56% statements, 93.82% branches, 96.53% combined |
| Offline benchmark | Calculations passed; missing FAISS cache reported as unavailable without API calls |
| CLI startup/quit | Passed without credentials |
| Headless Streamlit | Loopback health endpoint returned ok; AppTest separately exercised app views |

No hosted deployment, other OS, other Python version, or live API traffic from the credential-free clean environment is claimed. The lock snapshot is not a universally portable dependency guarantee. Streamlit health proves server startup, not independent visual inspection of every view.

The final ZIP is checked again after documentation finalization. Its separate dist/finnie-submission.validation.json record binds that run to the delivered archive SHA-256; dist/finnie-submission.zip.sha256 provides a convenient checksum. Both are generated outside the ZIP to avoid a self-referencing hash. Reports and temporary verification directories are not part of the source package.

## Remaining manual checks and demo

The learner confirmed the portfolio numbers/charts, TSLA historical summary/chart, low/high goal context and zero-rate amounts, and clarification followed by an explicit $199.74 goal result. Explicit confirmation is still absent for goal chart overlap/error/reset and market cached-history repeat/history-toggle behavior. Automated tests cover these paths, but that is distinct from browser acceptance.

Use the new environment without credentials for deterministic sample calculations and offline tests. Add your own local API credentials only if running live Chat/RAG/news/market checks. The first cited-answer request rebuilds the excluded source cache and incurs embedding usage.

After final manual checks, prepare the required 5–10 minute demo. Docker/MCP are optional and are not claimed. Source/answer fidelity and all model decisions cannot be guaranteed by the small development set or coverage score. No production hosting/authentication or concurrent-load validation is included.

## Exact packaging and documentation changes

- README.md: replaced stale mixed-status instructions with a reviewer-facing entry point, setup, configuration, feature examples, evidence links, limits and packaging commands. The prior text is preserved in docs/learning-history.md.
- docs/setup.md: environment, editable source install, credentials, runtime commands, verification, and symptom-based troubleshooting. Explicitly documents that FINNIE_PROVIDER is a display label, not an implemented provider switch.
- docs/technical-design.md: Mermaid data flow, module responsibilities, state/message contracts, sequential multi-agent execution, retrieval/cache design, calculation assumptions and performance limits.
- docs/interfaces.md: actual Python/CLI interfaces and input schemas; no nonexistent REST/MCP API is claimed.
- .env.example: blank credential fields and implemented setting names only.
- requirements.txt: delegates runtime dependency ranges to the editable project. requirements-lock.txt records exact installed third-party versions on the tested platform; no editable absolute workspace path is included.
- pyproject.toml: added package description, README metadata and Python code minimum; runtime dependency ranges are unchanged.
- samples/goal.json: reproducible goal example alongside the existing portfolio CSV.
- scripts/build_submission.py: explicit allowlist, linked-path/key-like-literal rejection, file hashes/byte sizes, ZIP integrity check, atomic output and archive checksum.
- scripts/validate_submission.py: manifest/path/hash checking, isolated source extraction, optional dependency install, actual source/resource assertions, quality command, offline benchmark, CLI and headless health check. It preserves symlinked venv interpreter paths and refuses a base interpreter before pip can run.
- tests/test_submission.py: six tests for exclusions, included-file hashes, missing/linked files, tampering, unexpected paths, key-like literals, and real symlinked-venv/base-interpreter behavior (some cases share one test). No actual .env is opened.
- .gitignore: ignores dist/build/install metadata in addition to existing secrets/caches/reports. .agent/PLAN.md records this milestone and the next demo/acceptance checkpoint.

Reproduce archive-only validation with `python scripts/validate_submission.py`. To create a new disposable environment and repeat installation/startup checks, run `python scripts/validate_submission.py --install`; this downloads dependencies and opens a temporary loopback server. It makes no live finance/model requests. Use --python only with a disposable venv whose package installation may be changed.
