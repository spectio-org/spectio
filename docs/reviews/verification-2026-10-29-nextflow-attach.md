# Verification of how `nf-spectio` attaches to a Nextflow run · 2026-10-29

**Round:** standalone fact-check for [inbox #69](inbox.md#69-nf-spectio-is-enabled-in-a-way-that-breaks-nf-core-runs-or-drops-the-bridge) · **Date:** 2026-10-29 · **Produced by:** one `fact-checker` run · **Status:** decided by Thomas the same day (option (a), refined by FC-318); FC-318 to FC-321 applied to the owning specs ([decision log](../decisions/log.md#2026-10-29-nf-spectio-is-enabled-with-nxf_plugins_default-set-per-run)).

The question: the simplest way to attach `nf-spectio` to a Nextflow run, for the Nextflow community in general, that leaves the pipeline's own plugins alone and keeps Seqera Platform working.

## In plain words

An nf-core pipeline ships its own list of Nextflow plugins and pins their versions (for example `nf-schema@2.7.2`). Nextflow keeps one list only. `-plugins nf-spectio@<ver>`, or a `plugins` block in any added config file, replaces the pipeline's list: its pinned checker is lost, and Nextflow fetches the newest one, which crashes on 26.10.4 and silently drifts on 25.10.9. A block in `~/.nextflow/config` goes the other way: the pipeline's list replaces it, the run works, and Spectio is quietly left out. `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` is added next to the pipeline's list, and Seqera Platform's `nf-tower` is still added after it.

![Three ways to add nf-spectio to a pipeline that pins nf-schema@2.7.2. 1: nextflow run with -plugins nf-spectio replaces the pipeline's list; nf-schema falls to the newest release, so the run fails on 26.10.4 and drifts on 25.10.9. 2: a plugins block in ~/.nextflow/config is replaced by the pipeline's list; only nf-schema@2.7.2 loads, no bridge, no warning. 3: NXF_PLUGINS_DEFAULT=nf-spectio before nextflow run adds the bridge; nf-schema@2.7.2, nf-spectio and, with -with-tower, nf-tower all load. Below: the variable is set per run, by the head script for launched runs, as a one-shot prefix for terminal runs, or as a Seqera Platform Head job variable; the runner's copy in $NXF_HOME/plugins starts with no registry, online or offline; the undocumented merge is checked weekly by nextflow-edge.yml](../assets/diagrams/nextflow-attach_light.png#only-light)
![Three ways to add nf-spectio to a pipeline that pins nf-schema@2.7.2. 1: nextflow run with -plugins nf-spectio replaces the pipeline's list; nf-schema falls to the newest release, so the run fails on 26.10.4 and drifts on 25.10.9. 2: a plugins block in ~/.nextflow/config is replaced by the pipeline's list; only nf-schema@2.7.2 loads, no bridge, no warning. 3: NXF_PLUGINS_DEFAULT=nf-spectio before nextflow run adds the bridge; nf-schema@2.7.2, nf-spectio and, with -with-tower, nf-tower all load. Below: the variable is set per run, by the head script for launched runs, as a one-shot prefix for terminal runs, or as a Seqera Platform Head job variable; the runner's copy in $NXF_HOME/plugins starts with no registry, online or offline; the undocumented merge is checked weekly by nextflow-edge.yml](../assets/diagrams/nextflow-attach_dark.png#only-dark)

## Sources and commits read

Cloned shallowly on 2026-10-29; the Seqera pages were fetched the same day. Empirical checks ran the local Nextflow binaries (26.10.4 build 14435, and 25.10.9) on a toy pipeline whose `nextflow.config` declares `nf-schema@2.7.2`, the pin of nf-core/rnaseq 3.27.0, and read each run's `Plugins resolved requirement=` debug line.

| Source | Revision |
|---|---|
| nextflow | `v26.10.4` = `691b821`, `v25.10.9` = `64d39b0` |
| nf-weblog | `013dac3` (1.2.0 + 2 commits) |
| nf-core/rnaseq `nextflow.config` | 3.27.0 |
| Groovy `ConfigObject.java` | branch `GROOVY_4_0_X` (Nextflow uses Groovy 4.0.33, `gradle.properties:12`) |
| [Seqera HPC compute environments](https://docs.seqera.io/platform-cloud/compute-envs/hpc), [Seqera launch advanced options](https://docs.seqera.io/platform-cloud/launch/advanced) | fetched 2026-10-29 |

## Claims table

| # | Claim | Location | Verdict | Source | Correction |
|---|---|---|---|---|---|
| 1 | `-plugins` replaces the config's plugin list | inbox #69; spike l.120; FC-311 | verified | `nf-cli-v1/.../ConfigCmdAdapter.groovy:350-351` @691b821; `ConfigBuilder.groovy:574-575` @64d39b0; docs `plugins/using-plugins.mdx` | – |
| 2 | A `-c` file with `plugins {}` fails the same way | spike l.121 | verified | merge order home → pipeline → local → `-c` (`ConfigCmdAdapter.groovy:178-218`), `result.merge(config)` (`ConfigBuilder.groovy:261` @691b821); Groovy `ConfigObject.doMerge` overwrites non-Map values (`ConfigObject.java:176-198`) | – |
| 3 | A `$NXF_HOME/config` `plugins {}` is overridden by the pipeline's own | inbox #69; spike l.122 | verified | same merge order; test: resolved `[nf-schema@2.7.2]` only | – |
| 4 | `NXF_PLUGINS_DEFAULT=nf-spectio@<ver>` adds the bridge next to the pipeline's plugins | inbox #69; spike l.123 | verified | `PluginsFacade.groovy:465-472`, `:543-552`, `:621-636` @691b821; `:428-432`, `:451-460` @64d39b0; test, both versions: `[nf-schema@2.7.2, nf-spectio@0.0.1]`, also with `-plugins nf-schema@2.7.2` | – |
| 5 | The list form is undocumented; the docs describe a boolean | FC-312 | verified | `docs/reference/env-vars.mdx:259-261`, `docs/plugins/developing-plugins.mdx:540-542` @691b821; `env-vars.md:163-164` @64d39b0 | The docs also say defaults apply "when no plugins are specified"; the code applies them anyway. FC-319 |
| 6 | A list replaces the plugins inferred from executor and work dir (`nf-amazon`, `nf-google`, `nf-azure`, `nf-k8s`) | inbox #69; FC-312 | partly true | `PluginsFacade.groovy:554-573` @691b821; `FileHelper.groovy:373-386` | Only `defaultPluginsConf` is dropped; tower, wave, cloudcache stay; object-store work dirs start their plugin lazily; `k8s` works on 26.10.4. FC-318 |
| 7 | `k8s` executor with a list fails `Unknown executor name: k8s` on 25.10.9 | FC-312 | verified | test on 25.10.9; `ExecutorFactory.groovy:143` @64d39b0 | On 26.10.4 it does not fail: nf-k8s is bundled (`modules/nf-cli-v1/build.gradle:18`). |
| 8 | A `spectio` config profile can enable the bridge | ui-spec §6 | wrong | `ConfigParserV1.groovy:395` @64d39b0; `NF.groovy:31-32` @691b821; tests | 25.10.9 aborts; 26.10.4 silently ignores the block. FC-320 |
| 9 | `-with-weblog` "deprecated in 26.10 and no longer supported" | synthesis §2 | partly true | `docs/deprecations.mdx:85` @691b821 | Deprecated in 25.04, removed in 26.10. FC-321 |
| 10 | `nf-tower` (Seqera Platform, `-with-tower`) survives a list | question to the check | verified | `PluginsFacade.groovy:474-477` @691b821, `:434-437` @64d39b0; test both versions with `-with-tower`: `[nf-schema@2.7.2, nf-spectio@0.0.1, nf-tower@…]`; 26.10.4 reached the Platform API (401 with a dummy token) | – |
| 11 | A pinned plugin needs the registry | dev-env §12, architecture §13.8 | wrong for a local copy | `PluginUpdater.groovy:274-286`, `:331-335` @691b821; `:234-237` @64d39b0; test both versions, online and `NXF_OFFLINE=true`, with `nf-spectio@0.0.1` not on the registry | A `<id>-<version>` directory already in `$NXF_PLUGINS_DIR` starts with no registry contact. |

## What each option gives

- **`NXF_PLUGINS_DEFAULT` list.** It replaces only the plugins that `defaultPluginsConf` infers: `nf-amazon` (`awsbatch`, `s3://`, `NXF_ENABLE_AWS_SES`), `nf-google` (`google-batch`, `google-lifesciences`, `gs://`), `nf-azure` (`azurebatch`, `az://`), `nf-k8s` (`k8s`), and on 25.10.9 `nf-weblog` (`weblog.enabled`). `nf-tower`, `nf-wave` and `nf-cloudcache` (and on 26.10.4 `nf-seqera`, `nf-agent`) are added after the merge and stay (`PluginsFacade.groovy:474-503` @691b821). Object-store work dirs start `nf-amazon`, `nf-google` or `nf-azure` lazily (`FileHelper.groovy:373-386`; tested `s3://` on 26.10.4). Real losses: the `k8s` executor on 25.10.x, SES mail, weblog inference on 25.10.9; none matters on SLURM with a POSIX work directory. `awsbatch` itself was not reached **[to be validated]**.
- **Seqera Platform.** Seqera's HPC compute-environment page names `NXF_PLUGINS_DEFAULT` as an example of a Head job variable ("Use this target for variables that Nextflow or its plugins read, such as NXF_OPTS, NXF_JVM_ARGS, NXF_PLUGINS_DEFAULT…", [HPC compute environments](https://docs.seqera.io/platform-cloud/compute-envs/hpc)). Pre-run scripts "are executed in the nf-launch script prior to invoking Nextflow processes" ([launch advanced options](https://docs.seqera.io/platform-cloud/launch/advanced)). Whether Platform's launcher passes `-plugins` or sets the variable itself is not documented **[to be validated]**; the variable works with `-plugins` too (tested).
- **Weblog.** No longer in core: `-with-weblog` aborts on 26.10.4 ("no longer supported -- use the 'nf-weblog' plugin", `ConfigCmdAdapter.groovy:480-481`), and `weblog.enabled` no longer loads the plugin (nf-weblog `CHANGELOG.md` 1.2.0; tested "Unrecognized config option 'weblog.enabled'"). It has the same plugin-list problem, posts HTTP only from the head, and sends no `onProcessCreate`, `onFlowBegin`, cached-task or publish events (`WebLogObserver.groovy:140-190`), which [ui-spec §5.1.1](../specs/ui-spec.md) needs.
- **A plugin declared in config so that it merges.** No supported way: inside one file `PluginsDsl.apply` puts the list (`config/parser/v2/ConfigDsl.groovy:348-362`), `includeConfig` replaces non-Map values (`Bolts.groovy:940-953`), and nf-core includes the institutional config (`nextflow.config:331`) before its own `plugins {}` (`:473`). An installed plugin is not enabled by being installed (`LocalPluginManager.groovy:55-61`); `NXF_CLASSPATH` is unsupported since 24.04.7-edge (launcher `nextflow:292`).
- **Trace file, `.nextflow.log`, report.** Core, no plugin, but completed and cached tasks only (`TraceFileObserver.groovy:215-243`), free text, or end of run only. A degraded fallback for a run with no bridge, not a replacement.

## Findings

### FC-318 · major · The `NXF_PLUGINS_DEFAULT` list drops less than inbox #69 says

- **Where:** inbox #69 (Context caveat; option (a) "appending … `nf-amazon`, `nf-google` or `nf-azure` for `s3://`, `gs://`, `az://`"); spike-stage-detection l.123 and FC-312.
- **Evidence:** the list replaces only `defaultPluginsConf` (`PluginsFacade.groovy:543-573` @691b821); `nf-tower`, `nf-wave`, `nf-cloudcache`, `nf-seqera` and `nf-agent` are added after the merge (`:474-503`); object-store work dirs start their plugin lazily (`FileHelper.groovy:373-386`; tested `s3://` on 26.10.4); `k8s` resolves on 26.10.4 because `nf-cli-v1/build.gradle:18` bundles nf-k8s (tested). The list also drops `NXF_ENABLE_AWS_SES` → `nf-amazon` (both versions) and `weblog.enabled` → `nf-weblog` (25.10.9, `:480-481` @64d39b0). Checked 2026-10-29.
- **Problem:** option (a) added head-script logic that is not needed, and #69 did not state that Seqera Platform's `nf-tower` is unaffected.
- **Proposal:** option (a) appends only `nf-k8s`, on 25.10.x with the `k8s` executor; state "keeps `nf-tower`, `nf-wave`, `nf-cloudcache`; Seqera Platform unaffected"; keep `awsbatch` **[to be validated]**.
- **Found by:** fact-checker
- **Status:** applied 2026-10-29 (architecture §13.8, P1 Task 9).

### FC-319 · major · The env-var route relies on code behaviour that contradicts the Nextflow docs

- **Where:** inbox #69 option (a), Recommendation ("relies on an undocumented interface").
- **Evidence:** the docs say "Whether to use the default plugins when no plugins are specified in the Nextflow configuration" (`docs/reference/env-vars.mdx:259-261` @691b821). The code merges the defaults even when plugins are declared (`PluginsFacade.groovy:465-472` @691b821, `:425-432` @64d39b0). Tested: declared `nf-schema` and default `nf-spectio` both start. Checked 2026-10-29.
- **Problem:** an upstream change that aligns the code with its docs would silently drop the bridge for every nf-core run, since they all declare plugins.
- **Proposal:** name the risk in architecture §13.8; a CI job on Nextflow `edge` asserts that a declared plugin and the default one both resolve (dev-env §11); Spectio asks Nextflow upstream to document the list form and the merge (draft below).
- **Found by:** fact-checker
- **Status:** applied 2026-10-29 (architecture §13.8, dev-env §11 `nextflow-edge.yml`); the upstream issue is drafted, not filed.

### FC-320 · major · A config profile cannot enable `nf-spectio`

- **Where:** ui-spec §6 ("or a `spectio` config profile/env set once by `spectio login`"); cli-and-shared-libraries §2 (`engine nextflow config --install`).
- **Evidence:** Nextflow 25.10.9 aborts with "Plugins definition is only allowed in config top-most scope" (`ConfigParserV1.groovy:395` @64d39b0; tested with `-profile spectio`); 26.10.4 (v2 parser, `NF.groovy:31-32`) ignores the block with no warning (tested: resolved `[nf-schema@2.7.2]`); a top-level block in any added config file replaces the pipeline's list (FC-311; `ConfigBuilder.groovy:261`; `ConfigObject.java:176-198`). Checked 2026-10-29.
- **Problem:** whatever `spectio login` writes as config either breaks the run, drops the bridge silently, or replaces the pipeline's pins.
- **Proposal:** remove "config profile" from ui-spec §6 and cli §2; `spectio login` and `engine nextflow` write at most an environment line.
- **Found by:** fact-checker
- **Status:** applied 2026-10-29 (ui-spec §6, cli §2).

### FC-321 · minor · `-with-weblog` was deprecated in 25.04 and removed in 26.10

- **Where:** synthesis.md §2.
- **Evidence:** "`-with-weblog` is deprecated in 26.10 and no longer supported" (synthesis) against `docs/deprecations.mdx:85` @691b821 (deprecated 25.04, removed 26.10); 26.10.4 aborts on `-with-weblog` (`ConfigCmdAdapter.groovy:480-481`); nf-weblog `CHANGELOG.md` 1.2.0: "Starting in Nextflow 26.10, `weblog.enabled = true` no longer loads the plugin automatically". Checked 2026-10-29.
- **Problem:** the "quick prototype" route has the same plugin-list problem as `nf-spectio`, and lacks the events ui-spec §5.1.1 needs.
- **Proposal:** correct the dates in synthesis §2 and note that weblog needs `id 'nf-weblog'` in `plugins` from 26.10.
- **Found by:** fact-checker
- **Status:** applied 2026-10-29 (synthesis §2).

## Open points

1. Seqera Platform's launch command (`-plugins`? its own `NXF_PLUGINS_DEFAULT`?) and the HPC Head job variable need one real Platform launch **[to be validated]**.
2. `awsbatch` with a list, on 25.10.9 and 26.10.4 (the executor stage was not reached) **[to be validated]**.
3. Whether an upstream issue already exists about the list form: GitHub search was unavailable from the checking session **[to be validated]**.
4. `NXF_PLUGINS_DEFAULT` on the EMBL cluster's Nextflow (already open in the [spike note](../research/spike-stage-detection-2026-10-28.md)).
5. Platform cloud compute environments, whose head container has no local plugin cache, need `nf-spectio` on the registry **[to be validated]**.

## Upstream issue draft

Not filed. To be filed on `nextflow-io/nextflow` by Thomas or with his go-ahead, after a search for an existing issue.

> **Title:** Document the list form of `NXF_PLUGINS_DEFAULT` and its merge with declared plugins
>
> `NXF_PLUGINS_DEFAULT` is documented as a boolean: "Whether to use the default plugins when no plugins are specified in the Nextflow configuration" (`docs/reference/env-vars.mdx`). The code also accepts a comma-separated list of plugin IDs with versions, and merges that list with the plugins the configuration declares (`PluginsFacade.groovy`, `defaultPluginsConf` and the merge in `pluginsRequirement`), even when the configuration declares plugins.
>
> This merge is the only way we found to add an observer plugin to a pipeline that pins its own plugins (for example nf-core pipelines pinning `nf-schema`) without replacing that list: `-plugins`, `-c` and `$NXF_HOME/config` all replace or are replaced, and a `plugins` block in a profile is rejected (v1 parser) or ignored (v2 parser). Tested on 25.10.9 and 26.10.4: `NXF_PLUGINS_DEFAULT=nf-foo@0.0.1 nextflow run …` resolves to the pipeline's plugins plus `nf-foo`, and `nf-tower` is still added for `-with-tower`.
>
> Could the list form and the merge be documented as supported behaviour (or, if they are not meant to be relied on, could a supported way to add a plugin next to a pipeline's declared ones be offered)? We would also suggest documenting that a list replaces the plugins inferred from the executor (`nf-k8s` on 25.10.x, `nf-amazon` for SES).
