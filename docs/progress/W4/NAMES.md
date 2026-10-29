---
step: NAMES
wave: W4
status: running
pr: null
review: changes
review_score: 10/14
review_ref: "doc-reviewer 2026-10-29, changes 10/14 on 0ca035f; six required changes applied with CR-001 to CR-005 and SEC-1 to SEC-6 (docs/reviews/code/NAMES.md); re-review pending"
---
# NAMES · Prepare the four package-name claims

!!! info "Running 2026-10-29 · branch `autopilot/pypi-name-claim` · Thomas: \"Pour PyPI, prépare-moi déjà ce qu'il faudrait faire dans un fichier ou sur le CI\" · nothing published, no token made, no workflow run · review round on `0ca035f`: code changes 0/1/4, security changes 0/1/5, doc changes 10/14, all applied · open for Thomas: SEC-1's agent deny rules, the placeholder version, the registry provider string, where the logger's catalogue page lives"

![NAMES figure: on the Nextflow registry, Thomas logs in through Seqera and claims nf-spectio with a provider; the claim waits in PENDING REVIEW until an admin approves it, and the approved claim makes the ID his with no release. On PyPI, a pending publisher with owner weber8thomas, repository spectio, workflow pypi-publish.yml and environment pypi-<project> holds nothing; Run workflow on main runs build then publish, only publish has id-token, and the token exchange creates the project before the 0.0.0 upload](../../assets/diagrams/name-claim_light.png#only-light)
![NAMES figure: on the Nextflow registry, Thomas logs in through Seqera and claims nf-spectio with a provider; the claim waits in PENDING REVIEW until an admin approves it, and the approved claim makes the ID his with no release. On PyPI, a pending publisher with owner weber8thomas, repository spectio, workflow pypi-publish.yml and environment pypi-<project> holds nothing; Run workflow on main runs build then publish, only publish has id-token, and the token exchange creates the project before the 0.0.0 upload](../../assets/diagrams/name-claim_dark.png#only-dark)

## What changed

- **`.github/workflows/pypi-publish.yml`, new:** started by hand, one project per run (`spectio`, `spectio-open`, `snakemake-logger-plugin-spectio`), three jobs:
    - `build`: `uv build`, the sha256 of each file as a step output, `dist/` uploaded; then `twine check --strict`, every classifier against `trove-classifiers`, and the wheel's file list against `wheel-contents.txt`;
    - `smoke`: checks the sums and the file count, installs the wheel in a fresh venv, runs `tools/release/pypi-placeholders/smoke.py`;
    - `publish`: only from `main`, in environment `pypi-<project>`, the only job with `id-token: write`; checks the sums again, then `pypa/gh-action-pypi-publish` v1.14.3 with `skip-existing`.
- **`tools/release/pypi-placeholders/`, new:** three working `0.0.0` packages (`uv_build==0.11.32`, MIT, `Repository` URL). `spectio` and `spectio-open` install a command with `--version`. `snakemake-logger-plugin-spectio` is a Snakemake logger that appends one JSON line per log event to `--logger-spectio-file` (default `spectio-events.jsonl`), opened with `O_NOFOLLOW` and mode 0600.
- **`dev/versions.env`:** `TWINE_VERSION=7.0.0`, `TROVE_CLASSIFIERS_VERSION=2026.9.21.13`.
- **`.github/CODEOWNERS`:** `/tools/release/` is code-owned.
- **Guide, new:** [Claim the package names](../../developer/claim-package-names.md): the registry claim, the GitHub environments and `main` protection, the pending publishers, the run, the manual fallback, open points.
- **Spec:** [dev-env §12](../../specs/dev-environment-and-testing.md#12-versioning-and-releases) Publishing: FC-314 to FC-317.
- **Records:** the [name-claim verification](../../reviews/verification-2026-10-29-names.md), the [review record](../../reviews/code/NAMES.md), a [decision-log entry](../../decisions/log.md#2026-10-29-how-the-four-package-names-are-held), a status line on [inbox #66](../../reviews/inbox.md#66-claim-the-four-package-names-and-confirm-how-the-bridges-are-released).
- **Figure, new:** `tools/diagrams/name_claim.py` and its four outputs, in `docs/assets/media.yaml`.

## Why

Thomas, 2026-10-29: "Comment faire pour réserver ces 4 noms de paquets? … Pour PyPI, prépare-moi déjà ce qu'il faudrait faire dans un fichier ou sur le CI. Puis je préparerai ceci moi-même sur le site." The fact-check found that a PyPI pending publisher holds nothing until it is used, so the preparation is a workflow Thomas runs right after adding each publisher, plus packages that do something real (PEP 541).

## How to test it

From the repository root, for one project (`smoke.py` needs the wheel installed):

```bash
uv build --out-dir /tmp/d tools/release/pypi-placeholders/snakemake-logger-plugin-spectio
uv venv /tmp/v && uv pip install --python /tmp/v/bin/python /tmp/d/*.whl
/tmp/v/bin/python tools/release/pypi-placeholders/smoke.py snakemake-logger-plugin-spectio
```

## Evidence

- **Jobs replayed locally** (every `run:` block of the three jobs, in order, with `GITHUB_OUTPUT` and the sums passed on): all steps exit 0 for the three projects; `bogus` stops at `::error::Unknown project: bogus`.
- **Negative checks:**
    - with `Framework :: Snakemake` put back, the build job fails with `invalid classifiers: ['Framework :: Snakemake']`;
    - with an extra line in `wheel-contents.txt`, the build job fails on the `diff`;
    - a file changed after its sum was recorded fails `sha256sum --check` (`FAILED`, exit 1).
- **Smoke:** `smoke: <project> ok` for all three: `--version` prints `0.0.0`; the logger writes one valid JSON line; a symlinked path raises `OSError` and its target stays empty.
- **Real Snakemake run** (snakemake 9.27.1, a one-rule Snakefile): `--logger spectio --logger-spectio-file events.jsonl` exits 0, writes 14 valid JSON lines (`workflow_started`, `run_info`, `job_started`, `job_info`, `job_finished`, `progress`, `resources_info`), file mode `600`. With `events.jsonl` a symlink to a missing file, the run stops with `OSError: [Errno 40] Too many levels of symbolic links` and the target is not created.
- **Linters:** actionlint (the repo's pinned binary, with shellcheck): clean. zizmor 1.31.1 `--offline --min-severity low`: no findings. The online audits need a token and run in CI.
- **Docs:** `python3 tools/docs/check.py --base origin/autopilot/integration` and `mkdocs build --strict`: see the PR's Checks.

## Findings filed

- FC-314 to FC-317 ([verification](../../reviews/verification-2026-10-29-names.md)): applied to dev-env §12.
- CR-001 to CR-005, SEC-1 to SEC-6, doc review 1 to 6 ([review record](../../reviews/code/NAMES.md)): applied, except SEC-1's permission part, open for Thomas.
