# Verification of the name-claim procedures · 2026-10-29

**Round:** standalone fact-check for [inbox #66](inbox.md#66-claim-the-four-package-names-and-confirm-how-the-bridges-are-released) · **Date:** 2026-10-29 · **Produced by:** one `fact-checker` run · **Status:** FC-314 to FC-317 applied the same day to [dev-env §12](../specs/dev-environment-and-testing.md#12-versioning-and-releases) ([decision log](../decisions/log.md#2026-10-29-how-the-four-package-names-are-held)); the procedure is the guide [Claim the package names](../developer/claim-package-names.md).

The question: how Thomas claims the Nextflow plugin ID `nf-spectio` and the PyPI names `spectio`, `spectio-open` and `snakemake-logger-plugin-spectio`, and what actually holds each name.

## Sources and commits read

Cloned shallowly on 2026-10-29; the live docs pages and the registry's pages were fetched the same day.

| Source | Revision |
|---|---|
| nextflow (docs) | `00143fb` |
| nextflow-plugin-gradle | `main` `cedaf05`, VERSION 1.0.0-beta.16, tag `v1.0.0-beta.16` = `b388249` |
| nf-plugin-template | `e6d5625` |
| pypi/warehouse | `481006f` |
| python/peps | `fc008c9` |
| snakemake-interface-logger-plugins | `f27aaf1` (v2.1.0) |
| snakemake-plugin-catalog | `d2c11a2` |
| pypa/gh-action-pypi-publish | `v1.14.3` = `7245906fb61fa33a13554f9d5fb856fe61758086` |

## Claims table

| # | Claim | Location | Verdict | Source | Correction |
|---|---|---|---|---|---|
| 1 | The plugin ID is "claimed in the registry once" | dev-env §12 Publishing | partly true | nextflow `docs/plugins/plugin-registry.mdx:14-40` ([live page](https://docs.seqera.io/nextflow/plugins/plugin-registry)) | An admin reviews the claim (PENDING REVIEW until approved, "required only once"); the claim's Provider must equal `nextflowPlugin.provider`. FC-316 |
| 2 | The job puts the key in `$HOME/.gradle/gradle.properties` as `npr.apiKey`, and `make release` publishes | dev-env §12 | verified | `docs/guides/gradle-plugin.mdx:103-123`; nextflow-plugin-gradle `RegistryReleaseConfig.groovy:48-54`; nf-plugin-template `Makefile:28-29` | The current template reads `NPR_API_KEY` from `.env` through a `registry {}` block; `npr.apiKey` still works (`apiKey ?: npr.apiKey ?: NPR_API_KEY`). FC-316 |
| 3 | One trusted publisher and one environment `pypi-<project>` per project, registered before that project's first publish | dev-env §12 | partly true | warehouse `warehouse/accounts/views.py:1952-1971`, `2014-2034`; `docs/user/trusted-publishers/creating-a-project-through-oidc.md:28-35` | One environment per project is required (two pending publishers cannot share owner, repository, workflow and environment), but at most 3 personal pending publishers exist at once, and a pending publisher does not hold the name. FC-314 |
| 4 | Each name "returned 404" on 2026-10-28, so it is free | inbox #66 | partly true | warehouse `legacy/api/json.py:268-269`; `packaging/services.py:578-611` | The JSON API also returns 404 for a project with no release; names are also refused by the confusable-name rule and an admin list. FC-315 |
| 5 | The Snakemake catalogue "lists it from there" | dev-env §12 | partly true | snakemake-plugin-catalog `source/collect_plugins.py:188-189, 243-250, 282-288, 591-592, 636-665` | Literal `startswith("snakemake-logger-plugin-")` on display names; warns without a `Repository` URL; reads `docs/intro.md` and `docs/further.md` at the root of that repository's `main` or `master` branch. FC-317 |

**Status on 2026-10-29, about 09:00 UTC:**
- `GET https://registry.nextflow.io/api/v1/plugins/nf-spectio` returns 404; the full list (109 plugins) has no ID containing "spect". A claimed ID with no release may also return 404 **[to be validated]**.
- The three PyPI names, and their underscore spellings, return 404 on `/pypi/<n>/json`, on `/simple/<n>/` and on TestPyPI. None collides with the full simple index (926,092 projects, serial 42905831) under the confusable-name rule.
- A GitHub search for other uses of `nf-spectio` could not run here (search API 403) **[to be validated on github.com]**.

## Findings

### FC-314 · major · dev-env §12: pending publishers do not hold names, and only 3 can be pending at once

- **Where:** dev-env §12 Publishing ("one PyPI trusted publisher and one GitHub environment (`pypi-<project>`) per project, registered before that project's first publish"); inbox #66.
- **Evidence:** "A 'pending' publisher does **not** create a project or reserve a project's name **until** it is actually used to publish" (warehouse `docs/user/trusted-publishers/creating-a-project-through-oidc.md:28-35`); creating a project deletes other users' pending publishers for that name (`packaging/services.py:768-790`); the project is created at the first token exchange, before any upload (`oidc/views.py:208-294`); "You can't register more than 3 pending trusted publishers at once" (`accounts/views.py:1952-1971`), all at `481006f`.
- **Problem:** about 30 projects cannot all be registered as pending publishers ahead of time, and doing so protects none of the names.
- **Proposal:** §12 says a name is held only once its project exists (first upload, or first use of the pending publisher); publishers are registered at most 3 pending at a time, or added to projects that exist. The limit for publishers registered under a PyPI organization is **[to be validated]**.
- **Found by:** fact-checker
- **Status:** applied (dev-env §12 Publishing, 2026-10-29)

### FC-315 · minor · inbox #66: a 404 does not prove a name is free

- **Where:** inbox #66 Context; dev-env §15.3 req. 12.
- **Evidence:** the PyPI JSON view resolves through a release (`warehouse/legacy/api/json.py:268-269`), so a project with no release also returns 404; a name is also refused when it collides after "ultranormalization" or is on the admin prohibited list (`packaging/services.py:578-611`).
- **Problem:** the availability check of #66 can report a name as free when it is not.
- **Proposal:** check `/simple/<name>/` and the confusable-name rule; for the registry, a claimed ID with no release may still return 404 **[to be validated]**.
- **Found by:** fact-checker
- **Status:** applied (dev-env §12 Publishing; inbox #66 status note, 2026-10-29)

### FC-316 · minor · dev-env §12: the registry claim and release prerequisites are incomplete

- **Where:** dev-env §12 Publishing (`nf-spectio` bullet).
- **Evidence:** admin review, PENDING REVIEW (`plugin-registry.mdx:40`); the claim's Provider equals `nextflowPlugin.provider` (`plugin-registry.mdx:32-35`, `gradle-plugin.mdx:24-26`); a release needs a README with Summary, Get Started, Examples and License and no placeholder text (`gradle-plugin.mdx:82-101`); the ID is `rootProject.name`, `[a-zA-Z0-9-]{5,64}` (`NextflowPluginConfig.groovy:133-136`); the template reads `NPR_API_KEY` (nf-plugin-template `e6d5625`).
- **Problem:** a provider mismatch or a missing README section blocks the first release.
- **Proposal:** §12 fixes the provider string at the claim, says the claim is admin-reviewed and that the approved claim alone holds the ID, lists the README rule, and accepts `NPR_API_KEY` as an environment secret as well as `npr.apiKey`.
- **Found by:** fact-checker
- **Status:** applied (dev-env §12 Publishing, 2026-10-29)

### FC-317 · minor · dev-env §12: what the Snakemake catalogue needs to list the plugin

- **Where:** dev-env §12 Publishing ("the Snakemake plugin catalogue lists it from there").
- **Evidence:** the catalogue keeps only display names starting with the literal `snakemake-logger-plugin-` (`collect_plugins.py:188-189`) and warns without a `Repository` project URL or `docs/intro.md` (`collect_plugins.py:243-250, 282-288`). It clones the `Repository` URL and reads `docs/intro.md` and `docs/further.md` from the root of its `main` or `master` branch (`_get_plugin_git_info`, `collect_plugins.py:636-665`), not from the package, at `d2c11a2`.
- **Problem:** the first upload's `Name` sets the display name; an underscore or capitalised spelling would never be listed.
- **Proposal:** §12 requires the exact name `snakemake-logger-plugin-spectio` and a `Repository` URL, and says that the catalogue page comes from `docs/intro.md` at the root of that repository. In this monorepo the root `docs/` is the MkDocs site, so the `0.0.0` release gets a catalogue warning (open point 9).
- **Found by:** fact-checker
- **Status:** applied (dev-env §12 Publishing, 2026-10-29); the placeholder has the exact name and the `Repository` URL; where `docs/intro.md` lives is open point 9.

## Open points

1. How long a registry claim review takes, and whether a pending claim already blocks others **[to be validated]**.
2. Whether a registry token can be limited to some plugins, and its expiry choices **[to be validated]**.
3. Whether registry admins expect a public repository before approving a claim **[to be validated]**.
4. A GitHub search for existing uses of `nf-spectio` and `spectio` **[to be validated on github.com]**.
5. How much a PyPI placeholder must do to avoid PEP 541 "name squatting": no source gives a threshold **[to be validated]**.
6. The PyPI prohibited-names list is not public; only the first run confirms the names **[to be validated on upload]**.
7. The pending-publisher limit under a PyPI organization **[to be validated]**.
8. Thomas's decisions: the placeholder version (`0.0.0` proposed; `0.0.1` stays free) and the registry provider string.
9. The catalogue page of `snakemake-logger-plugin-spectio`: the catalogue reads `docs/intro.md` at the root of `weber8thomas/spectio`, where `docs/` is the MkDocs site. Either a root `docs/intro.md` (and `docs/further.md`) kept out of the MkDocs nav, or a separate repository for the bridge whose URL is the `Repository` link. P1 Task 26 plans a package-local `docs/intro.md`, which the catalogue would not read. Until then the catalogue warns for `0.0.0`.
