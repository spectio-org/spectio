---
icon: material/tag-check
---
# Claim the package names

Spectio needs four names before its bridges can be installed from a terminal: the plugin ID `nf-spectio` on the Nextflow plugin registry, and `spectio`, `spectio-open` and `snakemake-logger-plugin-spectio` on PyPI ([inbox #66](../reviews/inbox.md#66-claim-the-four-package-names-and-confirm-how-the-bridges-are-released); [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) owns the release mechanics). Thomas does every step on the two sites; Claude never publishes. Every fact below was checked on 2026-10-29 in the [name-claim verification](../reviews/verification-2026-10-29-names.md).

![What holds each name, and when](../assets/diagrams/name-claim_light.png#only-light)
![What holds each name, and when](../assets/diagrams/name-claim_dark.png#only-dark)

**In short:**
- **Nextflow registry:** the claim is what makes the ID yours: no release, and no placeholder. That an approved claim holds the ID against anyone else is inferred from the docs, not stated (§1, step 5).
- **PyPI:** only a project that exists holds a name. A pending trusted publisher holds nothing until the workflow has run once.

## 1. `nf-spectio` on the Nextflow plugin registry

1. **Sign in** at <https://registry.nextflow.io/> with "Log in". Sign-in goes through Seqera (GitHub, Google or email); a first login sends an authentication link by email ([plugin registry docs](https://docs.seqera.io/nextflow/plugins/plugin-registry); nextflow `docs/plugins/plugin-registry.mdx:20-26` at `00143fb`).
2. **Decide the provider string first.** The claim's **Provider** must equal `nextflowPlugin.provider` in the plugin's Gradle build, or the first release is refused ([Gradle plugin guide](https://docs.seqera.io/nextflow/guides/gradle-plugin); `gradle-plugin.mdx:24-26`, `plugin-registry.mdx:32-35`). For example `weber8thomas`; it is Thomas's choice.
3. **Claim the ID:** **My plugins**, then **Claim a plugin**. Plugin name `nf-spectio`, Provider as above, then **Submit Request** (`plugin-registry.mdx:28-38`). The ID is the Gradle `rootProject.name` and must match `[a-zA-Z0-9-]{5,64}`; the `nf-` prefix is a convention, not a rule (nextflow-plugin-gradle `NextflowPluginConfig.groovy:133-136` at `cedaf05`).
4. **Wait for approval.** The claim shows as **PENDING REVIEW** under **Pending Ownership Requests** until an admin approves it; approval happens once (`plugin-registry.mdx:40`). How long it takes, and whether a pending claim already blocks others, is not documented **[to be validated]**. Whether the admins expect a public repository is **[to be validated]**.
5. **Once approved, stop.** "Ownership of a plugin is required to publish" (`plugin-registry.mdx:16`) and "You can claim a plugin even if it doesn't exist in the registry yet" (`gradle-plugin.mdx:109-111`), so an approved claim should hold the ID with no release. This is an inference: the docs do not say that a second claimant is refused **[to be validated]**. Do not upload a placeholder: a release needs a README with Summary, Get Started, Examples and License sections and no placeholder text (`gradle-plugin.mdx:82-101`).
6. **Access token: only at the first real release,** because tokens expire. **Access tokens**, then **Create New Access Token**, name, expiry, **Generate token**; it is shown once (`plugin-registry.mdx:44-62`). Whether a token can be limited to one plugin is not documented **[to be validated]**.

## 2. The three PyPI names

### 2.1 Before you start

- **Account:** a verified primary email and two-factor authentication on pypi.org (warehouse `forklift/legacy.py:541-585` at `481006f`; [PyPI two-factor docs](https://docs.pypi.org/your-account/two-factor-authentication/)).
- **The names are still free** on 2026-10-29: 404 on `/simple/<name>/` and on the JSON API, and no similar name in the full index under PyPI's confusable-name rule (`packaging/services.py:578-611`). PyPI's list of prohibited names is not public, so only the first run confirms them **[to be validated on upload]**.
- **What gets uploaded:** a small, working `0.0.0` release of each project, from [`tools/release/pypi-placeholders/`](https://github.com/weber8thomas/spectio/tree/main/tools/release/pypi-placeholders). PEP 541 removes projects with "no functionality" as name squatting ([PEP 541, invalid projects](https://peps.python.org/pep-0541/#invalid-projects)), so each one does something: `spectio` and `spectio-open` install a command that prints its version and what Spectio is; `snakemake-logger-plugin-spectio` is a real Snakemake logger that writes each log event as one JSON line (`--logger spectio`). No source gives a minimum **[to be validated]**.
- **Why `0.0.0`:** a file name can never be uploaded twice, even after deletion (warehouse `docs/user/publishing/troubleshooting.md:19` at `481006f`), so `0.0.1` stays free for the real release.

### 2.2 On GitHub (repository settings)

GitHub facts below were read on 2026-10-29 in [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments), [Managing environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) and [Manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

1. **Protect `main` first.** Branch protection on `main` with code-owner review ([autopilot §8](../playbooks/autopilot.md), inbox #8) is a prerequisite: the workflow and `tools/release/` are code-owned (`.github/CODEOWNERS`), and only protection makes that review binding. Do not run the workflow before it is set.
2. **The workflow reaches `main` through the promotion PR.** This change merges into `autopilot/integration`; "To trigger the `workflow_dispatch` event, your workflow must be in the default branch" (Manually running a workflow), so **Run workflow** appears only after the integration branch is promoted to `main`. The `publish` job also runs only from `main` (`if: github.ref == 'refs/heads/main'`).
3. **Create the three environments before the first run** (Settings, Environments): `pypi-spectio`, `pypi-spectio-open` and `pypi-snakemake-logger-plugin-spectio`. "Running a workflow that references an environment that does not exist will create an environment with the referenced name … the newly created environment will not have any protection rules or secrets configured" (Managing environments), so a missing environment would publish with no approval. For each environment:
    - **Required reviewers:** Thomas. "Only one of the required reviewers needs to approve the job for it to proceed" (Deployments and environments), so no agent's or bot's account is a reviewer, and none is a repository admin.
    - **Deployment branches and tags:** "Selected branches and tags", with the one rule `main`.
    - **Allow administrators to bypass configured protection rules:** unticked. "By default, administrators can bypass the protection rules" (Deployments and environments).
    - **Prevent self-review:** leave it off while Thomas is the only reviewer and starts the run himself; it stops "users who initiate a deployment" from approving it (Deployments and environments).
    - No agent session holds a token of the reviewer's account with `actions:write` or the right to approve deployments: such a token could start the workflow and approve its own run.
    - Then open the environment page and check that it lists these rules.

### 2.3 On pypi.org: one pending publisher per name

For each name, **Your account**, then **Publishing** (`/manage/account/publishing/`), then "Add a new pending publisher", GitHub tab:

| Field | Value |
|---|---|
| PyPI project name | `spectio` (then `spectio-open`, then `snakemake-logger-plugin-spectio`) |
| Owner | `weber8thomas` |
| Repository name | `spectio` |
| Workflow name | `pypi-publish.yml` |
| Environment name | `pypi-spectio` (the `pypi-<project>` that matches the name) |

!!! warning "A pending publisher holds nothing"
    "A 'pending' publisher does **not** create a project or reserve a project's name **until** it is actually used to publish. If … another user registers the project name before you actually publish to it, your 'pending' publisher will be **invalidated**" (warehouse `docs/user/trusted-publishers/creating-a-project-through-oidc.md:28-35`). Run the workflow right after you add each publisher. At most 3 pending publishers can exist at once per account (`accounts/views.py:1952-1971`): exactly the three names.

### 2.4 Run the workflow

Actions, **pypi-publish**, **Run workflow** on `main`, pick the project, run, then approve the deployment to `pypi-<project>`. Three jobs:
- `build` runs only uv and the pinned `uv_build` backend: `uv build`, then uploads `dist/`. No third-party checker runs in the job that produces the files;
- `smoke` works on a downloaded copy and feeds nothing to `publish`: `twine check --strict`, the wheel's file list against `wheel-contents.txt`, then installs the wheel and runs `tools/release/pypi-placeholders/smoke.py` (the CLI's `--version`; for the logger, one event written as valid JSON, a symlink, a hard link or another user's file refused, a loose file tightened to 0600);
- `publish` needs both, runs only from `main`, and alone gets `id-token: write`; it uploads the build job's files with `pypa/gh-action-pypi-publish` v1.14.3. Tool versions are pinned in `dev/versions.env`. The project is created, owned by the account that added the pending publisher, when the workflow exchanges its GitHub token, before any file is uploaded (`oidc/views.py:208-294`). Repeat for the other two names, then check `https://pypi.org/p/<name>`.

After the first run, the pending publisher becomes a normal trusted publisher on that project; later releases use the same workflow file and environment ([dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases)).

### 2.5 Fallback: upload by hand

If the workflow cannot run (the promotion is not merged, the Actions minutes are gone), the names can be taken from a laptop, in one sitting:
1. Make an API token scoped to the whole account (the projects do not exist yet) in Account settings, API tokens (warehouse `docs/user/publishing/publishing-to-pypi.md:21-41`).
2. For each of the three names, from the repository root (`twine==7.0.0` is `TWINE_VERSION` in `dev/versions.env`):
    ```bash
    uv build --out-dir dist/<name> tools/release/pypi-placeholders/<name>
    uvx twine==7.0.0 check --strict dist/<name>/*
    uvx twine==7.0.0 upload dist/<name>/*
    ```
    Username `__token__`; paste the token only at twine's password prompt. Never put it on the command line, in an environment file or in `~/.pypirc`.
3. Revoke the account-wide token as soon as the third upload is done.
4. Then add the trusted publisher of §2.3 on each new project, under Manage, Publishing; publishers on existing projects do not count against the limit of 3.

## 3. Afterwards

- Inbox #66 is answered when the four names are held; tell Claude which provider string the claim used, so `nf-spectio`'s Gradle build matches it.
- The Snakemake plugin catalogue finds the logger by its exact display name `snakemake-logger-plugin-spectio` (snakemake-plugin-catalog `source/collect_plugins.py:188-189` at `d2c11a2`) and warns without a `Repository` URL (`:243-250`). It reads `docs/intro.md` and `docs/further.md` at the root of the `Repository` URL's `main` or `master` branch (`:636-665`), not from the package. In this repository that root `docs/` is the MkDocs site, so the catalogue warns for `0.0.0` until the bridge's catalogue page has a home (open point below).
- TestPyPI is a separate site and holds nothing on pypi.org ([Using TestPyPI](https://packaging.python.org/en/latest/guides/using-testpypi/)); it is not needed here.

## 4. Open points

- **Agent permissions (SEC-1, Thomas decides, [inbox #71](../reviews/inbox.md#71-deny-agent-sessions-the-commands-that-start-or-approve-a-publish)).** The security review proposes that `.claude/settings.json` deny `gh workflow run`, `gh api …/pending_deployments`, `gh api …/dispatches` and `gh run rerun`, so no agent session can start or approve a publish. Claude does not edit its own permissions; until Thomas decides, the environments' required reviewer (§2.2) is the guard.
- **Where the logger's catalogue page lives.** A root `docs/intro.md` kept out of the MkDocs nav, or a separate repository for the bridge ([verification](../reviews/verification-2026-10-29-names.md), open point 9).
- **Choices:** the placeholder version (`0.0.0` proposed) and the registry provider string.
