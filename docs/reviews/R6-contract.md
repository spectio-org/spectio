# R6 · API contract review (2026-10-27)

**Step page:** [R6](../progress/W2/R6.md)

**Round:** R6 (API contract) · **Date:** 2026-10-27 · **Found by:** spec-reviewer, ux-reviewer · **Status of the round:** open, waiting for triage

**Sources.**
- **Scope.** The 0.0.1 API contract only ([`mvp-0.0.1.md`](../specs/mvp-0.0.1.md), [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15.1): the OpenAPI draft written by the R6 spike, checked against [`api-and-data-model.md`](../specs/api-and-data-model.md), the other specs it depends on, and the ten 0.0.1 boards.
- **The draft.** `spikes/openapi-draft/openapi.yaml` and `spikes/openapi-draft/README.md` on branch `autopilot/R6` (commit `b9c01fd`). It is a throwaway OpenAPI 3.1 skeleton written by hand from the specs. Where the specs are silent or contradict each other it writes the smallest guess and marks it `x-spec-gap` (43 entries). It leaves out pause and resume, the manifest, change sets, artefacts, webhooks and summaries.
- **Spec line numbers** ("l.") refer to `autopilot/integration` at `b2804e4`; the reviewers read the same spec text in the R6 worktree. Draft line numbers refer to `openapi.yaml` at `b9c01fd`.
- **How draft gaps are cited.** `gap #n (l.x)`: n counts the `x-spec-gap` keys in file order, starting with l.39 (the comment on l.5 is not counted); l.x is the line of that key. The spec-reviewer cited lines, the ux-reviewer cited ordinals; both are shown here. The full list is in [Appendix A](#appendix-a-x-spec-gap-to-finding-map).
- **Reviewers dispatched:**
  - **spec-reviewer:** the draft and its README against [`api-and-data-model.md`](../specs/api-and-data-model.md), [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md), [`ui-spec.md`](../specs/ui-spec.md), [`checking-scenarios.md`](../specs/checking-scenarios.md), [`synthesis.md`](../specs/synthesis.md), [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md), [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md), [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md), [`authentication-and-access.md`](../specs/authentication-and-access.md), the [inbox](inbox.md) and [R5](R5-security.md). It placed every one of the 43 gaps.
  - **ux-reviewer:** the ten boards of `mvp-0.0.1.md` §2 (Launch, LaunchSnakemake, RunsTable, RunsRows, RunDetail, Legend, RelaunchDialog, RunsCompare, Manifest, ReviewReport), plus EnvLocal for context, each rendered at 1440×1180 with `tools/canvas/render.js` and looked at. Every number, list, label and action was checked against the draft. Renders were written to `/tmp/r6-ux/` and are not kept in the repository.
  - Both reviewers returned a full report. None failed.
- **External facts.** No external code was read in this round. Claims about Nextflow and Snakemake behaviour (task totals, `storeDir`, Snakemake `log:`, the CloudEvents sequence extension) keep the **[to be validated]** mark the reviewers gave them.
- **Earlier rounds.** Open findings of [R1](R1-consistency.md), [R3](R3-journeys.md), [R4](R4-constraints.md), [R5](R5-security.md), [R7](R7-ui.md) and [R12](R12-ui-scenarios.md) are cited, not repeated. Where an R6 finding extends one, it says so in its **Where** or **Related** line.

**Merge method.**
- **Input:** 34 findings. spec-reviewer returned 12 (12 majors) as SR-080 to SR-091, and 4 questions. ux-reviewer returned 22 (17 majors, 5 minors) as UX-270 to UX-291. Every original ID is kept.
- **De-duplication:** no finding was merged. Where an SR and a UX finding ask for the same endpoint or field from the two sides (spec text, board), both are kept and each carries a **Related:** line naming the other. They should be triaged together.
- **Verification:** the reviewers checked each finding against the spec text with file:line references. During the merge, ten of the quoted spec passages (api l.166 and l.311, architecture l.514, ui l.163, synthesis l.220, cli l.49, mvp l.11, auth l.43, dev-env l.481, checking l.394) were reopened at `b2804e4` and all reproduced. The draft's `x-spec-gap` lines and its path list were re-extracted from `b9c01fd` and match both reports. **0 findings were dropped and 0 were downgraded.**
- **Corrections made during the merge:**
  - Both reviewers wrote while [R3](R3-journeys.md) was still a scratchpad draft. R3 is now merged, so references were updated to its final IDs: UX-242 is merged into SR-062 (relaunch at a gate), UX-245 into CH-047 (RunFailed and `sacct`), UX-247 into SR-055 (EnvLocal), and SR-060 into CH-042 (`launches.until_stage`). UX-250 (compare reachability) stays its own finding.
  - The spec-reviewer counted "37 gaps in new findings, 6 in existing R3 findings". The map itself gives 40 gaps placed in an R6 finding (4 of them, l.74, l.249, l.560 and l.1070, also shared with an R3 finding) and 3 placed only in an existing R3 finding (l.136 SR-065, l.311 SR-064, l.1042 SR-055). Appendix A uses the corrected count.
  - UX "gap N" references were rewritten as `gap #N (l.x)`.

Format: [`README.md`](README.md). Prefixes `SR`, `UX`. Specs were not edited in this round.

## Summary

![R6 round map: the 0.0.1 API draft against five 0.0.1 screens, each gap pinned with its finding ID](../assets/diagrams/r6_contract_map_light.png#only-light)
![R6 round map: the 0.0.1 API draft against five 0.0.1 screens, each gap pinned with its finding ID](../assets/diagrams/r6_contract_map_dark.png#only-dark)

| Severity | spec-reviewer | ux-reviewer | Total |
|---|---|---|---|
| Blocker | 0 | 0 | 0 |
| Major | 12 | 17 | 29 |
| Minor | 0 | 5 | 5 |
| **Total** | **12** | **22** | **34** |

Merged as duplicates: 0. Dropped as not reproducible: 0. Questions for Thomas: 5.

**No new blocker.** The items that really block the 0.0.1 contract are already open as blockers elsewhere, and several R6 findings extend them:
- **[SR-054](R3-journeys.md) (R3):** the ingest contract (api §14) is parked as "not needed for 0.0.1". SR-080 lists what a bridge author still lacks beyond SR-054's subset.
- **[SR-062](R3-journeys.md) (R3):** "relaunch with changed parameters" from a gate is two incompatible flows. SR-081, SR-085 and UX-284 depend on its answer.
- **[SEC-102](R5-security.md) (R5, inbox #15):** `single` mode trusts loopback. SR-091 shows that its browser half applies to every 0.0.1 laptop.
- **[SR-001](R1-consistency.md) (R1, inbox #11):** the ingest credential and contract. SR-080 and SR-054 share its root.
- Other R3 blockers these findings lean on: SR-055 (local environment, default `environment_id`) and CH-042 (run state machine, source states of run actions).

**Main themes.**
- **The ingest contract does not exist.** The draft had to invent the batch envelope, the acknowledgement, the heartbeat and the engine event vocabulary (SR-080).
- **The run's inner structure has no contract.** No stages resource, no stage-state enum, no single stage identifier, no task or attempt state enum, and the Legend board implies enums the draft does not match (SR-082, SR-083, UX-290).
- **Run actions and relaunch are under-specified.** Source states and responses, a fourth spelling of the relaunch modes, the lineage shape, resource overrides and the relaunch preview (SR-081, UX-280, UX-281, UX-282, UX-289).
- **The 0.0.1 gate cannot be served end to end.** No `run` filter, check values without thresholds, unclear If-Match, no read of a decided gate, and the only gate board's primary button needs a change set (SR-085, UX-283, UX-284, UX-285).
- **Boards need summary fields that the `Run` resource lacks.** Workflow name and engine, progress context, task totals, timestamps and meta fields cost 3 to 5 calls per list row (UX-270 to UX-273, UX-288, SR-088).
- **Wire conventions, events and SSE frames are unstated.** List envelope, defaults, Idempotency-Key, ID prefixes, the problem-type catalogue, SSE-only frames with no sequence, and no per-type data schemas (SR-090, SR-084).
- **Spec endpoints the draft dropped.** `runs:summary`, `gates:summary`, `/version`, the manifest, `/runs/{id}/samplesheets`, `/gates/{id}/items` and artefacts are listed in api §5 but cut from the draft; several boards need them (UX-274, UX-275, UX-278, UX-279, UX-285, UX-286; question 5).
- **Security.** A token-less loopback API on a laptop can be driven by any web page through DNS rebinding or CSRF (SR-091).

**All findings.**

| ID | Sev. | Title | Related |
|---|---|---|---|
| SR-080 | major | Ingest §14: the wire items the draft had to invent, beyond SR-054's subset | UX-272, UX-288 |
| SR-081 | major | Run actions and relaunch: source states, responses, the dialog's three meanings of "Resume", lineage, and a fourth mode vocabulary | UX-280, UX-281, UX-282, UX-289 |
| SR-082 | major | Stages have no API contract: no resource, no state enum, no single identifier | UX-271, UX-273, UX-278, UX-290 |
| SR-083 | major | Task and attempt states: no owner, no stored enum, display labels used as values | UX-290 |
| SR-084 | major | Events and SSE: frames outside the "complete" catalogue, no sequence for SSE-only frames, no data schemas | UX-271, UX-283 |
| SR-085 | major | The 0.0.1 gate: no run filter, untyped check values without thresholds, unclear If-Match, no response body, label-only actor kinds, verbs still split | UX-271, UX-283, UX-284, UX-285 |
| SR-086 | major | Workflow resource: `local` is missing from the source enum, and there is no name, no location and no way to resolve a key | UX-270 |
| SR-087 | major | Launch body: `gates` has one example value, the effective manifest is not frozen, and `links` is unnamed | UX-277, UX-278, UX-279 |
| SR-088 | major | Run resource: name, tags, task counts and the "% tasks" denominator have no fields | UX-271, UX-272, UX-287, UX-288 |
| SR-089 | major | Log endpoints: which file, which launch, which attempt, content type, follow, and the error when a log is gone | UX-273 |
| SR-090 | major | Conventions: list member, default limit, sortable fields, Idempotency-Key rules, ID prefixes, field errors and the problem-type catalogue | UX-274, UX-276, UX-287 |
| SR-091 | major | Token-less loopback: the browser threat (DNS rebinding, CSRF) was parked with the login-node question, but it applies to every 0.0.1 laptop | — |
| UX-270 | major | A run cannot be turned into "workflow name + version + engine logo" without scanning every workflow | SR-086 |
| UX-271 | major | List rows need a run "progress and context" summary; today that is 3–5 calls per row | SR-082, SR-084, SR-085, SR-088 |
| UX-272 | major | Task-progress denominators ("1,248 tasks", "68 % tasks", task quarters) have no source | SR-088, SR-080 |
| UX-273 | major | No run, stage or state timestamps: Started, Duration, "waiting 6 h 20" and "2 h ago" cannot be computed | SR-082, SR-089 |
| UX-274 | major | Runs list: free-text, tag, date and multi-state filters, totals, "Previous" and "Needs attention" are not in `listRuns` | SR-090 |
| UX-275 | major | App chrome on every 0.0.1 board has no operation: runner and server status, Review badge, search, bell | — |
| UX-276 | major | Launch: runner file checks, "Recheck", "Browse" and the disabled "Launch · fix 1 issue first" have no endpoint | SR-090 |
| UX-277 | major | Snakemake launch: `RunCreate` carries one samplesheet and a Nextflow `profile`, but the board sends two TSVs, a config file and a deployment method | SR-087 |
| UX-278 | major | No manifest read: the gate list before launch, stage sources and names, overlay versions and gate names cannot be shown | SR-087, SR-082 |
| UX-279 | major | "Copy to a new launch" cannot rebuild a `RunCreate`: samplesheet, profile and gates are not readable from a run | SR-087 |
| UX-280 | major | Relaunch overrides are parameters only; the dialog's main example is a process resource override ("extra config") | SR-081 |
| UX-281 | major | The relaunch preview (reused / to run per stage, estimate, suggested mode, suggestions, pre-flight) has no operation | SR-081 |
| UX-282 | major | Lineage and compare: entries lack name, from-stage, actor, failure summary and old → new values | SR-081 |
| UX-283 | major | A decided gate's outcome cannot be read: who, when, which action, why | SR-085, SR-084 |
| UX-284 | major | ReviewReport's action bar maps to `apply` + change set (outside 0.0.1); the 0.0.1 gate actions are not drawn | SR-085 |
| UX-285 | major | Gate check results cannot be pivoted into the item table or the per-check cards without reading every row | SR-085 |
| UX-286 | major | Tabs and row actions that 0.0.1 boards show have no draft operation: Outputs & reports, Software, Environment, evidence report | — |
| UX-287 | minor | Process summary lacks failures by class, module ID and not-scheduled reason | SR-088, SR-090 |
| UX-288 | minor | Run detail meta strip: work dir, engine version, run number and launched-by have no field | SR-088, SR-080 |
| UX-289 | minor | "Pause after stage" is the Running header action, but `:pause` and `:resume` are not in the draft | SR-081 |
| UX-290 | minor | Legend and the draft enums disagree: no Cancelling or Pausing chip, `stored` vs "Cached / storeDir", stage states free text | SR-082, SR-083 |
| UX-291 | minor | RunsCompare "Outcome" and "CPU-hours" rows need per-run check and accounting data that 0.0.1 does not have | — |

## Questions for Thomas

Questions 1 to 4 come from the spec-reviewer. The ux-reviewer raised no separate question; where one of its findings bears on a question, it is listed under "Also bears on". Question 5 is a merge note drawn from the ux-reviewer's closing notes.

1. **Browser protection in 0.0.1 (SR-091).**
   - Options:
     - (a) Host allow-list, Origin check on writes and JSON-only writes, now;
     - (b) wait for inbox #15;
     - (c) a local token even in 0.0.1.
   - **Recommendation: (a).** It costs little, does not change the "no setup" story, and closes a remote path to running code on a laptop. The #15 note covers login nodes only.
2. **Engine events and the published catalogue (SR-080, SR-084).**
   - Options:
     - (a) one `events` log: engine-native types under `spectio.engine.*`, internal (never delivered to webhooks), with a `seq`; heartbeats kept out of the log;
     - (b) a separate ingest log, and the projector writes only published types to `events`;
     - (c) widen the public catalogue to the full task lifecycle.
   - **Recommendation: (a).** It matches api §8.1 ("appends it to `events`") and keeps the public catalogue small.
3. **Progress denominator (SR-088).** Also bears on UX-272, which proposes `tasks_expected_source` ∈ {`engine_plan`, `previous_run`, `none`}.
   - Options:
     - (a) "% tasks" only when the engine gives a total (expected for Snakemake **[to be validated]**), otherwise "N done · M running" (UX-272: "n known tasks");
     - (b) estimate from the previous run of the same workflow version;
     - (c) drop "% tasks".
   - **Recommendation: (a).** It shows no number Spectio cannot back.
4. **Gate verbs the 0.0.1 API exposes (SR-085, with SR-062).** Also bears on UX-284 (the 0.0.1 gate actions drawn on ReviewReport).
   - Options:
     - (a) `approve` and `stop` only; "relaunch with changed parameters" through SR-062 path B; `apply` and `go_back` return 422 `not-in-this-version`;
     - (b) also `go_back` with a stage;
     - (c) all four, with `apply` limited to parameter edits.
   - **Recommendation: (a).** Change sets are outside the cut, and `go_back` needs the stage contract of SR-082 first. UX-284's proposal (Approve and continue, Stop run, Relaunch with changes…) matches it.
5. **Spec endpoints the draft cut but 0.0.1 boards need (UX-274, UX-275, UX-278, UX-279, UX-285, UX-286, UX-291).** api §5 already lists `GET /runs:summary`, `GET /gates:summary`, `GET /version`, `GET /workflows/{id}/manifest`, `GET /runs/{id}/samplesheets`, `GET /gates/{id}/items` and artefacts; the draft's 0.0.1 cut leaves them out. The ux-reviewer notes that triage can treat these as "widen the cut", not as new spec content.
   - Options:
     - (a) widen the 0.0.1 contract to all of them;
     - (b) widen it to the reads a 0.0.1 board needs, and hide the rest on the boards;
     - (c) keep the draft's cut, and hide everything they feed on the boards.
   - **Recommendation: (b)**, as the findings propose one by one: keep `runs:summary` (UX-274), `/version` and `gates:summary` (UX-275), a read-only manifest (UX-278, `PUT` stays out), `/runs/{id}/samplesheets` (UX-279), `/gates/{id}/items` (UX-285) and evidence artefacts (UX-286); hide search unless `/search` is kept, Software and Environment, Batch and Adopt, and RunsCompare Outcome and CPU-hours (UX-275, UX-286, UX-291).

## Findings: spec-reviewer

### SR-080 · major · Ingest §14: the wire items the draft had to invent, beyond SR-054's subset

- **Where:** api-and-data-model.md §14 (cited, does not exist), §8, §8.1; architecture-plugins-and-packaging.md §12, §13.1–§13.5; schedulers-and-monitoring.md §7. Same root as [SR-001](R1-consistency.md) (inbox #11) and [SR-054](R3-journeys.md) (R3, blocker).
- **Evidence:**
  - "the wire format and the testable bounds belong to the ingest contract (api §14)" (architecture l.514). api-and-data-model.md ends at §13.
  - "The runner tails the spool … and forwards what the server has not acknowledged. Event IDs make both paths idempotent (`unique (run_id, event_id)`)" (architecture l.520). "Ingest validates the batch, appends it to `events` and acknowledges." (api l.325)
  - "Each heartbeat carries a dropped-event counter." (architecture l.532). "Each heartbeat carries the bridge and engine versions, hook counters and an internal-error counter" (architecture l.540). "the heartbeat is part of the ingest contract, api §14, proposed every 60 s" (schedulers l.236).
  - "each event has a payload cap ([api] §14)" (architecture l.555). "Batches of at most 500 events or 1 s … gzip-compressed" (architecture l.528). "The spool … keeps at least 24 h or 200 MB … (the bound the ingest contract sets, api §14)" (architecture l.531).
  - "`running` → `succeeded` / `failed`: the engine reports completion or failure (`spectio.run.completed` / `.failed`)" (api l.270), and "This table is the complete catalogue." (api l.311). The table has no engine task lifecycle types: only `spectio.task.failed`, `.retried`, `.waiting_changed` (api l.301–302).
  - Draft: "Whole envelope invented" (gap #42, l.1492). "the acknowledgement body, and how the runner learns which spooled events the server has … are not specified" (gap #43, l.1502).
- **Problem:** SR-054 asks for the driven-run subset: envelope, run ID and launch number variables, ack, version header, no credential on loopback. The draft shows that a bridge author still lacks the following:
  1. **Per-event outcome.** With one bad event in a batch of 500, nothing says whether the whole batch is rejected, or whether a duplicate `(run_id, event_id)` counts as accepted, which the spool needs before it can drop events.
  2. **Heartbeat carrier.** It is not said whether a heartbeat is an event type (none is in the §8 catalogue) or a separate call. If it is an event, it uses up a run `seq` every 60 s, and SSE clients see it.
  3. **Engine event vocabulary.** Engine events are appended to `events`, and §7.1 treats `spectio.run.completed` as engine-reported. But the "complete" catalogue has no task submit, start or complete types. So the ingest vocabulary is neither the public one nor declared as separate.
  4. **Numbers for the bounds.** The payload cap, the maximum body size, 413 behaviour, and which header names the ingest version are all missing.
  5. **Error types.** `ingest-version-unsupported` (architecture l.510) is the only named problem type. The bodies of 422, 429 and 503 are not defined.
  6. **Run binding.** Nothing says whether one batch is one run or each event names its run (`subject`).
- **Proposal:** owner is a new api §14, "Ingest contract (driven runs, 0.0.1)". Architecture §13 keeps behaviour only and links to it.
  - §14.1 envelope: the api §8 envelope, plus `subject` = run ID, `source` = bridge plus launch n, and `spectiosource_seq`.
  - §14.2 request: `POST /ingest/events`, a JSON array of at most 500 events and at most 4 MB gzip, with header `Spectio-Ingest-Version: 1`.
  - §14.3 response: `200 {accepted:[event_id], duplicate:[event_id], rejected:[{event_id, type, detail}]}`. Problem types for 413, 422, 429 and 503 (with `Retry-After`) and `ingest-version-unsupported`.
  - §14.4 heartbeat: `spectio.bridge.heartbeat`. It updates `runs.flags` and is not stored in `events`, so it gets no `seq`.
  - §14.5 engine event types: `spectio.engine.<nextflow|snakemake>.*`. The projector consumes them; they are internal and not in the published catalogue. Add one sentence to §8 saying the catalogue lists published types only.
  - §14.6 bounds: payload cap 64 KB per event; spool 24 h / 200 MB.
  - The credential part stays under inbox #11, as SR-054 proposes.
- **Related:** UX-272 (whether the bridges send a planned task count), UX-288 (the engine version sent in the batch is never exposed). Question 2.
- **Found by:** spec-reviewer
- **Status:** open

### SR-081 · major · Run actions and relaunch: source states, responses, the dialog's three meanings of "Resume", lineage, and a fourth mode vocabulary

- **Where:** api-and-data-model.md §5 (Runs row), §7 (`runs`, `launches`), §7.1; ui-spec.md §4.4, §4.6; synthesis.md §5, §5ter; cli-and-shared-libraries.md §2. Extends [SR-063 and SR-062](R3-journeys.md) (R3). Related earlier findings: [CH-042](R3-journeys.md) (state machine for failed and resume), [CH-003](R4-constraints.md).
- **Evidence:**
  - "Resuming is a new launch that reuses the engine's cache. Each launch is a `Run` within the same `Lineage`." (synthesis l.220)
  - "Change the parameters and relaunch everything: a new run linked to the previous one." (synthesis l.149)
  - "one row per head process of a run (first launch, each Continue, resume or relaunch)" (api l.238). SR-063 cites only the api line, so the synthesis contradiction stays after SR-063 is applied.
  - Mode vocabularies:
    - "**Resume** … **Rerun from a stage** … **Start fresh**" (ui l.163–165);
    - "previous and next runs (resume / rerun / restart)" (ui l.134);
    - `relaunch (--resume, --from-stage N, --samplesheet v2.csv, --params)` (cli l.49);
    - the draft's `enum: [resume, rerun_from_stage, start_fresh]` (l.968, gap #27 at l.970);
    - SR-063's proposal `{resume, rerun_from, fresh}`.
  - "**Resume** (labelled **Continue** on a paused run or an open gate)" (ui l.163). The run endpoints are `POST /runs/{id}:cancel`, `:pause`, `:resume`, `POST /runs/{id}:relaunch` (api l.88).
  - §7.1 lists no transition out of `failed`, `succeeded` or `cancelled` (api l.264–272). The Failed row offers "Resume · Relaunch…" (ui l.118).
  - Only `POST /runs` has a stated response: "Response `201` with the run…" (api l.127). Draft: "do not say what `:cancel` returns … 409 or an idempotent 200" (gap #4, l.228).
  - Lineage: "`GET /runs/{id}/lineage` has no response shape … no lineage ID or 'what changed' structure" (gap #8, l.335). ui wants "with what changed" (ui l.134).
- **Problem:** SR-063 settles new run versus new launch, the mode enum and the body. These stay undefined:
  1. Which source states accept `:cancel`, `:resume` and `:relaunch`, what each returns, and the error for a wrong state.
  2. The dialog's "Resume" maps to three different calls with no rule: `:resume` on a paused run, a gate decision on an open gate, `:relaunch {mode: resume}` on a terminal run.
  3. The shape of `/lineage`.
  4. synthesis l.220 still says each launch is a Run.
  5. The draft adds a fourth spelling of the modes.
- **Proposal:** owner is a new api §5.1, "Run actions": one table of action × allowed source states × resulting state × response × problem type.
  - `:cancel`: from `queued`, `running`, `awaiting_review` or `paused`, returns 202 with the run. On `cancelling` or a terminal state it returns 200 with the run (idempotent).
  - `:relaunch`: from `failed`, `succeeded` or `cancelled` only; otherwise 409 `run-state-conflict`. Returns 201 with the new run and `Location`. `from_stage` takes a `stages[].id` (SR-082).
  - `GET /runs/{id}/lineage` returns `{root_run_id, runs:[{id, parent_run_id, relaunch_mode, from_stage, state, created_at, params_changed:[key]}]}`, with params diffs per SR-064.
  - ui §4.6: Resume on a paused run calls `:resume`; on a terminal run it calls `:relaunch {mode: resume}`; on an open gate the dialog is not offered, and the gate path is SR-062.
  - synthesis l.220: "Each relaunch is a new Run in the same lineage; each Continue is a new launch of the same Run."
  - The draft adopts SR-063's enum. cli §2 gains `--fresh` and `--from-stage <id>`.
- **Related:** UX-282 (lineage entries: the boards need old → new values, name, actor and failure summary, beyond SR-081's `params_changed`), UX-280 (resource overrides in the relaunch body), UX-281 (relaunch preview), UX-289 (`:pause` / `:resume` not in the draft).
- **Found by:** spec-reviewer
- **Status:** open

### SR-082 · major · Stages have no API contract: no resource, no state enum, no single identifier

- **Where:** api-and-data-model.md §5, §7 (`runs.stage_index`, `tasks.stage`, `gates.stage`, `check_results.stage`, `decisions.stage`), §8 (`spectio.stage.*`); ui-spec.md §3.2, §4.3, §4.4, §5.1; checking-scenarios.md §12.1–§12.3; cli §2; dev-environment-and-testing.md §15.1.
- **Evidence:**
  - "Monitoring: run state, number of jobs / tasks, stages | yes" (dev-env l.481)
  - The columns: `stage_index` on runs (api l.237); `stage` on tasks (l.240), gates (l.243) and check_results (l.244); "stage (for `go_back`)" (l.247)
  - "`stages[]` | `id`, `name`, `match` …" (checking l.394); "A gate is attached to a stage only by `stages[].gate: <gate_id>`" (checking l.403)
  - `relaunch … --from-stage N` and `decide <gate> … go-back --stage S` (cli l.49–50)
  - Six sector looks: completed, running, gate awaiting review, failed, skipped / fully cached, not started (ui l.62–69). "Workflows without declared stages get 4 sectors = quarters of task progress." (ui l.60)
  - Stages are "(2) detected from structure, display only, no gates … (3) none: … rerun-from-stage does not [work]" (ui l.242)
  - `spectio.stage.started`, `.completed` has a "When" column and no data (api l.300). The draft invents a stage schema (gap #6, l.276) and flags id versus index (gap #21, l.845).
- **Problem:** the gauge, "2 of 4 stages", the Stages & gates tab, rerun from a stage and `go_back` all need a per-run stage list with states. None is defined:
  - there is no endpoint and no stage-state enum;
  - the stage reference is an index on `runs`, unspecified on the five other tables, an index `N` in `relaunch` and a name `S` in `go-back`;
  - there is no `source` (declared or detected), which the UI needs to decide whether to offer rerun-from-stage;
  - nothing says whether the stage list is frozen at launch (an overlay can change before a relaunch);
  - nothing says which stage a task gets when it matches no `match` glob, or two.
- **Proposal:** owner is api §7, with a new `run_stages` projection:
  - columns: `run_id`, `stage_id` (the `stages[].id` string, or `detected:<n>`), `position`, `name`, `source` ∈ {declared, detected}, `state` ∈ {not_started, running, awaiting_review, completed, failed, skipped}, `gate_id`, task counts;
  - the stage list is frozen per launch, with `launches.until_stage` as proposed in SR-060 (merged into [CH-042](R3-journeys.md) in R3).
  - Replace `runs.stage_index` with `current_stage_id`. Every other `stage` column holds the id.
  - api §5: `GET /runs/{id}/stages`.
  - `spectio.stage.*` data: `{stage_id, position, launch}`.
  - checking §12.3: a task matching no glob has stage null; overlapping globs are refused by `spectio workflow validate`.
  - ui §3.2 links each sector look to an enum value.
  - cli `--from-stage <id>`.
- **Related:** UX-290 (the Legend's six gauge looks as the stage-state enum), UX-278 (`Stage.source`, `description`, `match[]` for the Manifest board), UX-271 (`stage_mode` including quarters, in the run summary), UX-273 (stage start and end times).
- **Found by:** spec-reviewer
- **Status:** open

### SR-083 · major · Task and attempt states: no owner, no stored enum, display labels used as values

- **Where:** api-and-data-model.md §7 (`tasks`, `attempts`), §8.2, §8.3; ui-spec.md §3.1. Related earlier findings: [CH-050](R3-journeys.md) (task identity across launches), [CH-046](R3-journeys.md) (tasks left `running`).
- **Evidence:**
  - "Task states (Nextflow / Snakemake) map to: pending, submitted, running, succeeded, retried, failed, failed (ignored), cached, stored, not scheduled." (ui l.56)
  - `tasks`, `attempts` | "run_id, process_or_rule, stage, tag · task_id, n, state, exit, resources" (api l.240). State is only on `attempts`.
  - "would let a task go back from `SUCCEEDED` to `RUNNING`, or let `sacct` mark a task `COMPLETED`" (api l.338): upper case, and the engine and scheduler vocabularies are mixed.
  - "counters per process and state" (api l.344); `/processes` "tasks by state" (api l.88)
  - The draft's guess: `enum: [pending, submitted, running, succeeded, retried, failed, failed_ignored, cached, stored, not_scheduled]` (l.1162, gap #35 at l.1163).
- **Problem:** the Tasks tab, its state filter, the per-state counters and the §8.2 rule "never move a terminal state back" all need one stored enum with an order. Today:
  - nothing says whether a task has its own state or takes the state of its last attempt (CH-050 assumes the latter);
  - "retried" and "failed (ignored)" are an attempt count and an error strategy, not states;
  - "stored" (Nextflow `storeDir`) and "not scheduled" have no defined trigger **[to be validated]**;
  - there is no mapping from Nextflow task status or Snakemake job status.
- **Proposal:** owner is a new api §7.2, "Task and attempt states":
  - `attempts.state` ∈ {pending, submitted, running, succeeded, failed, cached, stored}, plus `attempts.ignored` (bool);
  - `tasks.state` is derived from the last attempt, plus `not_scheduled`, meaning the task was planned but stopped by `ext.when` / `--until` or a failed upstream;
  - "retried" is a display flag for n > 1;
  - a rank order for the lattice;
  - a mapping table per engine, marked **[to be validated]** in spike T2.
  - ui §3.1 maps the labels to these values. §8.2 uses lower case.
- **Related:** UX-290 (the Legend board merges `stored` into "Cached / storeDir", unlike the draft's enum).
- **Found by:** spec-reviewer
- **Status:** open

### SR-084 · major · Events and SSE: frames outside the "complete" catalogue, no sequence for SSE-only frames, no data schemas

- **Where:** api-and-data-model.md §4, §5 (Events row), §7 (`events`), §8, §8.2, §8.3. Follows [CH-008](R4-constraints.md) (partly applied) and [CH-018](R4-constraints.md) (applied).
- **Evidence:**
  - "a per-run sequence (`spectiosequence`, or the documented `sequence` extension, `extensions/sequence.md`)" (api l.293)
  - "This table is the complete catalogue." (api l.311)
  - "The server sends at most one coalesced delta per run per second: counters per process and state, and the IDs of changed rows" (api l.344). "Raw task events go only to a client that has that task open." (api l.345)
  - "`spectio.check.evaluated` (SSE only)" (api l.305). "A single-run stream resumes with `Last-Event-ID` = the run's `seq`" (api l.336).
  - `.state_changed` and `.completed` / `.failed` (api l.297), and "Every transition emits `spectio.run.state_changed`" (api l.274)
  - `GET /events?run=…&after=seq` (api l.92) versus "cursor pagination (`?cursor=`, `limit` ≤ 200, `next`)" (api l.65)
  - Task events are "coalesced per run per minute for subscribers" (api l.301).
  - Draft gaps #14 (l.594), #15 (l.631), #38 (l.1356), #39 (l.1358), #40 (l.1386), #41 (l.1449).
- **Problem:**
  1. The 1 s delta and raw task events are SSE frames with no type name and no fields, although the catalogue claims to be complete.
  2. SSE-only frames (`check.evaluated`, the delta) are not said to be stored in `events`. If they are not stored, they have no `seq`: the SSE `id:` cannot be the run `seq` for them, and a reconnect with `Last-Event-ID` silently loses gate-check evaluations. If they are stored, every evaluation uses up a `seq`.
  3. The sequence extension is not chosen, nor is its type: string or integer **[to be validated against CloudEvents `extensions/sequence.md`]**.
  4. No 0.0.1 type has a `data` schema (`run.state_changed`, `stage.*`, `task.failed`, `gate.opened`, `gate.decided`, `check.*`).
  5. Nothing says whether `GET /events` returns envelopes or table rows, and `after` breaks the §4 cursor rule.
  6. The stream filters, the SSE `event:` field and how a client "has a task open" are unnamed.
  7. A terminal transition emits both `state_changed` and `completed` / `failed`. Nothing says this is intended.
- **Proposal:** owner is api §8.
  - The catalogue gains a "Data" column that links to JSON Schemas in `spectio-sdk`. Choose `spectiosequence` as an integer.
  - A new §8.5, "Stream frames":
    - `event:` = the CloudEvents type;
    - `id:` = the run `seq` for logged events only; SSE-only frames carry no `id:`;
    - after a `Last-Event-ID` resume the server replays logged events, then sends a fresh delta;
    - define `spectio.run.delta` (SSE only): `{run_id, seq_through, counts:{process:{state:n}}, changed:{tasks:[], stages:[], gates:[]}}`;
    - raw task events through `GET /events/stream?run=…&task=…`;
    - filters `run`, `project`, `type`.
  - `GET /events` returns envelopes. `?run=&after=<seq>` is the documented exception to the cursor rule, with `next` = the last `seq`.
  - State that `.completed` / `.failed` are emitted after `state_changed`.
- **Related:** UX-271 (the run summary is updated on the same path as the delta), UX-283 (today a decided gate can only be read by replaying `spectio.gate.decided`). Question 2.
- **Found by:** spec-reviewer
- **Status:** open

### SR-085 · major · The 0.0.1 gate: no run filter, untyped check values without thresholds, unclear If-Match, no response body, label-only actor kinds, verbs still split

- **Where:** api-and-data-model.md §4 (Writes), §5 (Gates row), §7 (`gates`, `check_results`, `decisions`, `events.actor_kind`); checking-scenarios.md §4.1, §5, §11.4; cli §2. Related earlier findings: [SR-012](R1-consistency.md) (partly applied, checking §5 pending #19), [CH-014](R4-constraints.md) (applied), [SR-058, SR-059 and SR-062](R3-journeys.md) (R3).
- **Evidence:**
  - "`GET /gates` (queue: `?assigned_to=me&state=open`)" and "`POST /gates/{id}/decisions` (`approve`, `apply`, `go_back` with a stage, `stop`; §7 — with If-Match)" (api l.91)
  - "on a gate with a quorum each decision is a vote and does not compare-and-swap on the gate ETag" (api l.66). Yet the server itself resolves the gate "in one conditional update (`UPDATE gates … WHERE id=? AND state='open' AND etag=?`)" (api l.247).
  - `check_results` | "… check_key, item_key (nullable), value, verdict (`pass`, `fail`, `provisional`, `too_large`, `error`), severity …" (api l.244). There is no type for `value` and no threshold. Check keys `min`, `max`, `kind`, `scope` exist only in spectio.yml (checking l.114–118).
  - "actor_kind (… person, AI agent, service / API, CLI …)" (api l.242). The draft guesses `[person, agent, service, cli]` (l.1280, gap #37 at l.1281).
  - Gate verbs: "approve · stop · go back to a stage · reassign · wait for a signal" (checking l.132), with no `apply`; versus `decide <gate> approve|apply|stop|go-back` (cli l.50).
  - "approve then continue, or relaunch with changed parameters" (dev-env l.484). Draft: "(2) … the response to a missing If-Match (428?) … (3) The response body … is not specified" (gap #13, l.560).
- **Problem:** Run detail cannot find a run's gate except by listing every gate. The review screen cannot show "14.8 % vs max 10 %", because the threshold is not stored with the result, and the manifest can change after launch. The client cannot tell whether `If-Match` is required, what a missing one returns, or what a decision returns. `actor_kind` has no wire values. Which verbs 0.0.1 exposes is unclear: `apply` needs a change set, which is outside the cut.
- **Proposal:** owner is api §5 (Gates row) with §7.
  - `GET /gates?run=` and `open_gate_id` on the run resource.
  - On open, the gate stores a copy of its check definitions (`gates.checks` JSON).
  - `GET /gates/{id}/checks` returns paged `{items:[{check_key, kind, scope, severity, threshold:{min,max}, item_key, value: number|string|boolean|null, verdict, file_uri, evaluated_at}]}`.
  - `If-Match`: a stale tag gives 412 `etag-mismatch`; a missing tag gives 428 `if-match-required`, except on quorum gates.
  - The decision returns 201 `{decision, gate}`.
  - `actor_kind` ∈ {person, agent, service, cli}.
  - In 0.0.1, `apply` returns 422 `not-in-this-version`. The "relaunch with changed parameters" path follows SR-062.
  - checking §5 is aligned under SR-012.
- **Related:** UX-284 (the 0.0.1 gate actions and the 428 from the board side), UX-285 (per-check aggregates, item table, `/gates/{id}/items`, beyond the checks shape), UX-283 (reading a decided gate: `GET /gates/{id}/decisions`, `Gate.resolution`), UX-271 (`open_gate` summary on the run, a superset of `open_gate_id`). Question 4.
- **Found by:** spec-reviewer
- **Status:** open

### SR-086 · major · Workflow resource: `local` is missing from the source enum, and there is no name, no location and no way to resolve a key

- **Where:** api-and-data-model.md §5 (Workflows row), §7 (`workflows`, `workflow_versions`); ui-spec.md §4.7; cli §2. Import body and fetching: [SR-056](R3-journeys.md) (R3). Schema endpoint and `ui:` block: [SR-065](R3-journeys.md) (R3) and [UX-119](R12-ui-scenarios.md).
- **Evidence:**
  - `workflows` | "project_id, source (git, nf-core, catalog, crate), engine · … key (… local `local/<directory name>/<short content hash>`)" (api l.236)
  - "`CHECK` constraints instead of enums" (api l.177)
  - Catalog cards show "name, source (nf-core / Snakemake catalog / git / local)" (ui l.169). Search covers "names" (api l.95).
  - "Options that take … a workflow (`--project`, `--env`, `launch`) accept a prefixed ID or a name. A name is resolved through the list endpoints" (cli l.39). `launch <org>/<name>/<version>` (cli l.49), while the API takes `workflow_version_id` (api l.111).
  - Draft gaps #24 (l.890), #25 (l.902), #26 (l.916).
- **Problem:**
  - A `CHECK` built from the §7 list rejects `local`, the most likely 0.0.1 source.
  - The UI, search and CLI show or resolve a workflow name that no column holds.
  - There is no column for the URL or path.
  - No list filter lets the CLI turn `<org>/<name>/<version>` into a `wfv_` ID.
- **Proposal:** owner is api §7 (`workflows`).
  - Add `name` and `location` (URL or absolute path).
  - source ∈ {git, nf-core, catalog, crate, local}.
  - api §5: `GET /workflows?name=&source=` and `GET /workflow-versions?key=`.
  - The import body stays with SR-056.
- **Related:** UX-270 (`GET /workflow-versions/{id}` and a workflow summary embedded in `Run`, which needs the `name` column added here).
- **Found by:** spec-reviewer
- **Status:** open

### SR-087 · major · Launch body: `gates` has one example value, the effective manifest is not frozen, and `links` is unnamed

- **Where:** api-and-data-model.md §5 (launch example); ui-spec.md §4.6; cli §2; checking-scenarios.md §12.7. Default environment: [SR-055](R3-journeys.md) (R3). Related earlier finding: [UX-216](R7-ui.md) (partly applied).
- **Evidence:**
  - `"gates": "from-manifest"` and `"notify": { "webhook_ids": [...] }` (api l.122, l.124)
  - "Response `201` with the run, its `id`, `state: queued` and links." (api l.127)
  - `run launch … --gates spectio.yml` (cli l.49) sends a file.
  - The launch aside offers "gates (each with "Change")" (ui l.158).
  - "A lab overlay … is merged over the author's file." (checking l.426)
  - Draft gaps #28 (l.1008), #30 (l.1042), #31 (l.1053), #32 (l.1057).
- **Problem:** the only defined `gates` value is `from-manifest`. The CLI sends a file and the UI lets the user change gates, and neither has a wire form. Nothing stores which merged manifest a run used, yet the gate's check definitions (SR-085) and "gates carry over" on relaunch (SR-063) both depend on it. `links` has no names or format. `notify` targets webhooks, which are outside 0.0.1.
- **Proposal:** owner is a new api §5.2, "Launch body": a normative table of fields, required flags and defaults.
  - `project_id` defaults to the default project. `environment_id` defaults to the only environment (SR-055).
  - `gates` = `"from-manifest"` (default) | `"none"` | an inline spectio.yml object, validated against checking §12.
  - The server stores the merged result as `run_inputs.kind = manifest`.
  - `links` = `{self, events, stream, ui}` as root-relative paths.
  - `notify`: 422 `not-in-this-version` in 0.0.1.
  - cli `--gates FILE` sends the inline object.
- **Related:** UX-278 (a manifest read and `runs.manifest_ref`; the same "which manifest did this run use" gap from the board side), UX-279 (echo the launch request on the run so it can be copied), UX-277 (several sample tables and a software choice in the launch body).
- **Found by:** spec-reviewer
- **Status:** open

### SR-088 · major · Run resource: name, tags, task counts and the "% tasks" denominator have no fields

- **Where:** api-and-data-model.md §5 (Runs row: `PATCH`, `/processes`), §7 (`runs`); ui-spec.md §4.3, §4.4; dev-environment-and-testing.md §15.1.
- **Evidence:**
  - "Run (name + ID, first) · … · Progress (stage gauge + "2 of 4 stages · 63 % tasks") · … · Origin" (ui l.105). "Header: run name" (ui l.110).
  - "`PATCH /runs/{id}` (name, tags, external_refs, project move)" (api l.88). The `runs` columns have no name, tags or counts (api l.237).
  - "number of jobs / tasks" (dev-env l.481)
  - `/processes` "(per process: tasks by state, retries, peak RSS, native ID range)" (api l.88), described in words only.
  - origin ∈ (ui, api, wes, cli-observed, cli-adopted) (api l.237). Nothing says which value `spectio run launch` gets.
  - Draft gaps #29 (l.1009), #34 (l.1137).
- **Problem:**
  - PATCH edits fields that do not exist.
  - Nobody says who names a run: the user at launch, Spectio, or the engine's own run name **[to be validated]**.
  - "63 % tasks" needs a total. Nextflow, a dataflow engine, does not know its task count in advance **[to be validated]**. Snakemake computes a job count for its DAG at start **[to be validated]**.
  - `/processes` has no field names.
  - It is not said whether a CLI launch has origin `api`.
- **Proposal:** owner is api §7 (`runs`).
  - Add `name` (from the launch body, default `<workflow name>-<last 6 of id>`), `tags` (JSON array), a projected `task_counts` {state: n}, and a nullable `expected_tasks`, set only when the engine reports a total.
  - ui §4.3 shows "% tasks" only when `expected_tasks` is known, and otherwise "N done · M running".
  - api §5: a `/processes` item = `{process, stage_id, counts:{state:n}, retries, peak_rss_bytes, native_id_min, native_id_max}`.
  - State that a CLI launch has origin `api` (the actor shows CLI through `actor_kind`).
- **Related:** UX-272 (same denominator gap; proposes `tasks_expected` plus `tasks_expected_source`), UX-271 (the run summary's `tasks` counters), UX-287 (missing content in `/processes`), UX-288 (more meta fields on `runs`). Question 3.
- **Found by:** spec-reviewer
- **Status:** open

### SR-089 · major · Log endpoints: which file, which launch, which attempt, content type, follow, and the error when a log is gone

- **Where:** api-and-data-model.md §5 (Tasks & logs row); ui-spec.md §4.4 (Logs tab); cli §2 (`run logs --follow`). Log sources on the local executor: [CH-048](R3-journeys.md) (R3). This finding covers only the HTTP contract.
- **Evidence:**
  - "`GET /tasks/{id}/logs/{stdout|stderr}` (range requests), `GET /runs/{id}/logs`" (api l.89)
  - "run log and per-task stdout/stderr (fetched on demand through the runner)" (ui l.129)
  - `logs --follow` (cli l.49)
  - "one row per head process of a run (first launch, each Continue …)" (api l.238)
  - Draft gaps #9 (l.383) and #10 (l.447).
- **Problem:** these are undefined:
  - which file `/runs/{id}/logs` returns (engine log or head stdout and stderr), and for which launch, since a gated run has at least two;
  - the content type, ranges and how `--follow` works;
  - which attempt a task log is, and how to ask for another;
  - the response when the file is gone (work directory cleaned, Snakemake job with no `log:` **[to be validated]**) or when the runner is offline (later versions).
- **Proposal:** owner is api §5 (Tasks & logs row).
  - `GET /runs/{id}/logs?launch=<n>&source=engine|head`.
  - `GET /tasks/{id}/attempts/{n}/logs/{stream}`; `/tasks/{id}/logs/{stream}` returns the last attempt.
  - `text/plain; charset=utf-8`; `Range: bytes=` with 206 and 416; `?follow=true` streams chunks until the launch ends.
  - Problems: 404 `log-not-found`, 410 `log-cleaned`, 503 `runner-offline`.
  - Which file each source names comes from CH-048.
- **Related:** UX-273 (`GET /runs/{id}/launches`, which also gives the launch numbers the run log needs).
- **Found by:** spec-reviewer
- **Status:** open

### SR-090 · major · Conventions: list member, default limit, sortable fields, Idempotency-Key rules, ID prefixes, field errors and the problem-type catalogue

- **Where:** api-and-data-model.md §4; ui-spec.md §11; cli §2 (exit codes); architecture §12. Related earlier findings: [CH-040](R4-constraints.md) (partly applied), [SEC-125](R5-security.md) (applied, scope only).
- **Evidence:**
  - "prefixed ULIDs (`run_01JB…`, `gate_01JB…`, `prj_01JB…`)" (api l.62). `wf_`, `wfv_`, `env_` and `whk_` appear only in examples (api l.65, l.111–124).
  - "cursor pagination (`?cursor=`, `limit` ≤ 200, `next` in the response) … sort (`?sort=-created_at`)" (api l.65)
  - "`Idempotency-Key` on every POST that creates or triggers something, kept 24 h" (api l.66). The CLI makes it an option, `--idempotency-key` (cli l.49).
  - "RFC 9457 `application/problem+json` with a stable `type` URI and, for validation, a list of field errors" (api l.69)
  - "an error panel that maps the RFC 9457 problem `type` … to a sentence" (ui l.374). `ingest-version-unsupported` is the only named type (architecture l.510).
  - Draft gaps #17 (l.726), #18 (l.733), #19 (l.749), #20 (l.839), #22 (l.868), #23 (l.880).
- **Problem:** every endpoint depends on these and none is stated:
  - the items member of a list page;
  - the default `limit`;
  - the sortable fields of each list;
  - whether `Idempotency-Key` is required, and its length and charset;
  - the prefixes for launch, task, attempt, check result, decision, event, user, group and operation;
  - the field-error member;
  - the problem types that the UI error panel and the CLI exit codes both map from.
- **Proposal:** owner is a new api §4.1, "Wire conventions" (a table).
  - List page = `{items:[…], next: <cursor>|null}`; `limit` default 50, maximum 200.
  - Sortable fields are listed in each §5 row: runs `created_at`, `started_at`, `state`; gates `opened_at`.
  - `Idempotency-Key`: optional, 1–255 printable ASCII characters; the UI sends one per submit.
  - Prefixes: `wf_ wfv_ run_ lch_ tsk_ att_ gate_ chk_ dec_ evt_ prj_ usr_ grp_ env_ rnr_ whk_ op_`.
  - Problem `type` = `/problems/<slug>` (a relative reference) and `errors:[{pointer, code, detail}]`.
  - A catalogue with HTTP status and CLI exit code for each type: `validation-failed`, `idempotency-key-reused`, `not-found`, `run-state-conflict`, `etag-mismatch`, `if-match-required`, `not-in-this-version`, `rate-limited`, `ingest-version-unsupported`, `log-cleaned`.
- **Related:** UX-274 (sortable fields including `last_activity`, multi-value `state`, `since` and `q` filters on runs), UX-276 (field errors and per-row file checks before launch), UX-287 (`sort` on `/processes`).
- **Found by:** spec-reviewer
- **Status:** open

### SR-091 · major · Token-less loopback: the browser threat (DNS rebinding, CSRF) was parked with the login-node question, but it applies to every 0.0.1 laptop

- **Where:** authentication-and-access.md §1 (`single`); api-and-data-model.md §6; mvp-0.0.1.md §1; inbox #15. Same root as [SEC-102](R5-security.md) (blocker, inbox) and [SR-031](R1-consistency.md) (inbox).
- **Evidence:**
  - "auth mode `single`, bound to 127.0.0.1 … Shared login nodes are not covered (inbox #15, open)" (mvp l.11)
  - "Requests from `127.0.0.1` / a Unix socket without a token are treated as that user." (api l.166). "binds to `127.0.0.1` by default. On any other interface it requires a token" (auth l.43).
  - SEC-102: "**Path 2, DNS rebinding and CSRF from the browser.** A malicious page can drive a tokenless localhost API through DNS rebinding" (R5-security.md l.139)
  - "Not needed for 0.0.1 (single user, local engines; Thomas 2026-10-27)" (inbox l.194, #15)
  - The CSRF token exists only for the browser session cookie (auth l.98), and single mode has no session. The draft: "no Origin / Host check and no CSRF rule for single mode" (gap #1, l.39).
- **Problem:** the #15 note parks the login-node path (SEC-102 Path 1). Path 2 needs only one user, a laptop and a browser, which is exactly the 0.0.1 frame. `POST /runs` with a local workflow runs code as that user. No spec asks for a `Host` or `Origin` check, so an implementer who follows the specs ships an API that any web page can reach to run code on the user's machine.
- **Proposal:** owner is auth §1 (`single` row), linked from api §6 and mvp §1. In 0.0.1 single mode:
  1. Reject a `Host` other than `127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>` with 403 `host-not-allowed`.
  2. Reject a write whose `Origin` is present and is not the server's own origin.
  3. Require `Content-Type: application/json` on writes.
  4. Send no CORS headers.

  This is the browser half of SEC-102 option (a). The Unix socket and peer-credential half stays in #15.
  - **Test:** `Host: evil.example` gets 403; a cross-origin POST gets 403.
- **Related:** question 1.
- **Found by:** spec-reviewer
- **Status:** open

## Findings: ux-reviewer

Board coordinates (x, y) are pixels on the 1440×1180 render. Features that 0.0.1 does not have at all (projects, roles, who may decide, AI, SLURM, the review queue) belong to [UX-227](R7-ui.md); they are raised here only where a 0.0.1 board still needs data for them.

### UX-270 · major · A run cannot be turned into "workflow name + version + engine logo" without scanning every workflow

- **Where:**
  - RunsTable, Workflow column (x 690–880, y 300–1100).
  - RunsRows, workflow line under each name (x 385–700).
  - RunDetail meta strip "Workflow / Engine" (x 300–660, y 195–235).
  - RelaunchDialog subtitle (x 100–560, y 305–320).
  - RunsCompare subtitle (x 350–900, y 120–150).
  - ReviewReport header line (x 390–1130, y 172–186).
  - Draft: `Run` (only `workflow_version_id`), `WorkflowVersion` (no name, engine or workflow summary). There is no `GET /workflow-versions/{id}`, only `/workflow-versions/{id}/schema`.
- **Evidence:** "nf-core/rnaseq 3.27.0" with the nf-core mark (RunsTable). "Engine: Nextflow 25.10.4 · nf-core" (RunDetail). Legend: "nf-core replaces Nextflow for genuine nf-core pipelines".
- **Problem:** to go from a run to a workflow name and version, a client must call `listWorkflows`, then `listWorkflowVersions` for every workflow, and join on the client. No path reads one workflow version by its ID. The engine mark needs `Workflow.engine` and `source`, which are two hops away. Every list row pays this cost.
- **Proposal:** api-and-data-model.md §5:
  - add `GET /workflow-versions/{id}`;
  - embed a read-only `workflow` summary in `Run` (`workflow_id`, `name` (gap #25, l.902), `engine`, `source`, `version_key`, `revision`, `commit`), or allow `?expand=workflow_version` on `GET /runs` and `GET /runs/{id}`.

  Record the summary in §7 as a denormalised read field.
- **Related:** SR-086 (adds the `name` and `location` columns and the lookup filters this summary needs).
- **Found by:** ux-reviewer
- **Status:** open

### UX-271 · major · List rows need a run "progress and context" summary; today that is 3–5 calls per row

- **Where:**
  - RunsTable, State context line (x 475–670) and Progress · gates column (x 900–1095), all rows.
  - RunsRows, the state line on the right (x 830–1160) and the action button (x 1310–1400).
  - Legend "Run states" context lines (x 57–475, y 135–570).
  - Draft: `Run`, `RunGraph`, `ProcessSummary`, `GET /gates?run=`, `GET /runs/{id}/tasks?state=failed`, `GET /tasks/{id}/attempts`.
- **Evidence:**
  - "Mapping QC · checks comp…", "stage 3 of 4 · quantification", "exit 1 · DEEPVARIANT_RUN…", "2 of 4 stages / lab overlay · 1 gate", "detected stages · no gate", "quarter 3 · 68 % ta…" (RunsTable).
  - "Bisulfite conversion · MShef4_J1 98.31 %, below 99 %", "DEEPVARIANT_RUNDEEPVARIANT (NA12878) exit 1" (RunsRows).
  - "Paused by Alice · resumable", "Stopped by policy (time limit)" (Legend).
- **Problem:** each row shows several things the run itself does not carry:
  - the stage count, stage name and stage mode (declared, detected, or quarters);
  - the gate count and source;
  - the failing task with its tag and exit code;
  - the failing check of an open gate;
  - who cancelled or paused, and whether the run is resumable.

  Gap #29 (l.1009) covers only the task counters. The rest needs `graph` + `processes` + `gates?run=` (gap #11, l.495) + `checks` or `tasks` + `attempts` for every row, and that row is also the target of the "Review" and "Resume…" buttons. A 50-row page means 150–250 requests.
- **Proposal:** api-and-data-model.md §5/§7: a read-only `summary` object on `Run`, also returned by list calls, with:
  - `stages_total`, `stage_name`, `stage_mode` (`declared|detected|quarters`);
  - `tasks` {`done`, `total`, `failed`, `cached`} (closes gap #29);
  - `open_gate` {`id`, `name`, `opened_at`, `first_failing_check`};
  - `last_failure` {`task_id`, `process_or_rule`, `tag`, `exit`, `failure_class`};
  - `state_actor` and `state_reason` for paused and cancelled runs;
  - `resumable` (bool).

  The server updates it on the same path as the §8.3 RunDelta.
- **Related:** SR-088 (`task_counts`, `expected_tasks`), SR-085 (`open_gate_id` and the `run` filter on gates), SR-082 (stage `source` and `current_stage_id`), SR-084 (the delta that keeps the summary fresh). Failure cause on a local run: [CH-047](R3-journeys.md) (R3).
- **Found by:** ux-reviewer
- **Status:** open

### UX-272 · major · Task-progress denominators ("1,248 tasks", "68 % tasks", task quarters) have no source

- **Where:**
  - RunDetail header "812 / 1,248 tasks" (x 450–905, y 148–163) and stage 4 "Not started" (x 290–1075, y 668–745).
  - RunsTable Progress column "812 / 1,248 tasks", "quarter 3 · 68 % ta…".
  - RelaunchDialog stage strip "≈ 300 tasks", "≈ 12 tasks" (x 513–918, y 517–585).
  - RunsCompare "+ 367 never reached" (x 499–790, y 440–470).
  - Legend "four sectors = task quarters" (x 511–930, y 85–120).
  - Draft: `ProcessSummary.tasks_by_state`, `RunDelta.counters`.
- **Evidence:** ui-spec.md §3.2: "Workflows without declared stages get 4 sectors = quarters of task progress". §4.3: "63 % tasks".
- **Problem:** `tasks_by_state` counts only tasks the engine has already reported. A percentage, quarters, "never reached" or the tasks of a stage not started yet all need an expected total. No spec or draft field defines one.
  - Nextflow creates tasks as channel items arrive, so the total is not known up front **[to be validated]**.
  - Snakemake builds its job DAG before it runs, so the logger plugin may be able to report a planned job count **[to be validated]**.

  RunsTable already writes "442 / 881 known tasks" for a CLI run, which shows the distinction exists in the design but not in the contract.
- **Proposal:**
  - ui-spec.md §3.2 should define progress as "known tasks" when no expected count exists.
  - api-and-data-model.md §5 `/processes` and the run summary (UX-271) should add `tasks_expected` (nullable) and `tasks_expected_source` (`engine_plan|previous_run|none`).
  - The bridges' ingest contract should say whether a planned count is sent (gap #42, l.1492).
  - The boards should show "n known tasks" when `tasks_expected` is null.
- **Related:** SR-088 (same denominator gap; proposes `expected_tasks` and "N done · M running"), SR-080 (the ingest contract that would carry a planned count). Question 3.
- **Found by:** ux-reviewer
- **Status:** open

### UX-273 · major · No run, stage or state timestamps: Started, Duration, "waiting 6 h 20" and "2 h ago" cannot be computed

- **Where:**
  - RunsTable "Started · duration" column (x 1330–1415).
  - RunsRows time column (x 1180–1300: "waiting 6 h 20", "started 1 h 05 ago", "Sun 22:56").
  - RunDetail header "1 h 05" and stage cards "288 tasks · 14 min" (x 350–1060, y 420–435, 510–520).
  - RelaunchDialog header "2 h ago" (x 450–890, y 148–163).
  - RunsCompare "Duration · wall clock · 5 h 12 m until the failure" (x 300–1415, y 525–565).
  - Legend "Waiting for a runner · 2 min", "Gate after stage 2 · since 12 min".
  - Draft: `Run` (`created_at`, `updated_at` only), `Stage` (no times).
- **Evidence:** ui-spec.md §4.3 columns "Started · Duration". The `launches` table (§7) has `started_at`, `exited_at`, `exit_code`, but the draft exposes no launch.
- **Problem:**
  - `created_at` is the queue time, not the start time.
  - `updated_at` changes on every edit, so it cannot mark the end of a run.
  - Nothing gives the time of entering the current state, which "waiting", "since" and Queued "· 2 min" need.
  - Stages have no start or end time.
  - A run with several launches (resume, Continue) needs a rule for wall-clock duration.

  The only fallback is replaying `GET /events` for each row.
- **Proposal:** api-and-data-model.md §7 `runs`:
  - expose `started_at`, `ended_at` and `state_changed_at` on `Run`;
  - add `started_at` and `ended_at` to `Stage` (from `spectio.stage.started/completed`);
  - say whether duration is first start → end or the sum of `launches`.

  §5: add `GET /runs/{id}/launches`, or embed `launches[]`. This also helps gap #9 (l.383).
- **Related:** SR-082 (the `run_stages` projection that would carry the stage times), SR-089 (the run log is chosen per launch).
- **Found by:** ux-reviewer
- **Status:** open

### UX-274 · major · Runs list: free-text, tag, date and multi-state filters, totals, "Previous" and "Needs attention" are not in `listRuns`

- **Where:**
  - RunsTable toolbar (x 290–1415, y 155–235: "Filter by run, workflow, tag", "Group: none", "Sort: last activity", "Filters · 1", chip "Last 7 days").
  - RunsTable header counts (x 355–955, y 122–138) and the "173 of 214 ran with no gate" bar (x 845–1415, y 215–230).
  - RunsTable footer "1–16 of 214 runs in the last 7 days" and "Previous" (x 290–1415, y 1120–1150).
  - RunsRows sections "NEEDS ATTENTION · 6" and "ACTIVE AND RECENT" (x 290–1415, y 155, 575).
  - Draft: `GET /runs` (filters `project`, `state` as a single value, `workflow`, `external_ref`; `PageNext` has `next` only).
- **Evidence:** "2,946 runs · 11 active · 27 awaiting review". api §4: "Lists return no total … clients page with Next / Load more, never numbered pages or 'of N'. Headline counts … come from the summary endpoints". ui-spec §4.3 says the same.
- **Problem:**
  - The draft leaves out `GET /runs:summary`, which api §5 lists. So no headline count or no-gate/gate ratio can be served.
  - `state` takes one value, so "Needs attention" (awaiting_review + failed) and "11 active" need two or more calls. No rule says when a failed run leaves "Needs attention".
  - There is no `q`, name-prefix, tag or `since` filter.
  - There is no `prev` cursor.
  - "1–16 of 214" and "Previous" contradict api §4, and that is a defect of the board.
- **Proposal:**
  - api-and-data-model.md §5: put `GET /runs:summary?since=&group_by=state` in the 0.0.1 contract.
  - §4: allow repeated or comma-separated `state`, add `since=` and a `q` name-prefix filter (an indexed prefix, as §7 Search allows), and list the sortable fields (gap #18, l.733, including `last_activity`).
  - ui-spec.md §4.3: define "Needs attention".
  - On the boards: drop "of 214" and "Previous", and use "Load more".
- **Related:** SR-090 (sortable fields and list conventions). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-275 · major · App chrome on every 0.0.1 board has no operation: runner and server status, Review badge, search, bell

- **Where:** every board.
  - Sidebar footer "Runners 3 / 4 online", "Server v0.4.0 · online" (x 55–225, y 1095–1155).
  - Sidebar "Review 27" badge (x 205–240, y 278–302).
  - Topbar search "⌘K" (x 915–1205, y 22–55), bell (x 1230–1255), avatar "AM", project switcher "demo-lab · all projects" (RunsTable and RunsCompare x 110–345, y 22–55).
  - Draft: no `/version`, `/runners`, `/gates:summary`, `/search`, `/me`, `/me/notifications`.
- **Evidence:** api §5 lists `GET /version` (public), `GET /runners`, `GET /gates:summary`, `GET /search?q=`, `GET /me/notifications`. The draft cut keeps none of them.
- **Problem:** in 0.0.1 the local runner runs inside the server (`--with-runner`), so the runner indicator still matters: `Run.flags.runner_offline` exists, but nothing global does. The Review badge needs a count that lists cannot give (api §4). Search, bell, avatar and project switcher have no source in single mode.
- **Proposal:**
  - api-and-data-model.md §5: add to the 0.0.1 contract `GET /version` (server version plus embedded runner status and last heartbeat) and `GET /gates:summary?state=open` for the badge.
  - ui-spec.md §2 / §11, under UX-227: hide in 0.0.1 the bell, avatar menu, project switcher and the "n / m runners" form. Hide search too, unless `GET /search` is kept.
- **Related:** the in-process runner record is [SR-055](R3-journeys.md) (R3, absorbs UX-247 on EnvLocal). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-276 · major · Launch: runner file checks, "Recheck", "Browse" and the disabled "Launch · fix 1 issue first" have no endpoint

- **Where:**
  - Launch: samplesheet check column and "Files checked by the runner · 10:12 · Recheck" (x 350–1060, y 290–505); "Browse" buttons (x 637–1060, y 540–572); button "Launch · fix 1 issue first" (x 1097–1415, y 580–625).
  - LaunchSnakemake: units table check column and Recheck (x 350–1060, y 525–730); same button (x 1097–1415, y 833–878).
  - Draft: only `POST /runs` (422 at submit time); `Problem.errors` (gap #22, l.868).
- **Evidence:** "S4 · fastq_2 not found on /data/demo/fastq. Fix the path or upload, then Recheck (checks run again automatically before launch)". ui-spec §4.6: "File checks … run through the runner, show when they last ran, and have a Recheck button".
- **Problem:**
  - No spec endpoint and no draft operation checks files before launch, or tells when they were last checked.
  - The only check is the 422 of `POST /runs`, which turns the form's live issue count into a failed submit.
  - "Browse" needs a directory listing on the environment, and nothing provides one (`/environments/{id}/storage` holds locations, not listings).
- **Proposal:** api-and-data-model.md §5 Runs:
  - add `POST /runs:validate` (same body as `RunCreate`; returns field errors, per-row file checks and `checked_at`), or `POST /environments/{id}/files:check`;
  - add `GET /environments/{id}/files?path=` for the picker, restricted to the environment's storage locations;
  - say that `POST /runs` runs the same checks.

  In 0.0.1 the local runner answers both.
- **Related:** SR-090 (the field-error member these checks would return).
- **Found by:** ux-reviewer
- **Status:** open

### UX-277 · major · Snakemake launch: `RunCreate` carries one samplesheet and a Nextflow `profile`, but the board sends two TSVs, a config file and a deployment method

- **Where:**
  - LaunchSnakemake: "samples · config/samples.tsv" and "units · config/units.tsv" (x 350–1060, y 340–730); aside "Software · conda + Apptainer · 9 envs cached · Change" (x 1097–1415, y 312–380); "config.yaml preview … Passed with --configfile · TSVs written next to it" (x 1097–1415, y 467–820).
  - Launch aside "Software · Profile singularity · Change" (x 1097–1415, y 216–268).
  - Draft: `RunCreate.samplesheet` (one `{param, rows}`), `RunCreate.profile`.
- **Evidence:** "samples.tsv + units.tsv · validated against schemas/samples.schema.yaml, units.schema.yaml".
- **Problem:**
  - `samplesheet` is one object, and its `param` names a Nextflow parameter. A Snakemake workflow with two sample tables, referenced by path from the config, cannot be expressed. The only way out is pointing at files that already exist.
  - Snakemake has `--software-deployment-method` rather than profiles. `profile` has no defined meaning for Snakemake.
  - No operation lists the profiles or software options that the "Change" buttons offer.
  - Gap #3 (l.136, `ui:` hints) is a separate problem.
- **Proposal:** api-and-data-model.md §5 (launch body) and §7 (`run_inputs`):
  - make `samplesheets` an array of `{target, format: csv|tsv, rows}`, where `target` is a parameter name (Nextflow) or a config key/path (Snakemake);
  - add `software` {`profiles[]` | `deployment_methods[]`} by engine;
  - expose the choices on `GET /workflow-versions/{id}` (UX-270) as `profiles[]` and `sample_tables[]`.
- **Related:** SR-087 (the normative launch-body table where these fields would go). Snakemake form and parameter delivery: [SR-065](R3-journeys.md) (R3).
- **Found by:** ux-reviewer
- **Status:** open

### UX-278 · major · No manifest read: the gate list before launch, stage sources and names, overlay versions and gate names cannot be shown

- **Where:**
  - Launch aside "Gates · 1 gate after stage 2 (spectio.yml) · Change" (x 1097–1415, y 280–345); LaunchSnakemake the same (y 390–455).
  - RunDetail "from spectio.yml · lab overlay 'rnaseq-demo-lab' v2 · view file" (x 700–1075, y 345–358) and the stage descriptions "FastQC, UMI extraction, trimming" (y 420–435).
  - Manifest board, all of it: stage cards with process chips (x 56–1160, y 158–330), gate card "Mapping QC · uniquely mapped ≥ 80 % per sample · a person decides" (x 558–700), spectio.yml (x 56–890, y 540–1080).
  - ReviewReport title "Mapping QC" and "gate from lab overlay demo-lab/rnaseq-qc" (x 390–1130, y 145–186).
  - Draft: no `/workflows/{id}/manifest`. `Stage` {id, name, gate_id, state}. `Gate` has no `name`, `key` or `source`. `Run` has no `manifest_id`.
- **Evidence:** ui-spec §4.6: "Each gate names its source and overlay version … Launch, the review step and Run detail show the same overlay version (§5.1)". api §5: "`GET/PUT /workflows/{id}/manifest` (spectio.yml overlay)".
- **Problem:**
  - The draft drops the manifest endpoint. The spec keys it by workflow, while stages and gates belong to a workflow version and an overlay version, and §7 `manifests` (kind, content) has no version number.
  - A run does not record which manifest it used, so Run detail cannot prove it shows "the same overlay version".
  - `Gate` has no display name (the `gates:` key, `mapping_qc`).
  - `Stage` has no `source` (declared, detected or quarters), description or process match list.
- **Proposal:**
  - api-and-data-model.md §5: add `GET /workflow-versions/{id}/manifest`, returning the effective manifest, its parts {kind repo|overlay, name, version} and the parsed stages and gates. Keep `PUT` out of 0.0.1.
  - §7: `manifests.version`, and `runs.manifest_ref` {id, version}.
  - Add `Gate.key` and `Gate.name`, and `Stage.source`, `description` and `match[]`.
  - Gap #31 (l.1053) then becomes "gates: from-manifest | none".
- **Related:** SR-087 (store the merged manifest per run as `run_inputs.kind = manifest`; `gates` values), SR-082 (stage `source`). How rnaseq gets its stages and overlay: [SR-057](R3-journeys.md) (R3). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-279 · major · "Copy to a new launch" cannot rebuild a `RunCreate`: samplesheet, profile and gates are not readable from a run

- **Where:**
  - RelaunchDialog "Copy to a new launch" (x 550–720, y 866–905; variant x 1078–1250, y 797–833).
  - RunsCompare "Copy run 3 to a new launch" (x 1212–1415, y 100–140) and the footer "the samplesheet (v1, 24 samples)" (x 290–930, y 1032–1046).
  - RunDetail meta "Profile · singularity" (x 860–1000, y 198–235).
  - Draft: `GET /runs/{id}/params` returns "the `run_inputs` rows of kind `params`" only. `Run` has no `profile` and no `gates`. `/runs/{id}/samplesheets` is left out.
- **Evidence:** api §5 lists `GET /runs/{id}/samplesheets` (versions). The draft cut omits it. `RunCreate.profile` and `gates` are write-only.
- **Problem:** a copy needs everything that was posted. Today only `params` and `workflow_version_id` come back, so the copy loses the samplesheet, the profile and the gate choice. RunsCompare cannot show the samplesheet version either.
- **Proposal:** api-and-data-model.md §5:
  - keep `GET /runs/{id}/samplesheets` in the 0.0.1 cut, or let `/params` take `?kind=`;
  - echo `profile`, `gates` and `samplesheet` refs on `Run`, as a read-only `launch_request`;
  - optionally add `GET /runs/{id}:launch-template`, which returns a ready `RunCreate` (also usable as "Copy" in CLI and MCP).
- **Related:** SR-087 (the launch-body table and the stored manifest). Parameter history shape: [SR-064](R3-journeys.md) (R3). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-280 · major · Relaunch overrides are parameters only; the dialog's main example is a process resource override ("extra config")

- **Where:**
  - RelaunchDialog "Edit parameters · 2 changed": "STAR_ALIGN memory 72 GB → 96 GB", "QUALIMAP_RNASEQ time 4 h → 8 h", "Sent as an extra config: withName: 'STAR_ALIGN' { memory = 96.GB }…" (x 102–918, y 600–790).
  - RunsCompare "STAR_ALIGN memory · config overlay, not a parameter" (x 300–1415, y 645–690).
  - Draft: `RelaunchRequest` {mode, from_stage, params}; `RunInput.kind` ∈ {params, samplesheet}.
- **Evidence:** api §5 `:relaunch` "(mode, from stage, param overrides)". §7 `run_inputs.kind (params, samplesheet)`.
- **Problem:** memory and time per process are not workflow parameters. The board sends them as an extra Nextflow config (or Snakemake `--set-resources`). The draft and the spec have no field to send them and no `run_inputs` kind to store them. So the OOM relaunch cannot be posted, and RunsCompare cannot show the config change in the parameter history. With the local executor, OOM is also the most likely reason to relaunch (EnvLocal "41 GB for runs").
- **Proposal:** api-and-data-model.md §5 and §7:
  - add `RelaunchRequest.resources` and `RunCreate.resources`: `[{process_or_rule, cpus?, memory?, time?}]`, engine-neutral; the engine plugin renders `withName` or `--set-resources`;
  - add `run_inputs.kind = resources`, so `/params` and lineage diffs include it.

  Gap #33 (l.1070, merge or replace) applies to both.
- **Related:** SR-081 (the run-actions table and the relaunch body), [SR-063](R3-journeys.md) (R3, `:relaunch` contract), [UX-113](R12-ui-scenarios.md) (resource overrides, inbox).
- **Found by:** ux-reviewer
- **Status:** open

### UX-281 · major · The relaunch preview (reused / to run per stage, estimate, suggested mode, suggestions, pre-flight) has no operation

- **Where:**
  - RelaunchDialog: badge "Resume · Suggested" (x 105–365, y 380–480), "Start fresh · About 14 h" (x 655–918), the stage strip "Reused · 288 tasks / Starts here · 314 reused · 22 to run / Will run · ≈ 300 tasks" (x 102–918, y 517–585), "suggested from the failure · from sacct" (x 684–904, y 613–628), the bar "602 reused · 4 failed tasks retried · ≈ 330 to run · ≈ 2 h 10 · work dir +0.9 TB · pre-flight ok" (x 102–918, y 805–840).
  - Variant: "No parameter change suggested … tool error (exit 1)", "≈ 410 reused · ≈ 260 to run" (x 978–1340, y 690–785).
  - Draft: only `POST /runs/{id}:relaunch`.
- **Evidence:** ui-spec §4.6: "an estimate of reused vs to-run tasks (for Nextflow, from a work-directory scan, labelled 'estimate')", "suggestions from the failure, e.g. more memory".
- **Problem:** the specs define no preview call. Suggestions live in `GET /runs/{id}/scheduler`, which is SLURM-only and deferred. So in 0.0.1 nothing feeds the strip, the counts, the estimate, the work-directory growth or the pre-flight result. The board's "from sacct" cannot apply to a local run (see R3 [CH-047](R3-journeys.md), which absorbs UX-245 on RunFailed and `sacct`).
- **Proposal:**
  - api-and-data-model.md §5: add `POST /runs/{id}:relaunch-preview`, with the same body as `:relaunch` and no side effects. It returns per-stage {reused, to_run, estimate: true}, `suggested_mode`, `suggestions[]` {process_or_rule, resource, from, to, reason, source: attempts|scheduler}, `estimated_duration`, `workdir_growth_bytes` and `preflight` (UX-276).
  - For local runs, suggestions come from `attempts.resources` and `failure_class`.
  - Label the board's source line by origin ("from the task's peak memory" when local).
- **Related:** SR-081 (relaunch source states and modes). Reuse estimate: [CH-010](R4-constraints.md).
- **Found by:** ux-reviewer
- **Status:** open

### UX-282 · major · Lineage and compare: entries lack name, from-stage, actor, failure summary and old → new values

- **Where:**
  - RunDetail Lineage card "Run 1 · rnaseq-2026-10-24 · failed in stage 2 (STAR out of memory) / Run 2 · this run · Resume with min_mapped_reads changed" (x 1097–1415, y 735–910) and "Parameters changed vs. previous run · aligner star_salmon → star_salmon, min_mapped_reads 5 → 10" (x 1097–1415, y 335–505).
  - RunsCompare column headers "Run 2 #334 · Resume of run 1 · 1 config change · Alice Martin · Relaunch → Resume · 24 Oct 15:02" and "Rerun of run 2 from stage 3 · 1 parameter" (x 487–1415, y 170–265); the lineage title "rnaseq-liver-tc" (x 352–700, y 120–135); "changed by Chloé Diallo" (x 1118–1300, y 625–638).
  - Draft: `LineageEntry` {run_id, parent_run_id, relaunch_mode, state, created_at, changed_params: [names]}; `Run` has no `from_stage`; `RunInput` has no `created_by`.
- **Evidence:** ui-spec §4.4 Lineage: "previous and next runs (resume / rerun / restart), with what changed". Gap #8 (l.335) says the "what changed" structure is undefined.
- **Problem:** gap #8 is acknowledged, but the draft's guess (names only) does not serve the boards. Parameter history is a 0.0.1 feature, so this matters. The boards also need:
  - old → new values;
  - config/resource changes (UX-280);
  - the run name (gap #29, l.1009);
  - `from_stage` for "Rerun … from stage 3", which `RelaunchRequest` accepts but nothing stores or returns;
  - who relaunched;
  - for a failed ancestor, the failed stage and failure class;
  - a lineage name or ID for the compare title.

  Without these, every entry needs `getRun` + `/params` + `/graph`.
- **Proposal:** api-and-data-model.md §7:
  - add `runs.from_stage` and a `lineage_id` (the root run's ID is enough);
  - give `LineageEntry` `name`, `from_stage`, `created_by`, `summary.last_failure` (UX-271), and `changes[]` {kind: params|samplesheet|resources, key, before, after}.

  §5: the server computes the diff against the parent, which answers gap #7's (l.311) "server or client". Expose `created_by` on `RunInput`.
- **Related:** SR-081 (proposes `{root_run_id, runs:[… from_stage …, params_changed:[key]]}`; UX-282 asks for values and actor on top). Parameter history: [SR-064](R3-journeys.md); RunsCompare reachability: [UX-250](R3-journeys.md) (both R3).
- **Found by:** ux-reviewer
- **Status:** open

### UX-283 · major · A decided gate's outcome cannot be read: who, when, which action, why

- **Where:**
  - RunDetail stage 2 note "Gate approved automatically by QC agent (policy: auto under threshold) · mapping rate 91.4 % ≥ 80 %" (x 350–1060, y 530–555).
  - ReviewReport tab "History 4" (x 963–1060, y 240–260) and "You accepted at 09:14" (x 905–1405, y 950–1010).
  - Manifest step "3 · Someone decides … approve, adjust, go back or stop" (x 725–1050, y 357–435).
  - Draft: `/gates/{id}/decisions` has `POST` only. `Gate` carries `state` but no resolution. `GateEventData.action` exists only on the event.
- **Evidence:** draft `decideGate` "201 The recorded decision" — no list or get.
- **Problem:** after the 0.0.1 "approve then continue", Run detail must say the gate was approved, by whom and when. The only source is replaying `GET /events?type=spectio.gate.decided`. Gap #13(3) (l.560) is about the POST response, not about reading.
- **Proposal:** api-and-data-model.md §5 Gates:
  - add `GET /gates/{id}/decisions` (paged, oldest first);
  - add a read-only `resolution` on `Gate`: {`action`, `decided_at`, `principal_id`, `actor_kind`, `justification`}, null while open;
  - include `resolution` in `Stage` (or `Stage.gate`) of `/graph`, so Run detail needs one call.
- **Related:** SR-085 (decision response body, `actor_kind` wire values), SR-084 (event data schemas).
- **Found by:** ux-reviewer
- **Status:** open

### UX-284 · major · ReviewReport's action bar maps to `apply` + change set (outside 0.0.1); the 0.0.1 gate actions are not drawn

- **Where:**
  - ReviewReport bottom bar "PENDING CHANGES · 2 · K562_REP1 flagged … · 3 warnings acknowledged · Discard changes · More ▾ · Apply and continue" (x 290–1415, y 1115–1170).
  - Item decision toggles Keep / Flag / Exclude (x 1240–1390, y 540–870).
  - "Flagged first / Exclude all failing" (x 1190–1415, y 437–465).
  - "Stages 3–4 · 8 samples · nothing reruns" (x 785–1015, y 1130–1160).
  - Draft: `DecisionAction` {approve, apply, go_back, stop}; `change_set_id` "outside the 0.0.1 cut".
- **Evidence:** mvp-0.0.1.md §2: "the simplest form: … one gate, approve then continue, or relaunch with changed parameters. ReviewReport also draws item decisions and a report reader, which 0.0.1 does not need".
- **Problem:** the only gate board in the 0.0.1 list has a primary button ("Apply and continue") that needs a change set. The draft cannot serve it. The two actions the draft can serve, `approve` and `stop`, are not drawn as buttons. "Acknowledged warnings" has no field anywhere. How "relaunch with changed parameters" maps from a gate is R3 [SR-062](R3-journeys.md) (absorbs UX-242) and gap #13(1) (l.560), so it is not repeated here.
- **Proposal:**
  - ui-spec.md §4.5: draw a 0.0.1 state of ReviewReport (or of RunDetail "Stages & gates") with "Approve and continue" (`approve` + `justification`), "Stop run" (`stop`) and "Relaunch with changes…". Hide the item toggles, the change bar and "Exclude all failing".
  - api-and-data-model.md §5: confirm `approve` with an optional `justification` is the whole 0.0.1 body, and specify the 428 for a missing If-Match (gap #13(2)).
- **Related:** SR-085 (proposes 428 `if-match-required` and `apply` → 422 `not-in-this-version` in 0.0.1). Question 4.
- **Found by:** ux-reviewer
- **Status:** open

### UX-285 · major · Gate check results cannot be pivoted into the item table or the per-check cards without reading every row

- **Where:**
  - ReviewReport check cards "Uniquely mapped min ≥ 85 % · block 7 / 8 · K562_REP1 84.47 · multiqc:star-uniquely_mapped_percent" (x 290–1415, y 283–425).
  - Item table, worst first, columns "Reads (M)", "dupRadar 1.04", "Genomic origin exonic %" (x 290–1415, y 478–935).
  - Header "8 samples · paused after stage 2 of 4 · waiting 1 h 12" (x 390–1130, y 172–205).
  - Draft: `GET /gates/{id}/checks` (cursor, limit ≤ 200, no filter or sort); no `/gates/{id}/items` (api §5 lists it).
- **Evidence:** api §5: "`GET /gates/{id}/items` (paged, filterable)". Gap #12 (l.535) already covers the missing shape, paging and threshold.
- **Problem:** beyond gap #12, the board needs:
  - per-check aggregates (pass/total, worst item);
  - a sort by worst verdict;
  - item attributes that are not checks (reads, dupRadar, exonic %);
  - the item count in the header.

  With one row per item × check, 500 samples × 6 checks is 3,000 rows, or 15 pages, before the table can draw its first sorted row. The header needs gate → run → graph → workflow version (3 more calls). "Tabs: Summary 4 to check, Samples 1 flagged" also need counts.
- **Proposal:** api-and-data-model.md §5 Gates:
  - keep `GET /gates/{id}/items?sort=worst&verdict=` in 0.0.1, with each item's checks inline (`items[].checks{check_key: {value, verdict}}`) and its `attributes`;
  - add `Gate.summary` {`items_total`, `items_failing`, `checks[]` {key, label, threshold, severity, pass, total, worst_item}};
  - `Gate.run` (UX-271 summary) for the header.

  §7: say that "info" metrics are checks with `severity: info`, or `gate_items.attributes`.
- **Related:** SR-085 (checks shape, frozen check definitions with thresholds, `value` type). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-286 · major · Tabs and row actions that 0.0.1 boards show have no draft operation: Outputs & reports, Software, Environment, evidence report

- **Where:**
  - RunDetail tabs "Outputs & reports", "Software", "Environment" (x 642–1055, y 290–310) and the card "Software (from pipeline_info) … All 64 tools and containers" (x 1097–1415, y 523–718).
  - RunsRows actions "Outputs", "Reports", "Batch", "Adopt…" (x 1310–1400, y 805–1100).
  - ReviewReport tab "Report · MultiQC" (x 670–800, y 240–260).
  - RunsCompare "Reports: MultiQC · 24 samples / depictio dashboard" (x 499–1415, y 930–955).
  - Draft: artefacts, environments and software are left out (README); `CheckResult.file_uri` has no fetch endpoint.
- **Evidence:** draft README: "Left out: … artefacts …". §15.1 lists no outputs view, but the gate needs its evidence.
- **Problem:**
  - The boards offer these as working tabs and buttons.
  - For the 0.0.1 gate, the reviewer cannot open the evidence file (the MultiQC report) that the checks were computed from: `file_uri` is a path with no content route.
  - The Software card has no source at all, since pipeline_info parsing is not in the draft.
  - "Batch" and "Adopt…" belong to deferred features.
- **Proposal:**
  - api-and-data-model.md §5: keep in 0.0.1 at least `GET /runs/{id}/artifacts?role=evidence|report` and `GET /artifacts/{id}/content`, and link `check_results.file_uri` to an `artifact_id`.
  - ui-spec.md §4.4: mark Software and Environment as not-0.0.1 ([UX-227](R7-ui.md)), or define `GET /runs/{id}/software`.
  - Hide Batch and Adopt in 0.0.1. Adopt is CLI, see §15.1.
- **Related:** MultiQC data at gate time: [SR-058](R3-journeys.md) (R3). Question 5.
- **Found by:** ux-reviewer
- **Status:** open

### UX-287 · minor · Process summary lacks failures by class, module ID and not-scheduled reason

- **Where:**
  - RunDetail "Busiest processes" (x 290–1075, y 860–1088: "nf-core/salmon/quant · 2f6b4c1", "48 / 48 running") and "Not scheduled: SALMON_PSEUDO (when: false — --skip_pseudo_alignment true) · 96 tasks" (x 290–1075, y 757–805).
  - RelaunchDialog chips "STAR_ALIGN · out of memory · 3 tasks · OUT_OF_MEMORY", "QUALIMAP_RNASEQ · timeout · 1 task" (x 102–780, y 337–362).
  - RunsCompare "3 failed · 6 retries · STAR_ALIGN OUT_OF_MEMORY at 64 GB" (x 499–790, y 485–515).
  - Draft: `ProcessSummary` {process_or_rule, stage, tasks_by_state, retries, peak_rss_bytes, native_id_range}.
- **Evidence:** gap #34 (l.1137) says the field names are guessed. This finding is about missing content.
- **Problem:**
  - The per-class failure chips need `tasks?state=failed` then `attempts` for each task.
  - "Busiest" has no sort key (gap #18, l.733).
  - The module path and commit, and the `when:` reason with the count of not-scheduled tasks, have no field. Whether `nf-spectio` can report never-created tasks at all is **[to be validated]**.
- **Proposal:** api-and-data-model.md §5 `/processes`: add `failures_by_class` {class: count}, `module` {path, commit}, `not_scheduled` {reason, count | null}, `sort=-tasks_running|-peak_rss`.
- **Related:** SR-088 (`/processes` field names), SR-090 (sortable fields).
- **Found by:** ux-reviewer
- **Status:** open

### UX-288 · minor · Run detail meta strip: work dir, engine version, run number and launched-by have no field

- **Where:**
  - RunDetail meta strip "Engine · Nextflow 25.10.4", "Launched · Alice · in UI", "Work dir /scratch/demo/…" (x 490–1415, y 195–245).
  - "#458"-style numbers on RunsTable, RunsRows, RunsCompare and ReviewReport.
  - RunsCompare "Nextflow · engine of the head job · 25.10.2 → 25.10.4" (x 300–1415, y 765–810).
  - EnvLocal "Queued · position 1".
  - Draft: `Run.bridge_versions` (bridge versions only); `IngestBatch.bridge.engine_version` is not echoed on `Run`; `created_by` is a bare `PrincipalId`.
- **Evidence:** "Nextflow 25.10.4 · nf-core", "#458", "Work dir /scratch/demo/amartin/rnaseq 1025".
- **Problem:**
  - The engine version reaches ingest but is never exposed.
  - The work dir and queue position are not columns.
  - A ULID has no short serial like "#458".
  - `created_by` needs a principal lookup, which the draft lacks (`GET /me`, `/users` are left out), even for the one local user.
- **Proposal:** api-and-data-model.md §7 `runs`:
  - `engine_version` (from the bridge batch), `work_dir` and `queue_position` (nullable);
  - either a per-project `number`, or a board rule to show the last 6 ULID characters.

  §5: keep `GET /me` in 0.0.1 so `created_by` resolves to a display name.
- **Related:** SR-088 (run `name` with a default built from the last 6 ID characters), SR-080 (the ingest batch that carries the engine version). Resume inputs including the engine version: [CH-043](R3-journeys.md) (R3).
- **Found by:** ux-reviewer
- **Status:** open

### UX-289 · minor · "Pause after stage" is the Running header action, but `:pause` and `:resume` are not in the draft

- **Where:**
  - RunDetail header button "Pause after stage" (x 1067–1207, y 116–156).
  - Legend "Paused · Paused by Alice · resumable" (x 57–475, y 328–378).
  - Draft: `RunState` includes `pausing` and `paused`, but no operation leads there (README: "Left out: pause/resume").
- **Evidence:** ui-spec §4.4 table "Running | Pause after stage · Cancel". §7.1: "which verbs lead there is open, inbox #16".
- **Problem:** the 0.0.1 RunDetail shows a primary action the contract does not have. The enum carries states no 0.0.1 call can reach, so clients must still render them.
- **Proposal:**
  - ui-spec.md §4.4: in 0.0.1 the Running row shows "Cancel" only, under UX-227's marking.
  - api-and-data-model.md §7.1: note that `pausing` and `paused` are reachable only once `:pause` ships, or add `:pause` / `:resume` to the 0.0.1 cut.
- **Related:** SR-081 (the run-actions table lists `:resume` and `paused` as a source state). State machine: [CH-042](R3-journeys.md) (R3).
- **Found by:** ux-reviewer
- **Status:** open

### UX-290 · minor · Legend and the draft enums disagree: no Cancelling or Pausing chip, `stored` vs "Cached / storeDir", stage states free text

- **Where:**
  - Legend "Run states" (x 57–475, y 135–570) draws 7 of the 9 `RunState` values.
  - "Task states by engine" (x 965–1385, y 85–385) has 9 rows; draft `TaskState` has 10 (`cached` and `stored` separate).
  - "Stage gauge" has 6 looks (x 511–930, y 135–328); draft `Stage.state` is a free string.
  - Draft: `RunState`, `TaskState`, `Stage.state`.
- **Evidence:** Legend row "Cached · CACHED / storeDir · up to date". ui-spec §3.1 lists `cancelling` and `pausing` with an icon and colour.
- **Problem:**
  - `cancelling` is reachable in 0.0.1 (`:cancel`), but no board or legend draws it.
  - The task-state mapping that the boards use (stored merged into cached) differs from the draft's enum.
  - Gaps #6 (l.276) and #35 (l.1163) say no enum exists. This finding adds that the Legend board already implies one, and the draft's guess does not match it.
- **Proposal:**
  - ui-spec.md §3.1/§3.2: own the display mapping, and add the Cancelling chip to Legend.
  - api-and-data-model.md §7: take the Legend's six gauge looks as the `Stage.state` enum (`completed|running|awaiting_review|failed|skipped|not_started`), and decide `stored` vs `cached` once.
- **Related:** SR-082 (proposes the same six stage states), SR-083 (keeps `stored` separate from `cached` in `attempts.state`; the two proposals must agree). The missing Pausing and Cancelling chips were already noted in R1 (pending), as listed in R3's "Cited, not repeated".
- **Found by:** ux-reviewer
- **Status:** open

### UX-291 · minor · RunsCompare "Outcome" and "CPU-hours" rows need per-run check and accounting data that 0.0.1 does not have

- **Where:**
  - RunsCompare "OUTCOME · medians over samples, from MultiQC data" (x 290–1415, y 815–955).
  - "CPU-hours · from sacct TotalCPU; saved = what the reused tasks cost" (x 290–1415, y 965–1070).
  - Draft: checks only under `/gates/{id}/checks`; no run-level check list; no CPU accounting.
- **Evidence:** "STAR uniquely mapped · 91.2 % · 21 of 24 samples only" for a run that failed before its gate. "412 CPU-h · 61 lost to failed attempts".
- **Problem:**
  - A run without an opened gate has no check results reachable in the draft, since live checks are deferred.
  - Medians across items are not computed anywhere.
  - CPU-hours come from sacct, and SLURM is deferred. Summing `attempts.resources` would mean reading every attempt of every task.

  Compare reachability itself is R3 [UX-250](R3-journeys.md).
- **Proposal:**
  - ui-spec.md §4.4 / RunsCompare: mark Outcome and CPU-hours as not-0.0.1.
  - Later, api-and-data-model.md §5: add `GET /runs/{id}/checks?check_key=&aggregate=median` and a `resources_total` {cpu_seconds, saved_cpu_seconds} on `Run`, computed from `attempts.resources` for local runs.
- **Related:** question 5.
- **Found by:** ux-reviewer
- **Status:** open

## Appendix A · x-spec-gap to finding map

All 43 `x-spec-gap` entries of `spikes/openapi-draft/openapi.yaml` on branch `autopilot/R6` (`b9c01fd`). "#" is the ordinal used by the ux-reviewer, "Line" the line used by the spec-reviewer. "Owner" is the finding that places the gap (spec-reviewer's map); "Also cited by" lists ux-reviewer findings and coverage rows that cite the same gap.

**Totals:** 40 gaps are placed in an R6 finding (4 of them, l.74, l.249, l.560 and l.1070, also shared with an R3 finding); 3 are placed only in an existing R3 finding (l.136, l.311, l.1042). No gap is unplaced.

| # | Line | Gap | Owner | Also cited by |
|---|---|---|---|---|
| 1 | 39 | Loopback: no Origin / Host / CSRF rule in single mode (root SEC-102) | SR-091 | — |
| 2 | 74 | `POST /workflows` body; import body owned by R3 SR-056 | SR-086 (+ SR-056) | coverage: Launch |
| 3 | 136 | `ui:` block and schema merge for the Snakemake form | R3 SR-065 (also UX-119) | UX-277; coverage: LaunchSnakemake |
| 4 | 228 | `:cancel` result, 409 or idempotent 200 | SR-081 | — |
| 5 | 249 | Relaunch: new run or new launch | SR-081 (+ SR-063) | coverage: RelaunchDialog |
| 6 | 276 | No stages endpoint, no stage-state enum | SR-082 | UX-290; coverage: RunDetail, Legend |
| 7 | 311 | `/params` response shape | R3 SR-064 | UX-282 |
| 8 | 335 | Lineage response shape, "what changed" | SR-081 | UX-282; coverage: RunDetail, RunsCompare |
| 9 | 383 | Run log: which file, launch, content type | SR-089 | UX-273 |
| 10 | 447 | Task log: which attempt, runner offline | SR-089 | — |
| 11 | 495 | No `run` filter on `GET /gates` | SR-085 | UX-271; coverage: RunsTable |
| 12 | 535 | Checks shape, paging, thresholds | SR-085 | UX-285; coverage: ReviewReport |
| 13 | 560 | Decision: (1) relaunch from a gate → R3 SR-062; (2) missing If-Match; (3) response body | SR-085 (+ SR-062) | UX-283, UX-284; coverage: ReviewReport |
| 14 | 594 | `GET /events`: envelope or row; `after` vs cursor | SR-084 | — |
| 15 | 631 | SSE filters, delta, "task open", `event:` field | SR-084 | — |
| 16 | 664 | Ingest: api §14 does not exist (with SR-054) | SR-080 | — |
| 17 | 726 | `limit` default | SR-090 | — |
| 18 | 733 | Sortable fields | SR-090 | UX-274, UX-287; coverage: RunsTable |
| 19 | 749 | `Idempotency-Key` required, length | SR-090 | — |
| 20 | 839 | ID prefixes beyond `run_`, `gate_`, `prj_` | SR-090 | — |
| 21 | 845 | Stage reference: id string or index | SR-082 | — |
| 22 | 868 | Field errors, problem-type catalogue | SR-090 | UX-276 |
| 23 | 880 | List items member | SR-090 | — |
| 24 | 890 | `local` missing from `workflows.source` | SR-086 | — |
| 25 | 902 | No workflow `name` column | SR-086 | UX-270; coverage: Launch |
| 26 | 916 | No workflow `location` field | SR-086 | — |
| 27 | 970 | `relaunch_mode` values | SR-081 | coverage: RelaunchDialog |
| 28 | 1008 | Launch response `links` | SR-087 | — |
| 29 | 1009 | Run name, counters, tags | SR-088 | UX-271, UX-282; coverage: RunsTable |
| 30 | 1042 | Default `environment_id`; SR-087 links to it | R3 SR-055 | coverage: Launch, EnvLocal |
| 31 | 1053 | `gates` values beyond `from-manifest` | SR-087 | UX-278; coverage: Launch |
| 32 | 1057 | `notify.webhook_ids` outside 0.0.1 | SR-087 | — |
| 33 | 1070 | Relaunch field names, merge or replace (with SR-063) | SR-081 (+ SR-063) | UX-280; coverage: RelaunchDialog |
| 34 | 1137 | `/processes` field names | SR-088 | UX-287 |
| 35 | 1163 | Task-state enum | SR-083 | UX-290; coverage: Legend |
| 36 | 1250 | `check_results.value` type | SR-085 | — |
| 37 | 1281 | `actor_kind` wire values | SR-085 | — |
| 38 | 1356 | `spectiosequence` vs `sequence`, value type | SR-084 | — |
| 39 | 1358 | Per-type `data` schemas | SR-084 | — |
| 40 | 1386 | Content of a coalesced task event | SR-084 | — |
| 41 | 1449 | RunDelta not in the "complete" catalogue | SR-084 | UX-271 (via the §8.3 delta) |
| 42 | 1492 | `IngestBatch` envelope invented | SR-080 | UX-272 |
| 43 | 1502 | `IngestAck` invented | SR-080 | — |

## Appendix B · 0.0.1 board coverage

From the ux-reviewer: which draft operations each 0.0.1 board would call, and whether the draft serves it. Board renders were made at 1440×1180 in `/tmp/r6-ux/` and are not kept. Fully served: none. Partly served: 9. Not served: 2 (Manifest, and EnvLocal, which is context only).

| Board | Draft operations it uses | Served |
|---|---|---|
| Launch | getWorkflow, listWorkflowVersions, getWorkflowVersionSchema, launchRun | **partly**: form and launch work. File checks and Recheck, Browse, environment, profile and gate pickers, and the disabled-button reason are not served (UX-276, UX-278, UX-279; gaps #2, #25, #30, #31) |
| LaunchSnakemake | same as Launch | **partly**: also two sample tables and the software deployment method (UX-277; gap #3) |
| RunsTable | listRuns, streamEvents; per row getRunGraph, listRunProcesses, listGates?run, plus workflow lookup | **partly**: headline counts, filters, totals, Started/Duration, workflow column and the progress summary are not served (UX-270 to UX-275; gaps #11, #18, #29) |
| RunsRows | listRuns (×2 for sections), per row getRunGraph, listGates?run, listGateChecks, listRunTasks, listTaskAttempts; relaunchRun | **partly**: N+1 context lines; Outputs, Reports, Batch and Adopt have no operation (UX-271, UX-273, UX-274, UX-286) |
| RunDetail | getRun, getRunGraph, listRunProcesses, listGates?run, getRunParams (×2), getRunLineage, cancelRun, relaunchRun, streamEvents | **partly**: pause, decided-gate note, manifest source, Software, Environment and Outputs tabs, meta strip fields and times (UX-272, UX-273, UX-278, UX-282, UX-283, UX-286 to UX-289; gaps #6, #8) |
| Legend | enums RunState, Stage.state, TaskState, Engine, WorkflowSource | **partly**: enum mismatches; context lines need UX-271 and UX-273 fields (UX-290; gaps #6, #35) |
| RelaunchDialog | getRun, getRunGraph, listRunProcesses, listRunTasks?state=failed, listTaskAttempts, getRunParams, relaunchRun | **partly**: mode and parameter overrides are served. Resource overrides, preview, suggestions and Copy are not (UX-279 to UX-281, UX-287; gaps #5, #27, #33; Continue at a gate is R3 SR-062) |
| RunsCompare | getRunLineage, getRun ×3, getRunGraph ×3, listRunProcesses ×3, getRunParams ×3 | **partly**: from-stage, actor, config and samplesheet changes, engine version, outcome and CPU-hours are not served (UX-279, UX-280, UX-282, UX-288, UX-291; gap #8) |
| Manifest | (getRunGraph for stage names only) | **not**: no manifest operation in the draft (UX-278) |
| ReviewReport | getGate, listGateChecks, decideGate (approve/stop), getRun | **partly**: the primary action needs a change set; items, aggregates, history, evidence report and queue position are not served (UX-283 to UX-286; gaps #12, #13) |
| EnvLocal (§1 frame, context only) | none | **not**: no environment or runner operation (R3 SR-055, which absorbs UX-247; gap #30; UX-275) |

**Basic journeys are served.** Every 0.0.1 journey can be served at a basic level: launch with parameters, monitor, approve or stop, relaunch with parameter overrides, and read the parameters per run. The ux-reviewer's findings are about what the boards show beyond that, and about N+1 calls.
