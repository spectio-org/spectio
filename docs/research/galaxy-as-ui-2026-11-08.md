# Galaxy as Spectio's UI, with Spectio's backend: an evaluation (2026-11-08)

*Research note, 2026-11-08. Asked by Thomas the same day: "Je veux que tu évalues la possibilité d'utiliser galaxy comme UI en gardant backend spectio, permettrait de bénéficier de tout l'écosystème existant" (evaluate using Galaxy as the UI while keeping Spectio's backend, to benefit from the whole existing ecosystem). No decision is taken here. The question is related to [inbox #17](../reviews/inbox.md#17-features-after-01-wes-trs-seqera-api-galaxy-batches-chaining), which Thomas deferred on 2026-10-27.*

## Sources

- **Galaxy code:** `galaxyproject/galaxy` `dev` at `0924bf1231a36f889f3ccc0676d54e8de5feb50a` (committed 2026-11-08), read from a shallow clone and not run. The newest release branch is `release_26.2`. Paths below are at that commit. The earlier reading at `fd43a3c` is in the [landscape note](landscape-2026-10-26.md#galaxy).
- **Other code:** `galaxyproject/galaxy-helm` at `bd3a9c3` (chart 6.8.9, appVersion 26.1.1); `galaxyproject/tools-iuc`; the Galaxy ToolShed API; `galaxyproject/foundry`; the READMEs of the projects in §3.
- **Web pages:** each one is linked where it is used.
- **Spectio:** the specs named below, and `web/package.json` and `packages/spectio-server/openapi/0.0.1.json` on this branch.
- **Unverified facts** are marked **[to be validated]**. Anything not cited is judgement.

## 1. What "Galaxy as the UI" would have to cover

Spectio's UI is no longer only a design.

- **A UI is already built.** `web/` is "React, Vite, Mantine 7, TanStack Router" (`web/package.json`). Its screens sit over a 0.0.1 API of 19 routes (`packages/spectio-server/openapi/0.0.1.json`): runs, stages, processes, tasks, attempts, files, logs, results, an SSE event stream, and cancel / relaunch / launch-template.
- **The stack was chosen on purpose.** It was picked to share Mantine and the Paper chrome with depictio, and is served by FastAPI from the wheel with no Node in production ([synthesis §7](../specs/synthesis.md); [decision log](../decisions/log.md), "Mantine rather than shadcn/ui").
- **Some screens are specific to Spectio,** and a generic workflow UI would have to provide them:
  - gate review: a queue, item tables with keep / redo / exclude, the changes bar, "Approve and continue" ([ui-spec §4.5](../specs/ui-spec.md); [checking scenarios](../specs/checking-scenarios.md));
  - steering by state: resume as a new run, relaunch, pause after a stage ([ui-spec §4.4](../specs/ui-spec.md));
  - declared or detected stages ([ui-spec §5.1.1](../specs/ui-spec.md#511-detected-stages));
  - scheduler pending reasons and efficiency ([schedulers §10](../specs/schedulers-and-monitoring.md));
  - observed runs and runner-offline states;
  - a separate phone layout ([ui-spec §4.11](../specs/ui-spec.md));
  - depictio branding and an embedded dashboard ([api §13](../specs/api-and-data-model.md)).

## 2. Galaxy's architecture, as far as a UI swap is concerned

### 2.1 The client is a monolith tied to Galaxy's API

- **Stack.** Vue 3.5 under `@vue/compat` with `bootstrap-vue` 2, Pinia, vue-router and Vite (`client/package.json:26-27,83,94,135-136,154,160,224,231`). The build goes to `static/dist` and is served by the Galaxy server (`client/package.json:168,174`).
- **Boot.** The client fetches `${appRoot}context` (`client/src/onload/loadConfig.js:8`, served by `lib/galaxy/webapps/galaxy/api/context.py:33`) and `GET /api/configuration` (`client/src/stores/configurationStore.ts:20`).
- **Typed calls.** They go through `@galaxyproject/galaxy-api-client`, a schema generated from Galaxy's pydantic models of about 58,490 lines (`client/packages/api-client/src/schema/schema.ts`). Even so, about 130 client files still import axios directly, for example to load the workflow graph with `/api/workflows/{id}/download?style=editor` (`client/src/components/Workflow/workflows.services.*:35-41`).
- **The invocation view.** It is built from `invocationStore`, `workflowStore` and `HistoryPageView` (`client/src/components/WorkflowInvocationState/WorkflowInvocationState.vue:9-40`). It calls the following routes (`client/src/stores/invocationStore.ts:23-104`; `client/src/api/invocations.ts:43,63`):
  - `/api/invocations/{id}` and its `/jobs_summary`, `/step_jobs_summary`, `/metrics`, `/request` and `/report`;
  - `/api/invocations/steps/{id}`;
  - `/api/jobs/{id}` and its `/outputs` and `/parameters_display`;
  - the history and dataset endpoints, through `HistoryPageView`.

  The payloads are Galaxy types: histories, HDAs and collections, and workflow steps in "editor" style (`lib/galaxy/schema/`).
- **Reusable packages.** `@galaxyproject/galaxy-api-client` is on npm (26.1.2, 2026-10-26), but it is an API client, not a set of components. The component package `@galaxyproject/galaxy-ui` is `"private": true` (`client/packages/ui/package.json`), and its only other consumer is the Tool Shed frontend (`client/packages/ui/README.md`).
- **No precedent found.** No precedent was found of the Galaxy client running against a non-Galaxy backend **[to be validated]**.

### 2.2 Galaxy's extension points sit below the workflow level

- **Job runners.** A runner executes one Galaxy job, which is one tool command.
  - The contract is `queue_job`, `stop_job` and `recover` (`lib/galaxy/jobs/runners/__init__.py:422-428`), plus polling in `AsynchronousJobRunner` (`:1060,1137,1153`).
  - Runners exist for SLURM, Kubernetes, Condor, the CLI, AWS, GCP Batch and Pulsar.
  - Pulsar has REST, MQ, Kubernetes, TES and GCP Batch variants (`lib/galaxy/jobs/runners/pulsar.py:274-1407`).
- **Workflow modules.** The module types are a fixed dict: `data_input`, `data_collection_input`, `parameter_input`, `pause`, `pick_value`, `tool` and `subworkflow` (`lib/galaxy/workflow/modules.py:3608-3617`). The factory asserts the type is in that dict (`:3595`). There is no plugin registry, so a module that hands work to an external engine would need a patch to Galaxy's core.
- **Pause step.** `PauseModule` raises `DelayedWorkflowEvaluation` until the step's `action` is set (`modules.py:2082-2147`). Approving passes the input through. Rejecting cancels the invocation with `cancelled_on_review`.
  - The action is set with `PUT /api/invocations/{id}/steps/{step_id}`, whose summary says "still very nebulous" (`lib/galaxy/webapps/galaxy/api/workflows.py:1772-1783`). No client call that sends this PUT was found.
  - So this is a pause for each dataset inside a Galaxy workflow. It is not a review with items, checks and evidence.
- **Other languages.** Runtime CWL raises "Runtime support for CWL tools is not implemented currently" (`lib/galaxy/tools/__init__.py:525-526`). The CWL PR [#12909](https://github.com/galaxyproject/galaxy/pull/12909) has been an open draft since 2021-11-12. WES advertises only `gx_workflow_ga` and `gx_workflow_format2` with the `galaxy` engine (`lib/galaxy/webapps/galaxy/services/wes.py:225-232,408-414`). There is no Nextflow or Snakemake support in Galaxy's core.
- **Galaxy-side features a link to Spectio could use:**
  - **Interactive Tools:** `tool_type="interactive"` containers with `<entry_points>` (`tools/interactive/interactivetool_ethercalc.xml:1-9`; `lib/galaxy/config/schemas/config_schema.yml:1738-1769`).
  - **Webhooks:** masthead and other plugins (`config/plugins/webhooks/demo/tool_list/config.yml`).
  - **File sources:** about 45 of them, including S3, SSH, WebDAV, DRS and iRODS (`lib/galaxy/files/sources/`).
  - **Visualizations:** plugins listed in `client/visualizations.yml`.
  - **OIDC:** Keycloak, generic `oidc`, CILogon, EGI and others (`lib/galaxy/config/sample/oidc_backends_config.xml.sample:66-260`). The API also accepts OIDC bearer tokens (`lib/galaxy/webapps/base/webapp.py:555-585`). So Galaxy and Spectio could share one Keycloak realm **[to be validated end to end]**.
- **States.** Job states are `new, resubmitted, upload, waiting, queued, running, finishing, ok, error, failed, paused, deleting, deleted, stop, stopped, skipped` (`lib/galaxy/schema/states.py:33-49`). Invocation states are `new, requires_materialization, ready, scheduled, cancelled, cancelling, failed, completed` (`:81-89`).
  - None of them matches `awaiting_review` or `pausing` (Spectio run states, [api §7.1](../specs/api-and-data-model.md)).
  - None of them matches the head-silent and runner-offline flags.

### 2.3 Running Galaxy takes a lot

- **Default dependencies.** SQLite by default, PostgreSQL through a SQLAlchemy URL (`config_schema.yml:81-88`). AMQP with a fallback to the database (`:4328-4340`). Celery, which is opt-in, but `enable_tool_requests` defaults to true and needs it (`:4342-4362`). 319 pinned Python requirements (`lib/galaxy/dependencies/pinned-requirements.txt`).
- **Helm chart.** It "expects ... cluster-wide operators for postgres, rabbitmq and cvmfs" (`galaxy/Chart.yaml`, `bd3a9c3`). It defines web, job and workflow handlers, Celery, Celery beat, nginx and tusd (`values.yaml:40-981`).
- **Licence.** MIT from 2026-02-25 (`LICENSE.txt`), so licensing does not block any of the options below.

## 3. Existing projects that combine Galaxy with Nextflow or Snakemake

| Project | Approach | Status | Licence | Source |
|---|---|---|---|---|
| FastOMA in tools-iuc | one Galaxy tool runs `nextflow run dessimozlab/FastOMA` | merged 2025-12-26 (#7560) | MIT | `tools-iuc/tools/fastoma/fastoma.xml:32` |
| NCBI EGAPx wrapper | tool wrapper around a Nextflow pipeline, split into prepare and execute steps; returns the Nextflow log and report | active, 2026-10-01 | MIT | `richard-burhans/galaxytools/tools/ncbi_egapx/ncbi_egapx.xml:358-360`; deployment on usegalaxy.* **[to be validated]** |
| stableexpression_galaxy | generates the tool XML from `nextflow_schema.json` for nf-core/stableexpression | pushed 2026-10-12 | none stated | `OlivierCoen/stableexpression_galaxy` README |
| CFSAN / FDA GalaxyTrakr | Nextflow DSL2 pipelines as single tools, with their own conda `cacheDir` | blog post, 2022 | — | [galaxyproject.org news, 2022-08-15](https://galaxyproject.org/news/2022-08-15-making-nextflow-work-with-galaxy-at-cfsan-fda) |
| Naturalis `edentity_metabarcoding_pipeline` | a Snakemake pipeline as one ToolShed tool | updated 2026-10-01, not approved | Apache-2.0 | ToolShed API, `q=snakemake` |
| nftoolmaker | converts nf-core modules to Galaxy tools | "Almost working", stalled 2023-09 | MIT | `fubar2/nftoolmaker` README |
| Galaxy Workflow Foundry | LLM-driven conversion of Nextflow, CWL and papers into Galaxy workflows, validated with `gxwf` | very active, created 2026-04-29, pushed 2026-11-07; extraction defects open on nf-core/rnaseq | MIT | [galaxyproject.github.io/foundry](https://galaxyproject.github.io/foundry); issues #499, #666 |
| Janis translate | converts Galaxy to Nextflow, CWL or WDL; its docs say manual fixes are needed | stalled 2023 | GPL-3.0 | [janis.readthedocs.io](https://janis.readthedocs.io) |
| Galaxy WES plan | WES server for Galaxy workflows only | issue opened 2025-11-18 | MIT | [galaxy#21315](https://github.com/galaxyproject/galaxy/issues/21315) |
| Pulsar and EuroScienceGateway | remote job execution (K8s, TES, GCP Batch); ESG aimed TES at Nextflow and CWL | Pulsar active; ESG ended in 2025; Nextflow use in production **[to be validated]** | Apache-2.0 | [pulsar docs](https://pulsar.readthedocs.io/en/latest/containers.html); [ESG WP3](https://galaxyproject.org/news/2023-01-19-eurosciencegateway-wp3) |
| sapporo-web, for comparison | a generic WES UI over many engines | stale since 2022-09-13, while sapporo-service is active | Apache-2.0 | [landscape note](landscape-2026-10-26.md#sapporo-web) |

**Not found:**

- a Galaxy issue proposing Nextflow or Snakemake as native workflow languages;
- a Galaxy client for an external WES;
- an Interactive Tool that hosts a Nextflow or Snakemake monitoring UI;
- a GCC or BOSC talk specifically on Nextflow–Galaxy interoperability **[to be validated]**.

**Maintainers on record:**

- mvdbeek, 2023-11-08: "You can run anything that can be run as a command line as a Galaxy tool… It will be bad and can't take advantage of scheduling steps individually and tracking the progress, but it'll work." ([help.galaxyproject.org/t/11110](https://help.galaxyproject.org/t/nextflow-as-a-galaxy-module/11110))
- fubar, 2024-08-21: wrapping a whole pipeline is "rarely the right solution", because the job "requires the maximum RAM/CPU required for any subworkflow (!) for the entire duration". ([help.galaxyproject.org/t/13225](https://help.galaxyproject.org/t/nf-core-pipeline-integration-to-local-galaxy/13225))
- jmchilton, 2018: "It should be easier to put smaller, alternative UIs on top of Galaxy." ([galaxy#6408](https://github.com/galaxyproject/galaxy/issues/6408)) This is the opposite direction to the one asked here.

## 4. The options

| | Option | What it takes | What Spectio keeps | Verdict |
|---|---|---|---|---|
| A | **Galaxy's client against Spectio's backend** | emulate `/context`, `/api/configuration`, invocations, jobs, histories and HDAs, plus the axios calls outside the schema; keep up with each Galaxy release | nothing of its UI; gates, stages and the scheduler view have no screen in Galaxy | **not feasible**: the API to emulate is large and moving, and the screens Spectio needs do not exist |
| B1 | **Galaxy as the full stack, with a Spectio run wrapped as a tool** (`spectio launch` in the tool `<command>`) | one tool per pipeline (generated from `nextflow_schema.json`, like stableexpression); outputs collected at the end | execution and gates, invisible from Galaxy: one opaque job, no progress per stage or task | **works, but weak**: the only pattern used in production, and the one maintainers call "bad" |
| B2 | **Spectio as a Galaxy job runner or Pulsar-like endpoint** | implement `queue_job`, `stop_job` and `recover` | same as B1: the runner unit is one tool job | **no gain over B1** |
| B3 | **A new "spectio" workflow module in Galaxy** | patch the closed module dict and the scheduler in Galaxy's core; map gates onto `PauseModule` | partial: a gate becomes a per-dataset pause | **not feasible without upstream**; maintainers are putting their effort into conversion (Foundry), not delegation |
| C | **Coexistence: a bridge between the two products** | a Galaxy "Run on Spectio" tool that calls Spectio's API and returns outputs and a link; a Galaxy file source or BioBlend to push results into a history; shared OIDC; optionally Spectio's UI as an Interactive Tool or a masthead webhook | everything | **feasible and cheap**: Galaxy users reach Spectio, and Spectio's UI stays |
| D | **Borrow the design only** | read Galaxy's invocation graph, galaxy-charts and `PauseModule` as prior art | everything | already done for gates ([synthesis §5](../specs/synthesis.md)) |

## 5. What "the whole ecosystem" would bring

The ecosystem Thomas wants to gain from has these parts:

- the ToolShed's tools;
- training material ([GTN](https://training.galaxyproject.org));
- the public servers usegalaxy.*;
- an existing user base.

All of these are about **Galaxy tools and Galaxy workflows**. Spectio's runs are Nextflow and Snakemake pipelines, so they gain none of it unless they are converted into Galaxy workflows. That conversion is the Foundry's project, and it is a different product.

What Spectio could gain is **reach**: Galaxy users and Galaxy instances could start nf-core pipelines through Spectio. Option C provides that without giving up Spectio's UI.

The public usegalaxy.* servers would also be unlikely to accept long, opaque, whole-pipeline jobs, given fubar's remark on resources **[to be validated with their admins]**.

## 6. Recommendation

1. **Do not use Galaxy as Spectio's UI (A, B3).**
   - Galaxy's client cannot be pointed at another backend without emulating Galaxy.
   - Its model has no place for stages, review gates, steering or scheduler states.
   - Spectio's own UI already runs on a 19-route API.
2. **If Galaxy matters for adoption, plan a bridge (C) after 0.1.** Its shape:
   - a generated Galaxy tool per pipeline that launches through Spectio's API and links back to the run;
   - results returned to the Galaxy history;
   - shared Keycloak.

   This fits the "Galaxy adapter" left open in [inbox #17](../reviews/inbox.md#17-features-after-01-wes-trs-seqera-api-galaxy-batches-chaining), but in the other direction: Galaxy calls Spectio, rather than Spectio driving Galaxy.
3. **Before committing, run a 1-day spike** (`spike/galaxy-bridge`):
   - a local Galaxy 26.1 container;
   - one tool XML that calls `spectio` against a local server on a fixture workflow;
   - outputs back in a history;
   - an OIDC bearer accepted by both sides.

   This would also cover spike 8 of [R9](../reviews/R9-landscape.md) (Galaxy WES and pause).
4. **Raise the idea with Galaxy maintainers before building.** The BioFAIR 2026 interoperability sprint (15-17 Sep 2026, `BiocCodingCollaborations/BioFAIR2026_Sprint`) brought Galaxy and nf-core together. Its outputs are not published yet **[to be validated]**.

## 7. If we do it anyway: the least-bad route

*Added on 2026-11-08, after Thomas's follow-up: "Et si l'on voudrait vraiment le faire ?" (And what if we really wanted to do it?).*

The goal would be that a Galaxy user launches, follows and decides Spectio runs without leaving Galaxy. Spectio keeps execution, stages and gates. Option A, emulating Galaxy's API, stays excluded (§4). The route below keeps Galaxy unmodified, and every piece of it is a published Galaxy extension point. Code references are to Galaxy at `0924bf1`.

### 7.1 The pieces

1. **One Galaxy tool per pipeline, generated from `nextflow_schema.json`.**
   - stableexpression_galaxy already does this generation (§3).
   - Spectio already reads that schema for its launch forms ([ui-spec §7](../specs/ui-spec.md)).
   - The tool's `<command>` is a thin client: `spectio launch … --wait`. It sends the run to Spectio's API, and Spectio's runner executes it on SLURM or Kubernetes.
   - The Galaxy job only waits, so it does not hold "the maximum RAM/CPU … for the entire duration" (§3, fubar). That problem comes from running the whole engine inside the Galaxy job.
   - The client traps the job's termination and calls `:cancel`.
2. **Per-user credentials.**
   - The tool XML's `<credentials>` element injects user-managed variables and secrets into the tool's environment (`lib/galaxy/tool_util/xsd/galaxy.xsd:707,832-844`; API `lib/galaxy/webapps/galaxy/api/credentials.py`).
   - That carries a Spectio token per user, so the run is attributed to the person, not to a service.
   - A shared Keycloak realm (§2.2) is the later step **[to be validated end to end]**.
3. **A `spectio_run` output dataset, plus a visualization plugin bound to it.**
   - A visualization plugin declares the datasets it opens with `<data_sources><data_source><model_class>HistoryDatasetAssociation</model_class><test test_attr="ext">…</test>` (`config/plugins/visualizations/example/static/example.xml:5-10`).
   - The tool would write a small `spectio_run` dataset (server URL and run id) as soon as the run is accepted, rather than at the end **[to be validated: can an output be visible while the job still runs?]**.
   - The plugin, opened on that dataset in Galaxy's centre panel, renders Spectio's own views of the run: stages, tasks, logs and the gate review.
   - The rendering would use the planned embeddable `@spectio/elements` ([api §9](../specs/api-and-data-model.md)), calling Spectio's API directly.
   - **This is the step that puts Spectio's UI inside Galaxy.**
4. **Gates.**
   - The Galaxy job stays `running` while the Spectio run is `awaiting_review`.
   - The decision is taken in the embedded view and posted to Spectio's API.
   - The thin client prints the run's state changes. Galaxy serves running-job output through `GET /api/jobs/{job_id}/console_output` (`lib/galaxy/webapps/galaxy/api/jobs.py:451-470`), so the job panel shows "waiting for review".
5. **Data in and out.**
   - **Inputs:** Galaxy datasets are paths in Galaxy's object store. Spectio's runner must see them through a shared filesystem, or fetch them through Galaxy's API or DRS. On HPC sites, the shared filesystem is the likely case **[to be validated per site]**.
   - **Outputs:** the client lays out Spectio's results for `discover_datasets` (for example `from_provided_metadata="true"`, `lib/galaxy/tool_util/xsd/galaxy.xsd:83`), so they land in the Galaxy history and the next Galaxy tools can use them.
6. **Later, and only with upstream.**
   - **A `SpectioJobRunner`:** an `AsynchronousJobRunner` with `queue_job`, `check_watched_item`, `stop_job` and `recover`, shaped like `lib/galaxy/jobs/runners/kubernetes.py:141,191,717` and loaded through `job_conf`. It would replace the waiting process. Galaxy's runner API is internal and can change with each release.
   - **Stages shown as Galaxy invocation steps:** this needs a new workflow module type (§2.2), so a discussion with Galaxy's maintainers first.

### 7.2 What Spectio would have to add

All of these are already planned or close to it:

- a launch that takes input paths and an `external_refs` entry `galaxy:job/<id>` ([synthesis §7quinquies](../specs/synthesis.md));
- per-user tokens (`spk_…`, [api §6](../specs/api-and-data-model.md));
- `@spectio/elements`, with CORS and `frame-ancestors` for the Galaxy origin;
- a schema-to-tool generator next to the launch-form code.

### 7.3 What is lost compared with Spectio's own UI

The Galaxy route covers launching, following one run and deciding its gates. It does not cover:

- the phone layout ([ui-spec §4.11](../specs/ui-spec.md));
- the review queue across runs, which would need a Galaxy webhook or a link out;
- observed runs not launched from Galaxy;
- the scheduler and efficiency views, unless the plugin embeds them;
- Spectio's branding.

Spectio's own UI would remain the full product. Galaxy would be a second way in.

### 7.4 Effort and next step (judgement)

- **Spike, about 3 days, on `spike/galaxy-bridge`:**
  - Galaxy 26.1 in a container;
  - one generated tool for a fixture workflow;
  - `spectio launch --wait` against a local server;
  - a `<credentials>` token;
  - outputs collected with `discover_datasets`;
  - a stub visualization plugin that shows the run's state through Spectio's API.

  The exit check: launch from Galaxy, see the stage change in Galaxy, cancel from Galaxy, and find the results in the history.
- **Pieces 1–5 in production:** a few weeks, mostly the generator, data staging and `@spectio/elements`. Piece 6 depends on Galaxy's maintainers.

The main risks:

- running two stacks: Galaxy needs PostgreSQL, a message queue, Celery and CVMFS (§2.3);
- data staging on sites without a shared filesystem;
- the visualization plugin API changing between Galaxy releases;
- whether the admins of public usegalaxy.* servers would install a tool that calls an outside service **[to be validated]**.
