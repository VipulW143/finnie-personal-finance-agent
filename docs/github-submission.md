# GitHub, video and final submission

The supplied submission instruction requires pushing the project to GitHub and downloading that repository as a ZIP for the form. The local allowlisted ZIP is a verified packaging checkpoint; it is not evidence that a GitHub repository exists or was downloaded.

## Deliverables

1. GitHub repository containing source, source summaries/catalog/glossary, configuration templates, tests, evaluation files, samples, README and design/setup/interface documentation. Public is the learner's selected option. Private requires evaluator access.
2. README with architecture overview/diagram, setup/run commands, environment list, test commands, sample usage, and final demo video link.
3. .env.example with comments for every setting; no actual .env or secret values.
4. A 5–10 minute Finnie demo showing multi-turn agents, portfolio analysis, actual market data, goal planning, and the implementation's sources/limits. The personal recording guide is retained locally and is not part of this repository.
5. Final repository ZIP downloaded from GitHub for the form. Supply repository/video URLs in form fields when provided; the README also makes them discoverable from the ZIP. If a separate video-file upload is required by the form, attach the recording there as well.

Docker is optional; do not delay the required repository/video for it. The local prototype has no Docker or MCP deliverable claimed.

## Publication sequence

- Prepare the public repository, proposed name finnie-personal-finance-agent. The public repository has been created under VipulW143: https://github.com/VipulW143/finnie-personal-finance-agent. The authenticated connector is available for file publication.
- Upload/commit the actual project files at repository root. Do not upload only the ZIP file. The files should be browsable on GitHub with README.md at the root, not buried inside an extra ZIP or course-download directory.
- Use the explicit packaged source set or equivalent exclusions, rather than adding the entire course folder. Exclude .env, .venv, .finnie, caches, reports, dist, build metadata and original course reference documents. Include the 50 captured education summaries and citations.
- Check the rendered README/architecture, a source file, article catalog, .env.example and test instructions. For a public repository, verify it opens without your account session.
- Rehearse/record the demo against that code. Upload the recording with evaluator-readable access.
- Add the actual video URL to README.md and push the update. Any code fix made while rehearsing must also be tested, committed and pushed before the final archive download.
- From GitHub's repository Code menu, choose Download ZIP after the final commit. Check the downloaded archive contains the final README/video URL and required folders. Keep the repository URL, video URL and the final commit identifier with your submission record.

The video can be referenced by a link in the README instead of storing a large recording in the code repository, provided the evaluator can access it and the form has no stricter upload requirement. The ZIP alone cannot prove the video is accessible; test its link permissions.

Official references: [create a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository), [download source code archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives).

## Current status

Local implementation/package checks passed: 97 tests and 96.53% combined coverage, installation in a disposable Python 3.14.5 environment, and CLI/headless Streamlit startup. The public GitHub repository is https://github.com/VipulW143/finnie-personal-finance-agent. The 9-minute-9-second recording is published at https://github.com/VipulW143/finnie-personal-finance-agent/releases/tag/demo-video, and README.md links to its download. The video is a release asset, not embedded in source archives. Submit a ZIP downloaded from the final main branch; attach the video link/file separately if the form requests it. New recording/submission guide files were added after the verified local ZIP checkpoint; that older local ZIP is not the final submission archive.
