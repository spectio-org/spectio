# R3 · End-to-end journeys (0.0.1)

**Step page:** [R3](../progress/W2/R3.md)

**Round:** R3 (journeys) · **Date:** 2026-10-27 · **Found by:** spec-reviewer (journeys 1–2), constraints-hunter (journeys 3–4), ux-reviewer (all four journeys, boards rendered) · **Status of the round:** triaged (TRIAGE2, 2026-10-27): 6 accepted, 0 rejected, 21 inbox (16 assumed) · triage: [TRIAGE2](../progress/W2/TRIAGE2.md)

**Sources.**
- **Branch and commit:** `autopilot/integration` at `e22e376`. Line numbers ("l.") refer to that commit.
- **Round brief:** [`next-phase.md`](../playbooks/next-phase.md) R3. Scope is 0.0.1 only ([`mvp-0.0.1.md`](../specs/mvp-0.0.1.md), [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md) §15): one user, no sign-in, engines on the same machine, SQLite, `spectio serve --with-runner`. Out of scope: users, roles, SLURM, Kubernetes, depictio, LabID, phones.
- **Journeys:**
  1. a researcher installs the Python bundle on a laptop, registers nf-core/rnaseq, launches it with a QC gate after the first stage, reads the checks, approves, and the run continues;
  2. the same with a Snakemake workflow, where the gate fails, the researcher changes two parameters, relaunches, then compares the two runs' parameters;
  3. a run fails on one task: the researcher finds the failing task, reads its log and relaunches from the cache;
  4. the server restarts while a run is active, and the run's state, tasks and stages are still right afterwards.
- **Reviewer scopes:**
  - spec-reviewer, journeys 1 and 2: [`mvp-0.0.1.md`](../specs/mvp-0.0.1.md), [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md), [`ui-spec.md`](../specs/ui-spec.md), [`api-and-data-model.md`](../specs/api-and-data-model.md), [`checking-scenarios.md`](../specs/checking-scenarios.md), [`synthesis.md`](../specs/synthesis.md), [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md), [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md), the [decision log](../decisions/log.md) and the [inbox](inbox.md);
  - constraints-hunter, journeys 3 and 4: the same specs plus [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md), [`admin-and-operations.md`](../specs/admin-and-operations.md) and the [synthetic-pipelines spike note](../research/spike-synthetic-pipelines-2026-10-26.md);
  - ux-reviewer, all four journeys: the 11 boards of the 0.0.1 map (EnvLocal, Launch, LaunchSnakemake, RunsTable, RunsRows, RunDetail, Legend, RelaunchDialog, RunsCompare, Manifest, ReviewReport) plus three boards the journeys need but the map leaves out (RunFailed, WorkflowImport, WorkflowOverlay). Each was rendered with `tools/canvas/render.js` and looked at (renders in `/tmp/r3-ux/`, not kept in the repository).
- **Reviewer status:** all three reviewers returned output. None failed.
- **External code:** no external code was read in this round. Facts about Nextflow, Snakemake and systemd keep the source the specs or earlier rounds give (Nextflow `114f1fe` `Session.groovy:609-615` and Snakemake `1c67a66` `job_scheduler.py:171, 241-245`, both as cited at synthesis §5ter.3; systemd.kill as cited by R4 CH-028), or are marked **[to be validated]**.
- **Earlier rounds:** open findings in [R1](R1-consistency.md), [R4](R4-constraints.md), [R7](R7-ui.md) and [R12](R12-ui-scenarios.md) are cited, not repeated. See [§ Cited, not repeated](#cited-not-repeated).

**Merge method** (review-round skill, steps 3-4):
- **Input:** 37 findings. spec-reviewer returned 15 (5 blockers, 9 majors, 1 minor) as SR-054 to SR-068. constraints-hunter returned 11 (2 blockers, 8 majors, 1 minor) as CH-041 to CH-051. ux-reviewer returned 11 (2 blockers, 8 majors, 1 minor) as UX-241 to UX-251. Every original ID is kept.
- **De-duplication:** ten findings describe the same problem as another finding and were merged into it. The primary is the most complete finding; it takes the other's evidence and its "Found by". Each primary lists what it absorbs, and each absorbed ID has a one-line stub in the findings table:
  - UX-242 → SR-062 (relaunch at a failed gate);
  - SR-060 → CH-042 (launch completion mapped onto the run state);
  - SR-068 → CH-043 (launch directory, session ID, `spectio://results`);
  - UX-241 → SR-057 (no 0.0.1 path to register rnaseq and give it a gate);
  - UX-251 → SR-058 (`multiqc:` checks have no reader or data at the gate);
  - UX-248 → SR-061 (failures before the engine starts);
  - UX-246 → CH-041 (server restart and the engine head);
  - UX-244 → CH-048 (task and run logs);
  - UX-247 → SR-055 (no local environment or runner record; EnvLocal draws a separate runner);
  - UX-245 → CH-047 (why a run failed, on a local run).
- **Not merged, linked:** UX-243 (no parameter editor in the relaunch dialog) depends on SR-062's decision but is a separate board gap, so it stays with a **Related** line. SR-056 (registration contract) and SR-057 (rnaseq gate path) share UX-241's WorkflowImport evidence; SR-056 keeps the API contract, SR-057 the screens and the overlay. SR-063 (`:relaunch` contract) and CH-042 (state machine) touch the same verbs from two sides and are cross-linked.
- **Verification:** every blocker and major (25 primaries, plus the 9 absorbed blockers and majors) was checked with `grep` against the cited spec lines at `e22e376`. All 34 reproduced; **0 findings were dropped and 0 were downgraded**. Corrected: 4; confirmed after a doubt: 1 (CH-046).
  - **SR-055:** `--with-runner` is in architecture §7.1 (l.331), not §7.2.
  - **UX-246 (now in CH-041):** "synthesis §6" is §5ter.6 (l.281); synthesis §6 is "Results visualisation".
  - **CH-044:** the spool quote was a paraphrase. The text is "keeps at least 24 h or 200 MB of events, whichever comes first (the bound the ingest contract sets, api §14); beyond it the oldest non-terminal events are dropped first, terminal events never" (architecture §13.2).
  - **CH-046:** the reviewer's quote "an OOM-killed head ends without `onFlowComplete`" is in schedulers §3.1 (l.64); the citation stands as written.
  - **UX-250:** RunsCompare is reachable not only from Coverage.dc.html:80 but also from the Lineage tab of RunFailed, RunLiveChecks and RunOutputs. None of those three is on the 0.0.1 map, and RunDetail, RunsTable and RunsRows still have no link, so the finding stands.
- **Ranking:** by severity, then by the number of documents the finding touches (specs, boards, the decision log, the inbox).
- **Proposed new sections:** this file reuses the numbers earlier rounds assigned (api §14 ingest contract, architecture §7.7 runner protocol). One new subsection is proposed: "Local launcher: detach, adopt, exit" under schedulers §3.1 (CH-041); its number is assigned at apply time, after the existing subsections.

Format: [`README.md`](README.md). Prefixes `SR`, `CH`, `UX`. Specs were not edited in this round.

## Summary

![R3 round map: four 0.0.1 journeys step by step, each step specified or pinned with the finding that breaks it](../assets/diagrams/r3_journeys_map_light.png#only-light)
![R3 round map: four 0.0.1 journeys step by step, each step specified or pinned with the finding that breaks it](../assets/diagrams/r3_journeys_map_dark.png#only-dark)

| Severity | Count |
|---|---|
| Blocker | 7 |
| Major | 18 |
| Minor | 2 |
| **Total** | **27** |
| Merged into another finding | 10 |
| Dropped (not reproducible) | 0 |

**What the numbers say.** None of the four journeys can be finished from the specs as written. Journey 1 stops at the gate (no stages for rnaseq, no MultiQC data, launch completion read as success). Journey 2 stops at the relaunch (two incompatible flows, no parameter editor). Journey 3 stops at Resume (`failed` is terminal). Journey 4 stops at the restart (nothing says whether the engine survives the server). Two contracts that every journey needs, the ingest contract and the local environment and runner record, are parked as "not needed for 0.0.1".

**The five findings that matter most:**
1. **CH-042 (absorbs SR-060): the run state machine.** A gated launch ends normally, so §7.1 marks the run `succeeded` and it can never reach the gate; `failed` is terminal, yet the UI offers Resume on it.
2. **SR-062 (absorbs UX-242): "relaunch with changed parameters" at a failed gate is two incompatible flows**, one run (`apply`, `go_back`) or two runs (`stop`, `:relaunch`), and no 0.0.1 screen draws either.
3. **SR-057 and SR-058: the rnaseq gate cannot exist and cannot be evaluated.** rnaseq declares no stages and 0.0.1 has no overlay path; after stage 1 MultiQC has not run, and the default install has no MultiQC.
4. **CH-041 (absorbs UX-246): the engine head is a child of `spectio serve`.** A restart can kill it, and if it survives, nothing finds it again, reads its exit code or stops a second head from starting.
5. **SR-054 and SR-055: the ingest contract (api §14) and the local environment and in-process runner** are listed as "not needed for 0.0.1", yet no bridge build and no launch can work without them.

## Journeys walked

Each step ends with the spec section that covers it, or with the primary finding that reports the gap. Absorbed IDs are shown through their primary.

**Journey 1: Python bundle on a laptop, nf-core/rnaseq, gate after stage 1, approve, the run continues**
1. Install `uv tool install "spectio[server]"` (architecture §7.3); the install carries no MultiQC reader and no engine prerequisites: GAP → SR-058, SR-067.
2. `spectio init` creates the instance, user, group and project, but no environment and no runner: GAP → SR-055.
3. `spectio serve --with-runner` starts the server and the local runner in one process; the first-run screen is UX-211 (accepted): specified (architecture §7.1).
4. Check that the engines and both bridges are ready: EnvLocal draws a separate runner service and no bridge readiness: GAP → SR-055, SR-067.
5. Register nf-core/rnaseq (`POST /workflows:import`, `spectio workflow import`, WorkflowImport): the contract is undefined and the screen is not in 0.0.1: GAP → SR-056, SR-057.
6. Declare a stage and a gate after stage 1: rnaseq declares none and there is no overlay path in 0.0.1: GAP → SR-057.
7. Fill in the form from `nextflow_schema.json` (ui §4.6, api §5 `GET /workflow-versions/{id}/schema`); the environment card has nothing real to show: GAP → SR-055.
8. Press Launch (`POST /runs`, api §5): no `environment_id` default, no defined `gates` values, no `spectio://results`, no submitting or 422 state: GAP → SR-055, SR-057, CH-043, SR-061.
9. The runner starts `nextflow run` with the stop config and nf-spectio; how the run ID reaches the plugin, a refusal below the version floor, and where the launch directory and session ID are stored: GAP → SR-054, SR-061, CH-043.
10. Events reach `POST /ingest/events`: GAP → SR-054.
11. Watch stage 1 (`queued` → `running`, Summary, SSE, RunsTable and RunsRows): specified (api §7.1, ui §4.3, ui §4.4, api §8.3).
12. Stage 1 ends and the head exits normally: GAP → CH-042.
13. Gate-time check evaluation (binding on the runner, verdict on the server, checking §11.1); no MultiQC data exists at this point: GAP → SR-058.
14. Does the gate open when every check passes? GAP → SR-059.
15. Read the checks (ui §4.5, api §5 `GET /gates/{id}/checks`); RunDetail is never drawn awaiting review: GAP → SR-062.
16. Approve (`POST /gates/{id}/decisions` with If-Match, `spectio gate decide`, api §5, cli §2); no plain "Approve and continue" and no "approved by you" record is drawn: GAP → SR-062.
17. Continue as a new launch with `-resume <sessionId>` (api §7 `launches`, synthesis §5ter.5); the session ID is stored nowhere: GAP → CH-043.
18. `awaiting_review` → `running` → `succeeded` (api §7.1); which launch's completion ends the run is ambiguous: GAP → CH-042.

**Journey 2: Snakemake, the gate fails, change two parameters, relaunch, compare**
1. Install, init and serve, as in journey 1: GAP → SR-055, SR-067.
2. Register a Snakemake workflow from a Git URL or a local path (fallback at ui §4.7, `local/…` key at api §7); the contract is missing: GAP → SR-056.
3. `spectio.yml` in the repository declares the stages and a gate: specified (checking §12.1–§12.4).
4. Launch form from the Snakemake config schema plus the `ui:` block; the `ui:` block is undrafted and there is no fallback: GAP → SR-065.
5. `POST /runs`, and how the parameters reach Snakemake: GAP → SR-065.
6. The runner builds `snakemake --logger spectio --until <last rules>` in the workflow's environment: GAP → SR-066, SR-067.
7. Events from the logger plugin: GAP → SR-054.
8. Watch the run (RunDetail is engine-agnostic): specified (ui §4.4).
9. `--until` is reached and Snakemake exits 0: GAP → CH-042.
10. A `block` check fails and the gate opens: specified (checking §4, api §7.1).
11. Read the failing checks (ui §4.5, api §5); ReviewReport is drawn only for nf-core with MultiQC: GAP → SR-062.
12. Change two parameters: GAP → SR-062, UX-243.
13. Relaunch: GAP → SR-063, UX-243.
14. The new run reruns the affected jobs (`--forcerun`, synthesis §5ter.5); which stage and which directory: GAP → SR-063, CH-043.
15. Parameters stored per run (`run_inputs`, api §7); stored against resolved values: GAP → SR-064.
16. Compare the two runs' parameters (Parameters tab, Lineage, RunsCompare): GAP → SR-064, UX-250, UX-249.

**Journey 3: a task fails, the researcher finds it, reads its log and resumes from the cache**
1. A run is launched locally and events flow through the bridge: specified (mvp §2, api §5, architecture §13.1).
2. A task fails and the engine retries it (synthesis §2ter); which task caused the run failure under retries, `ignore`, `finish` or `--keep-going`: GAP → CH-047.
3. The run ends `failed` when the engine reports it (api §7.1); a head that dies without a terminal event: GAP → CH-046.
4. The failure class comes from the trace status, error text and exit code (schedulers §3.5, spike note finding 2), but the class sources are `sacct` or Kubernetes only: GAP → CH-047.
5. Notice the failure (RunsRows "Needs attention", RunsTable state rail): specified (ui §4.3).
6. Open the failed run and see why it failed; ui §3.1 gives only "Engine or task failure; resumable", and RunFailed is SLURM-only and off the map: GAP → CH-047.
7. Find the failing task with the Tasks-tab filter (ui §4.4); the tab is never drawn and retries are not grouped: GAP → CH-047, CH-048.
8. Read the task's stdout and stderr (`GET /tasks/{id}/logs/{stdout|stderr}`, api §5); the file sources and the Logs tab are missing: GAP → CH-048.
9. Read the run log (`GET /runs/{id}/logs`); its source is not specified: GAP → CH-048.
10. Click Resume on the Failed run (ui §4.4 l.118) against api §7.1, which has no way out of `failed`: GAP → CH-042.
11. The relaunch dialog offers Resume with a reuse strip (ui §4.6; estimate in CH-010, UX-109); its suggestions come from `sacct`: GAP → CH-047.
12. `:resume` or `:relaunch`, on the same run or a new one: GAP → CH-042, SR-063.
13. The resume waits until the previous head is gone and its lock is free: specified (synthesis §5ter.2 `CONTINUE_REQUESTED`, CH-003 partly applied).
14. The runner runs `nextflow run -resume <sessionId>` in the same launch directory: GAP → CH-043.
15. Snakemake reruns in the same directory, with or without `--unlock` and `--rerun-incomplete`: GAP → CH-043.
16. Cached work is reported and merged with the first launch's tasks: GAP → CH-050.
17. The failed task reruns as a new attempt across launches: GAP → CH-050.
18. The run goes `failed` → `running` → `succeeded`: GAP → CH-042.
19. Follow the new run through the Lineage aside: specified (ui §4.4).
20. Counters and the gauge are right at the end: GAP → CH-050.

**Journey 4: the server, with its in-process runner, restarts while a run is active**
1. One run is `running` and another is `awaiting_review` with an open gate: specified (api §7, §7.1).
2. `spectio serve` gets SIGTERM or dies (`kill -9`, OOM, Ctrl-C); there is no shutdown sequence for the in-process runner: GAP → CH-041.
3. What happens to the engine head (survives, dies with the process group or cgroup, breaks on a stdout pipe): GAP → CH-041.
4. The engine keeps emitting and the bridge appends to the spool (architecture §13.1, §13.2; bounds pending api §14, SR-001): specified (architecture §13.1).
5. The browser during the outage: "Spectio is unreachable" is specified (ui §11) but undrawn (UX-205), and the single-process case has no frame: GAP → CH-041.
6. The sidebar footer keeps showing "Server · online" and "Runners 3 / 4 online": GAP → CH-041, SR-055.
7. Nobody forwards the spool during the downtime, and after the restart the offset to forward from is not defined: GAP → CH-044.
8. SQLite reopens and recovers its WAL (architecture §7.2); the order of the recovery steps is not defined: GAP → CH-051.
9. The projector catches up on events acknowledged but not projected: GAP → CH-045.
10. The runner re-adopts live heads; only "reconciliation with the database, PIDs and `sacct`" exists (synthesis §5ter.6): GAP → CH-041.
11. Runner-offline flags are held back after boot: specified (admin §3.2, CH-033 applied).
12. A `runner_commands` row leased before the crash is delivered again, with no idempotent local launch: GAP → CH-041.
13. The head finished during the downtime and its terminal event is in the spool; replay plus the lattice handle it once CH-044 is fixed: specified (api §8.2).
14. The head was killed with the server and left no terminal event, so the run stays `running`: GAP → CH-046.
15. Tasks that were running when the head died stay `running`: GAP → CH-046.
16. A stage boundary reached during the downtime must open its gate after the replay: GAP → CH-045, CH-049.
17. The open gate survives (`gates` row, api §7.1), but a timeout that expired during the downtime is not handled: GAP → CH-049.
18. A `check.dispatch` evaluation interrupted mid-way has no lease and waits forever: GAP → CH-049.
19. A decision just after the restart: Continue waits for the head and lock check (synthesis §5ter.2), which needs the head re-adopted first: GAP → CH-041.
20. The browser reconnects with `Last-Event-ID` (cursor issues in CH-018): specified (api §8.2, ui §11).
21. While the server catches up, the UI shows stale "running" with no recovery signal: GAP → CH-051.

## Findings table

| ID | Severity | Title | Documents touched | Status |
|---|---|---|---|---|
| SR-062 | blocker | "Relaunch with changed parameters" from a failed gate is two incompatible flows, and neither is drawn | 7 | inbox, assumed (#32) |
| SR-055 | blocker | No local environment, runner record or in-process runner interface in 0.0.1 | 7 | inbox, assumed (#35) |
| SR-057 | blocker | nf-core/rnaseq cannot be registered, get a stage and get a gate in 0.0.1 through any specified path | 7 | inbox (#34) |
| CH-041 | blocker | In-process runner: the engine head's fate on server stop, re-adoption and exit code are unspecified | 7 | inbox, assumed (#35) |
| CH-042 | blocker | Run state machine: `failed` is terminal yet "resumable", and launch outcomes are mapped onto the run state | 5 | inbox, assumed (#32) |
| SR-058 | blocker | At gate time after stage 1, `multiqc:` bindings find no MultiQC data, and 0.0.1 installs no MultiQC | 4 | inbox (#34) |
| SR-054 | blocker | 0.0.1 needs the ingest contract, but the log parks it as "not needed for 0.0.1" | 5 | inbox (#36) |
| SR-061 | major | Failures before the engine starts have no state transition, reason or screen | 5 | inbox, assumed (#40) |
| CH-047 | major | "Why did it fail": no run-level failure cause, no pointer to the failing task, and no local failure classes | 6 | inbox, assumed (#40) |
| SR-056 | major | Registering a workflow is outside the 0.0.1 cut, and its contract is undefined | 6 | inbox (#34) |
| CH-043 | major | Resume inputs are not stored: launch directory, engine session ID, engine version, Snakemake unlock and rerun flags | 5 | inbox, assumed (#40) |
| SR-063 | major | The `POST /runs/{id}:relaunch` contract is undefined | 4 | inbox, assumed (#32) |
| SR-064 | major | Parameter history: stored vs resolved values, Snakemake config, response shape | 4 | accepted |
| SR-067 | major | Engine prerequisites on a laptop: who provides Java and Nextflow, the Snakemake environment and the bridges | 4 | inbox (#35) |
| CH-044 | major | The spool forward cursor, replay order and drop policy after a restart are unspecified | 3 | accepted |
| CH-046 | major | A head that ends with no terminal event leaves the run and its tasks `running` forever on the local launcher | 3 | inbox, assumed (#40) |
| CH-048 | major | Task and run logs on the local executor: sources unspecified, Tasks and Logs tabs never drawn | 5 | inbox, assumed (#40) |
| CH-049 | major | An open gate across a restart: expired timeouts, interrupted check evaluation, stuck background tasks | 4 | accepted |
| CH-050 | major | Task identity across launches of one run: cached tasks reported by Nextflow and silent in Snakemake | 3 | inbox, assumed (#40) |
| SR-059 | major | When every check passes, does the planned stop open a gate or continue automatically? | 3 | inbox, assumed (#33) |
| SR-065 | major | The Snakemake launch form and parameter delivery are not specified for 0.0.1 | 3 | inbox, assumed (#40) |
| UX-243 | major | Relaunch with changed parameters has no parameter editor and no Snakemake variant | 3 | inbox, assumed (#32) |
| UX-250 | major | RunsCompare cannot be reached from a 0.0.1 run screen, and draws data a local run does not have | 5 | inbox, assumed (#40) |
| CH-045 | major | The projector has no checkpoint: events acknowledged but not projected at a crash, re-projection and catch-up order | 2 | accepted |
| SR-066 | major | How the runner computes the Snakemake `--until` targets from `match` globs is unspecified | 2 | accepted |
| CH-051 | minor | Boot recovery has no defined order and no "catching up" signal in the UI | 4 | inbox, assumed (#40) |
| UX-249 | minor | RunDetail's "Parameters changed vs. previous run" lists a parameter that did not change | 2 | accepted |
| SR-060 | major | The end of a gated launch has no defined mapping to run states | — | merged into CH-042 |
| SR-068 | minor | Run directories, the engine session ID and `spectio://results` are undefined for local runs | — | merged into CH-043 |
| UX-241 | blocker | The 0.0.1 map has no screen to register a workflow or attach the overlay that defines its gate | — | merged into SR-057 |
| UX-242 | blocker | The 0.0.1 gate (approve and continue, or relaunch with changed parameters) is not drawn, and its relaunch path contradicts itself | — | merged into SR-062 |
| UX-244 | major | The Tasks and Logs tabs are never drawn | — | merged into CH-048 |
| UX-245 | major | A failed run's explanation depends on `sacct`, and RunFailed is not on the 0.0.1 map | — | merged into CH-047 |
| UX-246 | major | Server restart in 0.0.1: no screen during or after the outage, no state for an engine lost while down | — | merged into CH-041 |
| UX-247 | major | EnvLocal draws a separate runner service, not the 0.0.1 single process, and does not show engine readiness | — | merged into SR-055 |
| UX-248 | major | From the Launch button to the first event: no submitting, starting or "engine did not start" state | — | merged into SR-061 |
| UX-251 | major | With the default install, the rnaseq gate's checks have no reader, and the `n/a` check state is not drawn | — | merged into SR-058 |

---

## Blockers

### SR-062 · blocker · "Relaunch with changed parameters" from a failed gate is two incompatible flows, and neither is drawn

- **Where:** owner ui-spec.md §4.4 (actions by state), with api-and-data-model.md §5 and §7.1; mvp-0.0.1.md §2; synthesis.md §5ter.2; ui-spec.md §4.5, §4.6. Boards: ReviewReport (sticky bar "More ▾ · Discard changes · Apply and continue", x 1030–1416, y 1124–1166; the More items exist only in a `title` tooltip, ReviewReport.dc.html:237; header "Review queue · 5 of 8 assigned to you", "Can decide AM +3", "AI · suggests"); RunDetail (no awaiting-review variant); RelaunchDialog (footer note, x 102–530, y 870–902).
- **Evidence:**
  - "approve then continue, or relaunch with changed parameters" (mvp §2).
  - "Awaiting review | Review (opens the gate) · Cancel" (ui §4.4, l.116). There is no Relaunch.
  - Review Parameters tab: "Change parameters for the next stages"; "Apply and continue"; More: "go back to an earlier stage, stop the run here" (ui §4.5).
  - "`awaiting_review` → `running`: decision `approve`, `apply` or `go_back` starts the next launch"; "`awaiting_review` → `cancelled`: decision `stop`" (api §7.1, l.268).
  - "`params_changed` → `RUNNING(k or chosen stage)` with the new parameters" (synthesis §5ter.2, l.243).
  - "**Resume** (labelled **Continue** on a paused run or an open gate)" (ui §4.6, l.163). RelaunchDialog repeats it, so the dialog can be opened at a gate.
  - `launches`: "one row per head process of a run (first launch, each Continue, resume or relaunch)" (api §7, l.238), against `runs.parent_run_id, relaunch_mode` and the separate `POST /runs/{id}:relaunch` (api §5).
  - No board shows `awaiting_review` → `running` after a person's decision. RunDetail's only gate line is "approved automatically by QC agent". ReviewReport draws only "Apply and continue" with item changes, no plain "Approve and continue", and only for nf-core with MultiQC.
- **Problem:** the researcher must fix parameters of the stage that failed.
  - **Path A**, gate `apply` or `go_back` with a parameter change set, keeps one run. But ui-spec says changes apply only to "next stages", and nothing says whether `go_back` carries a change set.
  - **Path B**, `stop` → Cancelled → Relaunch…, creates a second run. A QC failure is then recorded as a cancel, and Run detail offers no Relaunch at a gate.

  The choice changes the data model, the lineage and what RunsCompare compares; "compare the two runs" works only with Path B. The 0.0.1 screen does not exist: the drawn screen is the full multi-reviewer one.
- **Proposal:** Thomas picks one path for 0.0.1 (question 1). spec-reviewer recommends Path B; ux-reviewer proposed Path A through `go_back`. This merge recommends Path B, because it matches journey 2's "compare the two runs" and keeps the run lattice intact (CH-042 option (b)).
  - ui §4.4: the Awaiting review row gets "Relaunch…". It records `stop` with reason `relaunched` (the run becomes `cancelled` with `cancel_reason = relaunched`), then calls `:relaunch` with mode `rerun_from` (the gated stage by default) and parameter overrides (SR-063).
  - dev-env §15.1: gate `apply` with parameter edits is "later".
  - Either way, align the meaning of "relaunch" in the api §7 `launches` row with api §5.
  - Boards: a GateSimple variant of ReviewReport with Summary only (check cards "1 failing · 1 warning", the MultiQC report link, the data age per ui §11), visible buttons rather than a tooltip menu ("Approve and continue" as primary, "Change parameters and rerun stage…" opening RelaunchDialog preset to the gated stage with the parameter editor of UX-243, "Stop run"), and an engine-neutral layout that works for Snakemake.
  - RunDetail frames: awaiting review (header primary "Review gate", gate card in Stages), and after the decision ("Approved by you · 10:42", "Continuing · restarting Nextflow with -resume" until the first event).
- **Absorbs:** UX-242 (the same contradiction seen from the boards; its evidence and board proposals are folded in above).
- **Related:** UX-243 (the dialog's parameter editor), SR-063 (`:relaunch` body), CH-042 (state machine), UX-109 (R12, which stages a change reruns).
- **Found by:** spec-reviewer as SR-062; ux-reviewer as UX-242
- **Status:** inbox, assumed: path B: relaunching at a failed gate or after a failure creates a child run through `POST /runs/{id}:relaunch`, the parent stays terminal; the 0.0.1 gate verbs are `approve` and `stop` — pending Thomas (TRIAGE2, 2026-10-27), inbox #32

### SR-055 · blocker · No local environment, runner record or in-process runner interface in 0.0.1

- **Where:** api-and-data-model.md §6 (Single-user mode), §5, §7; architecture-plugins-and-packaging.md §7.1, §7.3 (§7.7 is assigned but not written); ui-spec.md §4.6, §4.8; mvp-0.0.1.md §1. Boards: EnvLocal ("Runner as a user service" card with `systemctl --user status spectio-runner`, "Lingering", "outbound HTTPS only", x 290–656, y 688–925; header "Runner online · heartbeat 12 s ago"; Credentials tab; "Need these? Connect a SLURM or Kubernetes runner"); Launch and LaunchSnakemake Environment cards "demo-hpc SLURM · htc"; AppSidebar footer "Runners 3 / 4 online".
- **Evidence:**
  - "At first start Spectio creates: the instance, a user named after the OS account, a group `personal`, a project `default` owned by that group, and owner rights for the user." (api §6, l.165)
  - "`spectio init` # data dir, config, first user, project "default"" (architecture §7.3).
  - `runs` has `environment_id`; `runners` has "environment_id, principal_id, version, last_heartbeat_at, status" (api §7, l.233, l.237). The `POST /runs` example has `"environment_id"` (api §5).
  - "`spectio serve --with-runner` also starts a local runner in the same process, which is the default in personal mode." (architecture §7.1, l.331; the reviewer cited §7.2, corrected in this merge).
  - Inbox #12 (runner ↔ server transport, owner architecture §7.7) is "not needed for 0.0.1" (log 2026-10-27, l.352). The launch form aside lists "environment" (ui §4.6).
  - mvp §1 names EnvLocal as the board for "everything on one machine", one process with the local runner. The board shows a systemd runner service, a heartbeat and outbound HTTPS instead. Whether macOS, which has no systemd, is in 0.0.1 scope is **[to be validated]**.
- **Problem:** an implementer cannot tell:
  - whether init creates an `environments` row of kind `local`;
  - whether the in-process runner gets a `runners` row, and as which principal;
  - how the server gives it launch, Continue, cancel and gate-time evaluation work;
  - what the environment picker and the environment page show.

  Every launch needs this. The 0.0.1 environment page shows things that do not exist (a runner service, a heartbeat, credentials, a SLURM upsell).
- **Proposal:**
  - api §6: init also creates environment `local` (kind `local`, owned by `personal`). `serve --with-runner` registers a `runners` row bound to it, as the system principal. `POST /runs` defaults `environment_id` to the only environment.
  - architecture §7.1 (or a stub §7.7 "In-process runner, 0.0.1"): the in-process runner consumes the same `runner_commands` rows (CH-007, assumed), read in-process, so that #12 later replaces only the transport.
  - ui §4.6: hide the environment picker when only one environment exists; Launch preselects the local environment with a software profile valid on the host.
  - EnvLocal 0.0.1 variant: header "This machine · engines run here as local processes · part of `spectio serve`"; drop the service card, heartbeat, Credentials tab and SLURM upsell. The "Engines ready" list belongs to SR-067. The first-run Overview (UX-211) links here rather than to "Connect a runner".
- **Absorbs:** UX-247 (EnvLocal draws the separate runner, not the 0.0.1 single process; its engine-readiness half is linked from SR-067).
- **Related:** SR-067 (engine prerequisites), CH-041 (the sidebar footer during a restart).
- **Found by:** spec-reviewer as SR-055; ux-reviewer as UX-247
- **Status:** inbox, assumed: one built-in local environment and runner record, with an in-process runner interface, as the default `environment_id` — pending Thomas (TRIAGE2, 2026-10-27), inbox #35

### SR-057 · blocker · nf-core/rnaseq cannot be registered, get a stage and get a gate in 0.0.1 through any specified path

- **Where:** owner checking-scenarios.md §12.7 (overlays); api-and-data-model.md §5 (`POST /runs` `gates`, `/workflows/{id}/manifest`), §7 (`manifests`); ui-spec.md §4.7, §5.1; cli §2; mvp-0.0.1.md §2; dev-environment-and-testing.md §15.1. Boards: WorkflowImport (footer "Added to project Liver time course · visible to demo-lab"; "Path on a cluster · read through a runner" card, x 926–1310, y 776–1084); WorkflowOverlay ("Who decides · group demo-lab · AI agents propose only"); Launch Gates card "1 gate after stage 2 (spectio.yml) · Change", where Change goes to `#`.
- **Evidence:**
  - "nf-core/rnaseq declares none; the rnaseq stages in the mockups come from such an overlay"; detected stages are "display only, no gates" (ui §5.1, l.242).
  - `GET/PUT /workflows/{id}/manifest` is at workflow level (api §5), against "workflow_versions ||--o{ manifests" (api §7 ER).
  - The overlay editor is the workflow detail's "Stages & gates" tab (ui §4.7). It is not among the 0.0.1 features (mvp §2). The §15.1 rows are Launch, Monitor, Relaunch, Parameter history and QC gate (dev-env §15.1, l.468–498); none covers importing a workflow or writing an overlay.
  - `"gates": "from-manifest"` (api §5 example, l.122), with no other value defined; `run launch … --gates spectio.yml` (cli §2, l.49) passes a file the API cannot accept.
  - "Built-in presets for frequent pipelines can ship with Spectio as overlays: rnaseq | mapped %, rRNA %, strandedness" (checking §4, l.96). No file or version is given.
  - The boards that do this (WorkflowImport, WorkflowOverlay) assume projects, groups, cluster paths and AI agents, and neither is on the 0.0.1 map.
- **Problem:** journey 1 stops at "launch it with a QC gate after the first stage". An implementer cannot tell whether 0.0.1 ships an rnaseq preset, needs the overlay editor, or accepts a `spectio.yml` at launch, nor which workflow version an overlay attaches to. Implementers will either skip this or build the full multi-project import.
- **Proposal:**
  - checking §12.7: an overlay attaches to a workflow with a version range (`workflow.version`). Fix the api §7 ER (`manifests.workflow_id` + range).
  - api §5: `gates` ∈ `"from-manifest"` | `"none"` | `{"spectio_yml": "<inline YAML>"}`. `--gates FILE` sends the inline form. The run stores the resolved manifest and its checksum, so a relaunch reuses it.
  - dev-env §15.1 (owner of the 0.0.1 cut), mirrored in mvp §2: add "Register a workflow (nf-core, Git URL, local path) and declare stages and one gate". 0.0.1 ships one built-in rnaseq overlay (stage 1 = preprocessing and alignment, one gate), and overlays are edited as YAML only (question 3).
  - 0.0.1 board variants: WorkflowImport with "Path on this machine" and no project or visibility footer, plus empty, loading and "catalogue unreachable → Git URL or path" states; WorkflowOverlay read-only (or with stage `match` globs and one "Gate after this stage" switch), without "Who decides". Launch's Gates card opens the overlay's gate picker (UX-112).
- **Absorbs:** UX-241 (no 0.0.1 screen to register a workflow or attach an overlay; its board evidence and variants are folded in above).
- **Related:** SR-056 (the registration API contract), FC-002 (the generated `ext.when` must wrap rnaseq's own), UX-216 (gate label at launch), UX-112 (adding a gate at launch).
- **Found by:** spec-reviewer as SR-057; ux-reviewer as UX-241
- **Status:** inbox (TRIAGE2, 2026-10-27), inbox #34 (0.0.1 scope, reserved)

### CH-041 · blocker · In-process runner: the engine head's fate on server stop, re-adoption and exit code are unspecified

- **Where:** synthesis.md §5ter.6, §8; architecture-plugins-and-packaging.md §7.1, §7.2, §13.1; api-and-data-model.md §7 (`launches`, `runner_commands`), §7.1, §8; schedulers-and-monitoring.md §3.1; ui-spec.md §4.8, §11. Boards: AppSidebar footer "Runners 3 / 4 online · Server v0.4.0 · online" (every board); RunDetail header; RunsTable and RunsRows.
- **Evidence:**
  - "On server restart: reconciliation with the database, PIDs and `sacct`." (synthesis §5ter.6, l.281). This is the whole restart rule for 0.0.1. (ux-reviewer cited "synthesis §6"; corrected in this merge.)
  - `--with-runner` starts the local runner in the same process (architecture §7.1, l.331); the bundle is one process with api, worker and local runner (architecture §7.2).
  - `launches`: "run_id, n, head_native_id, head_state, started_at, exited_at, exit_code" (api §7, l.238). There is no PID start time, no host and no launch-directory path.
  - "Idempotent launch. Before `sbatch`, the runner looks for the head job's name in its `squeue --me` / `sacct` snapshot … and adopts the job" (schedulers §3.1, l.70). This is SLURM only.
  - Nextflow aborts the run on SIGTERM or SIGINT (`Session.groovy:609-615`, Nextflow `114f1fe`, cited at synthesis §5ter.3). Snakemake drains on SIGTERM (`job_scheduler.py:171, 241-245`, `1c67a66`, same section).
  - systemd's default `KillMode=control-group` kills every process of the unit (R4 CH-028, citing systemd.kill).
  - ui §11 specifies "Reconnecting… data as of …" and "Spectio is unreachable", and no board draws them (UX-205, pending). The Runner offline model cannot appear, because the UI itself is unreachable. api §7.1 has no state or flag for "head gone without a terminal event".
- **Problem:**
  - With the runner inside `spectio serve`, the engine head is the server's child. Restarting the server's systemd unit, or Ctrl-C in the terminal that started `spectio serve` (the foreground process group), signals the head too **[to be validated]**. Nextflow then aborts and Snakemake drains and exits. Either way the run fails, or "resumes" with lost work, without anyone asking.
  - If the head survives (for example after `kill -9` of the server alone), three things are undefined:
    1. **Finding the head.** There is no stored PID with a start time, so PID reuse can make the runner adopt an unrelated process.
    2. **Learning the exit code.** The restarted server is no longer the parent, so it cannot `waitpid`.
    3. **Head stdout.** If it is a pipe into the server, its next write after the server dies raises EPIPE or SIGPIPE **[to be validated per engine]**.
  - A `launch` command leased before the crash is delivered again (CH-007), and the local launcher has no equivalent of the `squeue` name match. Result: a second head in the same launch directory.
  - In the UI, a run may still be running, may have reached its gate, or may have died silently, and the screen shows "Running" until "head silent" fires after 5 minutes, then nothing actionable. The sidebar footer claims "online" from the server, which is down.
- **Proposal:**
  - Add a numbered subsection "Local launcher: detach, adopt, exit" under schedulers-and-monitoring.md §3.1 (owner), linked from synthesis §5ter.6 and architecture §7.1:
    - heads start in their own session (`setsid`, or `start_new_session=True`), outside the server's cgroup where systemd is used (`systemd-run --user --scope`, see CH-028);
    - stdin is `/dev/null`; stdout and stderr go to files in the launch directory (`.spectio/head.out`, `.spectio/head.err`), never to pipes;
    - a small wrapper (`spectio-head-wrap`) writes `.spectio/head.pid` with the PID, the process start time and the boot ID, then writes `.spectio/head.exit` when the head ends, so the exit code survives the server.
  - Adoption on boot: for every `launches` row whose `head_state` is not terminal, read `head.pid`, check that the PID, start time and boot ID match, and either adopt the process or read `head.exit`. The same check makes a re-delivered `launch` idempotent.
  - api §7 `launches`: add `launch_dir`, `pid`, `pid_start_time`, `host_boot_id`.
  - Decide what a server SIGTERM does to heads in personal mode: leave them running (recommended) or stop them (question 6). State it in mvp-0.0.1.md.
  - UI: a RunDetailReconnect board with three frames: during the outage ("Spectio is unreachable · last update 10:41:08 · retrying", actions disabled with their reason); after restart ("Catching up · 1,204 events from the spool", data age shown, resumes with `Last-Event-ID`; the banner itself belongs to CH-051); the outcome ("Kept running", "Reached the gate while Spectio was down → Awaiting review", or "Engine stopped while Spectio was down · Resume", see CH-046). Run lists show "Refreshing…" during snapshot-then-tail. The footer state comes from the client (Live / Reconnecting), not from the server.
- **Likelihood · impact:** high (every upgrade or restart of a personal install) · high (failed runs, duplicate heads, lost exit codes).
- **Cheapest test:** half a day with nf-toy and smk-toy and the spike's `run_scenarios.py` harness. With a prototype launcher, start a run, then send `kill -9` to the server, SIGTERM to the server, Ctrl-C in its terminal, and `systemctl --user restart`. Check that the head survives each case, that `head.exit` is written, and that a restarted stub adopts the head without starting a second one (spike 1).
- **Absorbs:** UX-246 (server restart with no screen during or after the outage, and no state for an engine lost while down).
- **Related:** CH-028 (R4, systemd and supervised heads, separate-runner case), CH-007 (durable runner commands), CH-046 (no terminal event), CH-051 (boot order and catching-up banner), UX-205 (R7, loading, error and stale states).
- **Found by:** constraints-hunter as CH-041; ux-reviewer as UX-246
- **Status:** inbox, assumed: on server stop the engine heads keep running detached and are re-adopted at the next start — pending Thomas (TRIAGE2, 2026-10-27), inbox #35

### CH-042 · blocker · Run state machine: `failed` is terminal yet "resumable", and launch outcomes are mapped onto the run state

- **Where:** owner api-and-data-model.md §7.1; api §5 (`:resume`, `:relaunch`), §7 (`runs.parent_run_id`, `launches`), §8.2; ui-spec.md §3.1, §4.4, §4.6; synthesis.md §5ter.2, §5ter.4; checking-scenarios.md §11.5.
- **Evidence:**
  - "`failed` | Failed | … | Engine or task failure; resumable" (ui §3.1, l.46). "Failed | Resume · Relaunch…" (ui §4.4, l.118).
  - api §7.1 lists no transition out of `succeeded`, `failed` or `cancelled`. "Projections never move a terminal state back" (api §8.2, l.338).
  - "`running` → `succeeded` / `failed`: the engine reports completion or failure (`spectio.run.completed` / `.failed`)" (api §7.1, l.270).
  - "At the end of a stage (last Snakemake `PROGRESS`, Nextflow `onFlowComplete` …) the platform: 1. collects the declared evidence … 2. creates the `Intervention`" (synthesis §5ter.4).
  - "'End of stage' means every process matching the stage's `match` globs has fired `onProcessTerminate`" (checking §11.5).
  - `launches` holds "one row per head process of a run (first launch, each Continue, resume or relaunch)" (api §7, l.238), while `runs` also has `parent_run_id` and `relaunch_mode`.
  - Resuming after a failure is the normal path: `tool_error_then_fixed_resume` passes on both engines ([spike note](../research/spike-synthetic-pipelines-2026-10-26.md), Results, l.40). A plain rerun in the same directory recovers a Snakemake engine fault (same note, finding 1).
- **Problem:**
  - **Launch completion read as run completion.** With `ext.when = false` or `--until`, the head ends normally and the bridge reports completion. Applied literally, §7.1 makes the run `succeeded`, a terminal state, so it can never reach `awaiting_review` or Continue. Spool replay after a restart (CH-044) can deliver that event before or after `spectio.gate.opened`. Also undefined: the state while gate checks are evaluated (minutes with MultiQC), an evaluation error, and a head failure inside the gated stage.
  - **Resume after a failure**, the main action of journey 3, has no defined semantics:
    - **same run:** a new `launches` row, `failed` → `running`. This breaks the lattice and the WES mapping, where `EXECUTOR_ERROR` is final;
    - **new run** linked by `parent_run_id`: the cache lives in the old run's launch directory, and history and counters split across two runs.
- **Proposal:**
  - api §7.1 (owner): engine completion events move `launches.head_state`. Only a server rule moves `runs.state`, and it uses the stage plan: last stage and success gives `succeeded`; a stage boundary keeps the run `running` (flag `evaluating_gate`) until the gate row is written, then `awaiting_review` (or the next launch, per SR-059); engine failure in any launch gives `failed`; an evaluation error opens the gate with verdict `error` (SR-058). `spectio.run.completed` is emitted only when the last planned launch completes. Add `until_stage` to `launches`. The lock wait is CH-003.
  - Pick one option and write it into §7.1 and §8.2 (question 1):
    - (a) `failed` is resumable: `failed` → `queued` when a resume or same-run relaunch is accepted, and the lattice applies per launch, not per run; or
    - (b) Resume always creates a child run that reuses the parent's launch directory (`runs.launch_dir`, CH-043), and the parent stays `failed`.
  - ui §3.1 and §4.4 then follow: either the "resumable" wording and the Resume action stay, or Resume becomes "Resume as new run". api §5 says which verb applies to `failed` (SR-063).
- **Likelihood · impact:** certain (journeys 1, 2 and 3) · high (the wrong state machine gets built; history splits or the lattice breaks).
- **Cheapest test:** a one-hour table test. Replay the spike's `tool_error_then_fixed_resume` and `gate_qc_then_resume` event logs through a 30-line projector stub, and check the final run state and the gate under both options (spike 2).
- **Absorbs:** SR-060 (the end of a gated launch has no defined mapping to run states; its proposal is folded into the first bullet).
- **Related:** SR-062, SR-063, CH-003 (R4, partly applied), CH-046.
- **Found by:** constraints-hunter as CH-042; spec-reviewer as SR-060
- **Status:** inbox, assumed: `failed` stays terminal; Resume and Relaunch create a child run (path B), and launch outcomes live on `launches`, not on the run state — pending Thomas (TRIAGE2, 2026-10-27), inbox #32

### SR-058 · blocker · At gate time after stage 1, `multiqc:` bindings find no MultiQC data, and 0.0.1 installs no MultiQC

- **Where:** owner checking-scenarios.md §7 (source bindings), §11.5; architecture-plugins-and-packaging.md §7.3; ui-spec.md §3.3, §11 (`n/a`). Boards: ReviewReport check cards (x 290–1416, y 282–430), e.g. "Uniquely mapped · min ≥ 85 % · block · `multiqc:star-uniquely_mapped_percent`"; Manifest `check:` with `evidence: multiqc/**`.
- **Evidence:**
  - "`multiqc:<module>.<column>`: read from MultiQC's data directory." (checking §7, l.205)
  - "MultiQC runs once, at the end of nf-core/rnaseq (in the 3.27.0 megatest, at minute 2,038 of 2,040)" (checking §11.6, l.379).
  - The example gate after `align` uses `from: "multiqc:star.uniquely_mapped_percent", min: 80, severity: block` (checking §7). Every check in the 0.0.1 rnaseq example uses a `multiqc:` binding.
  - The per-file meaning applies only "On a watched file" (checking §11.2), and live checks are "later" (dev-env §15.1, l.484).
  - "Check providers run in a separate check runtime … not the runner's base install" (checking §11.5, l.372); "`[checks]` (heavy check bindings: MultiQC for `multiqc:` bindings …)" while the install line is `"spectio[server]"` (architecture §7.3, l.358, l.366).
  - `error` exists among the verdicts (checking §11.4, l.363), but nothing maps a missing value to it. No board draws a check card in the `n/a` state; R12 UX-103 defines the state but no board.
- **Problem:** the generated `ext.when = false` skips MULTIQC, so `multiqc_data/` does not exist at the gate and the block check has no value. Even if it existed, the default install has no MultiQC. The verdict for a missing value is not stated, so the gate's outcome is undefined, and the UI cannot say whether a gate with `n/a` checks is approvable or whether `n/a` counts as a fail.
- **Proposal:**
  - checking §7: at gate time, a `multiqc:` binding runs MultiQC itself, limited to the named module (MultiQC's module filter option **[to be validated]**). It reads the stage's task outputs within the run roots (§11.1) and writes to a Spectio directory under the launch directory, with the column names of UX-101.
  - A missing value gets verdict `error`, which blocks auto-approval.
  - architecture §7.3: the 0.0.1 install is `spectio[server,checks]`; the separate check runtime of §11.5 is "later" (question 4).
  - Draw an `n/a` check card: icon plus "n/a", the reason ("MultiQC reader not installed · `uv tool install "spectio[server,checks]"`" or "file not found"), and its effect on "Approve and continue" (disabled reason, or "approve with n/a acknowledged").
  - Test: the rnaseq test profile gated after alignment yields a `star` value (spike 3).
- **Absorbs:** UX-251 (with the default install the checks have no reader, and the `n/a` state is not drawn).
- **Related:** UX-101 (R12, MultiQC column names), UX-103 (R12, `n/a` check state), CH-016 and CH-017 (R4, gate stop on real nf-core pipelines; MultiQC cost).
- **Found by:** spec-reviewer as SR-058; ux-reviewer as UX-251
- **Status:** inbox (TRIAGE2, 2026-10-27), inbox #34 (0.0.1 scope, reserved)

### SR-054 · blocker · 0.0.1 needs the ingest contract, but the log parks it as "not needed for 0.0.1"

- **Where:** api-and-data-model.md §14 (cited, does not exist; the file ends at §13.6); decisions/log.md 2026-10-27; inbox #11; architecture-plugins-and-packaging.md §13.2; synthesis.md §2bis, §5ter.6. Owner finding: SR-001 (R1, inbox).
- **Evidence:**
  - "Inbox #11, #12, #14 and #15 are not needed for 0.0.1 and stay open for later versions." (log 2026-10-27, "Stays open", l.352)
  - "api §14 (the engine → server ingest contract: envelope, run handshake, driven-run variables, batching, logs) cannot be written until we know how a run started in a terminal gets a credential" … "Blocked: APPLY1 for api §14 … the walking skeleton" (inbox #11, l.118).
  - The 0.0.1 rows "Snakemake, through the Spectio logger plugin" and "Nextflow, through `nf-spectio`" (mvp §2); "`nf-spectio` and the Snakemake logger both post to `/api/v1/ingest/events`" (synthesis §2bis, l.70).
  - "the wire format and the testable bounds belong to the ingest contract (api §14)" (architecture §13, l.514); "(the bound the ingest contract sets, api §14)" (architecture §13.2, l.531).
  - "with the Spectio run ID passed to `nf-spectio` by us" (synthesis §5ter.6). No mechanism is named.
- **Problem:** 0.0.1 can skip only the credential for observed runs: loopback is trusted in `single` mode (api §6), and observed runs are deferred (dev-env §15.1). The first nf-spectio and logger builds still need the envelope, how a driven run learns its run ID and launch number, the ingest response and ack, the ingest version header (CH-002) and batching. Because #11 is parked, nobody owns these now.
- **Proposal:** split inbox #11 (question 6).
  - Write api §14 now with the driven-run subset:
    - the envelope is the api §8 CloudEvents envelope plus `spectiosequence` and a source sequence;
    - the runner sets environment variables with the server URL, run ID and launch number (names fixed in §14);
    - the ack body;
    - the ingest version header;
    - no credential on loopback in `single` mode (api §6).
  - Keep the observed-run credential under #11.
  - Amend the 2026-10-27 log line.
- **Related:** SR-001 (R1, owner of api §14), CH-002 (R4, ingest version header), CH-044 (spool cursor numbers that §14 will own).
- **Found by:** spec-reviewer
- **Status:** inbox (TRIAGE2, 2026-10-27), inbox #36 (ingest credential and the split of inbox #11, reserved)

---

## Majors

### SR-061 · major · Failures before the engine starts have no state transition, reason or screen

- **Where:** owner api-and-data-model.md §7.1, §7 (`failure_class`); architecture §13.4; ui-spec.md §4.4, §4.6, §5.1, §11. Boards: Launch and LaunchSnakemake aside buttons (x 1096–1416, y 580–625 and y 833–878); RunDetail (only a Running frame).
- **Evidence:**
  - From `queued`, api §7.1 has only "→ `running`" and "→ `cancelling`".
  - "the runner checks the Nextflow version before launch and refuses below the floor with a clear message" (architecture §13.4, l.548).
  - "the launch form shows 'gates unavailable'" (ui §5.1); file checks "run again automatically before launch" (ui §4.6).
  - `failure_class` exists only "on `attempts` and `scheduler_jobs`" (api §7, l.256), yet the WES row for `failed` uses a failure class (api §7.1).
  - No board shows a pending POST, a 422 schema error as a problem toast (ui §11), or the navigation to the new run. The first minutes of a laptop run are spent downloading the nf-spectio plugin, pulling containers or creating conda environments, which would show as a bare "Queued".
- **Problem:** on a laptop the likely failures happen before launch: Java or `nextflow` missing, or Nextflow below 25.04; Snakemake below 9, or the logger plugin missing; the workflow fetch fails or the environment cannot be built; a file check fails at submit; nf-schema validation fails. None of them has a way out of `queued`, an event or a UI message, and a run that dies before any task has no task and no failure class.
- **Proposal:**
  - api §7.1: `queued` → `failed`, triggered when the runner reports that the launch could not start, with `runs.failure = {class, message}` (the same column as CH-047).
  - Add `launch_error`, `engine_missing`, `engine_version` and `input_check` to the class enum (WES `SYSTEM_ERROR`).
  - `POST /runs` returns 422 for synchronous validation failures (file checks, gates unavailable) and creates no run.
  - ui §4.4: the Failed header shows the message.
  - Boards: Launch button states ("Launching…", then an error toast with the request ID); a RunDetail "Starting" frame (elapsed timer, tail of the engine's startup output such as the plugin download, Cancel); a RunDetail "Engine did not start" frame (Failed, no tasks, head log, "Fix and relaunch").
- **Absorbs:** UX-248 (no submitting, starting or "engine did not start" state).
- **Related:** SR-067 (prerequisites), CH-047 (`runs.failure`).
- **Found by:** spec-reviewer as SR-061; ux-reviewer as UX-248
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### CH-047 · major · "Why did it fail": no run-level failure cause, no pointer to the failing task, and no local failure classes

- **Where:** owner api-and-data-model.md §7 (`runs`, `tasks`, `attempts`); ui-spec.md §3.1, §4.4 (header, Summary, Tasks), §10.2 (failure-class card); api §5 (`GET /runs/{id}`, `/tasks`); synthesis.md §2ter; schedulers-and-monitoring.md §3.5; mvp-0.0.1.md §2. Boards: RunFailed ("Why it failed · Classified from sacct state, exit code and the job log", x 290–1035, y 380–405; evidence grids `sacct -j 48731209`; "Relaunch with 2 suggested changes", x 1076–1348, y 140–176).
- **Evidence:**
  - ui §4.4's Tasks tab filters by state only, and the header shows "Failed | Resume · Relaunch…".
  - Task states include "retried, failed, failed (ignored)" (ui §3.1).
  - A Nextflow retry gives a new taskId and a new work directory. Snakemake does not send the attempt number and re-emits the same jobid (synthesis §2bis and §2ter).
  - `runs` has no failure-cause column. `failure_class` is stored per attempt and scheduler job (api §7, l.256).
  - "Failure classes come from the `sacct` state, exit code and reason, or from the Kubernetes container state and events" (schedulers §3.5, l.127). A local executor has neither. The local exit codes that do exist are in the same section: "an OOM kill gives 137 locally" (l.145).
  - mvp §2 maps only RunDetail for monitoring and RelaunchDialog for relaunch. RunFailed, the only failed-run board, is not listed.
- **Problem:**
  - In journey 3 the researcher must open the task that failed the run. Several things hide it: with retries, earlier attempts show as failed although the task later succeeded; with Nextflow `errorStrategy 'finish'` or `'ignore'`, and Snakemake `--keep-going`, many failures can appear while the run fails for one of them, or for none (an engine error) **[to be validated per engine]**; Nextflow's new taskId per retry means grouping attempts of one logical task needs a key (process plus tag plus hash?) that is not defined. Nothing tells the UI which task to show first.
  - On a local run nothing defines which class a task failure gets: `tool_error`, or an out-of-memory kill seen only as exit 137 **[to be validated per engine]**. RunFailed's memory suggestion has no data behind it. Implementers either port the SLURM card or show nothing.
- **Proposal:**
  - api §7 (owner): add `runs.failure {class, task_id, attempt_n, message}`, set by the projector from the engine's terminal error (`onFlowError` payload; Snakemake `ERROR` or `JOB_ERROR` **[to be validated]**).
  - Define the logical-task key per engine in synthesis §2ter (shared with CH-050).
  - schedulers §3.5 gets local rules: a non-zero exit code is `tool_error`; a SIGKILL or exit 137 is "killed (memory?)", only where the engine reports it **[to be validated]**; otherwise the class is unknown and the UI says "n/a · no scheduler accounting on a local run".
  - ui §4.4: the Failed header links to the failing task, and the Tasks filter defaults to "failed, final attempt".
  - A RunFailed local variant (failure card with exit code, stderr tail and "Open task log", see CH-048; suggestions only when the evidence exists), added to mvp §2.
- **Likelihood · impact:** certain (journey 3) · medium (support load, wrong task inspected).
- **Cheapest test:** one hour. Replay the spike's `oom_fatal`, `flaky_retry` and `timeout_fatal` event streams (both engines) through the stub projector and check that the selected failing task is the one in the engine log (spike 5).
- **Absorbs:** UX-245 (a failed run's explanation depends on `sacct`, and RunFailed is off the 0.0.1 map).
- **Related:** SR-061 (failures before any task), CH-048, CH-050, UX-113 (R12, suggested resource changes).
- **Found by:** constraints-hunter as CH-047; ux-reviewer as UX-245
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### SR-056 · major · Registering a workflow is outside the 0.0.1 cut, and its contract is undefined

- **Where:** dev-environment-and-testing.md §15.1; mvp-0.0.1.md §2; api-and-data-model.md §4, §5, §7; ui-spec.md §4.7; cli §2.
- **Evidence:**
  - mvp §2 and dev-env §15.1 list Snakemake, Nextflow, launch, monitoring, relaunch, parameter history and the gate. Neither has a registration row.
  - "`GET/POST /workflows` … `POST /workflows:import` (git, nf-core, Snakemake catalog, RO-Crate)" (api §5, l.85).
  - "Long operations (catalogue import, …) return `202 Accepted` with an `Operation` resource (`/operations/{id}`)" (api §4, l.68). `/operations` is not in the §5 table.
  - "import falls back to a Git URL or a path" (ui §4.7, l.169); the key "local `local/<directory name>/<short content hash>`" (api §7); `workflow import nf-core/rnaseq --versions 3.27.0` (cli §2).
  - UX-123 (inbox) asks "whether the server or a runner clones".
  - The WorkflowImport board exists but is not on the 0.0.1 map (UX-241, now in SR-057).
- **Problem:** both journeys start here, yet these are undefined: `POST /workflows` against `:import`; the import body for each source; who fetches the code and the schema, where it is cached, and when `params_schema` and the author's `spectio.yml` are read; the Operation result (workflow and version IDs) and its failure states; whether an edited local path makes a new version.
- **Proposal:**
  - dev-env §15.1: add "Register a workflow (nf-core by name, Git URL, local path)" to 0.0.1 (shared with SR-057).
  - api §5: define the `:import` body for each source; define the Operation result as `{workflow_id, workflow_version_ids[], errors[]}`; add `GET /operations/{id}`.
  - State that in 0.0.1 the in-process runner fetches into the data directory and extracts `params_schema` and `spectio.yml`.
  - Re-hash local paths at launch; a changed hash creates a new `local/…` version.
  - UX-123 keeps the multi-runner question.
- **Related:** SR-057 (screens and the overlay), UX-123 (inbox).
- **Found by:** spec-reviewer
- **Status:** inbox (TRIAGE2, 2026-10-27), inbox #34 (0.0.1 scope, reserved)

### CH-043 · major · Resume inputs are not stored: launch directory, engine session ID, engine version, Snakemake unlock and rerun flags

- **Where:** owner synthesis.md §5ter.5 (resume rules) and api-and-data-model.md §7 (`runs`, `launches`); api §5 (example); architecture §7.2; checking-scenarios.md §11.1; ui-spec.md §4.6.
- **Evidence:**
  - "Continue | … | same launch directory, `-resume <sessionId>`" (synthesis §5ter.5 table, l.268).
  - "Snakemake: explicit `rerun_triggers`; `unlock` + `rerun_incomplete` after an abrupt stop." "Nextflow: … same version across stages" (synthesis §5ter.5, l.275–276).
  - Neither `runs` nor `launches` has a session ID, a launch directory, a work or results directory, or an engine version (api §7, l.237–238). Only `bridge_versions` exists, and it records the bridges.
  - Run roots are "the launch directory, the engine work directory, the results directory" (checking §11.1).
  - `"outdir": "spectio://results"` (api §5). The scheme is not defined in any spec.
  - Nextflow upgrades break the cache (synthesis §2, l.24, citing `docs/migrations/26-04.mdx:405-409`; FC-020).
  - nf-spectio receives the `sessionId` in `onFlowCreate` (synthesis §2bis, l.39).
- **Problem:**
  - **Directories.** Without stored paths the runner has no default location, check globs have no root, and SR-063's directory reuse has nothing to point at.
  - **Session ID.** `-resume` with no session ID uses the last session recorded in the launch directory's history **[to be validated]**, which may be a different launch (a manual run in the same directory, or a dry run). Spectio does not store the `sessionId`.
  - **Version drift.** Without a pinned `NXF_VER` per run, a Nextflow upgrade between the failure and the Resume silently recomputes everything.
  - **Snakemake.** After a failure or an abrupt stop, the lock under `.snakemake/locks` and the incomplete markers decide whether the rerun starts at all **[to be validated]**. Nothing says whether the runner adds `--unlock` (only safe once no head is alive) or `--rerun-incomplete` by itself. A relaunch with changed parameters reruns jobs depending on `rerun_triggers`, which affects the ui §4.6 estimate.
- **Proposal:**
  - api §7: add `runs.launch_dir`, `runs.work_dir`, `runs.results_dir`, `runs.engine_version` (pinned at the first launch), and `launches.engine_session_id`, filled from `onFlowCreate` and, for Snakemake, from the run UUID if it has one **[to be validated]**.
  - architecture §7.2: default layout `<data-dir>/runs/<run id>/{launch,work,results}`.
  - api §5: `spectio://results` resolves to `results_dir` (or is removed from the example).
  - synthesis §5ter.5 (owner) gets a "Resume after failure" row per engine:
    - Nextflow: `-resume <stored sessionId>`, `NXF_VER` = the stored version, and Resume is refused with a reason if that version is unavailable;
    - Snakemake: `--unlock`, but only after CH-003's "head gone" check, then `--rerun-incomplete` with the run's `rerun_triggers`.
- **Likelihood · impact:** medium (stray sessions, upgrades) · high (a silent full recompute, or a rerun refused because of a lock).
- **Cheapest test:** two hours with nf-toy and smk-toy (spike 2). Nextflow: run once, run a second time with different parameters in the same directory, then `-resume` without an ID and count the cached tasks. Snakemake: `kill -9` the head mid-run, then rerun with and without `--unlock` and `--rerun-incomplete`.
- **Absorbs:** SR-068 (run directories, the engine session ID and `spectio://results` are undefined for local runs).
- **Related:** CH-041 (`launches.launch_dir`, the same column seen from adoption), SR-063, FC-020 (R2).
- **Found by:** constraints-hunter as CH-043; spec-reviewer as SR-068
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### SR-063 · major · The `POST /runs/{id}:relaunch` contract is undefined

- **Where:** owner api-and-data-model.md §5, §7 (`runs.relaunch_mode`); ui-spec.md §4.4, §4.6; cli §2.
- **Evidence:**
  - "`POST /runs/{id}:relaunch` (mode, from stage, param overrides)" (api §5, l.88), and `relaunch_mode` with no enum (api §7).
  - "Resume / Rerun from a stage / Start fresh"; "**Start fresh** | New work directory, nothing reused" (ui §4.6, l.165).
  - `relaunch (--resume, --from-stage N, --samplesheet v2.csv, --params)` (cli §2, l.49). There is no fresh option.
  - The Failed row offers "Resume · Relaunch…" (ui §4.4), and `:resume` is a separate verb (api §5).
  - `runs` and `launches` store no launch directory and no engine session ID (api §7; see CH-043).
- **Problem:** undefined: whether relaunch creates a new run or a new launch of the same run; the mode values; whether the new run reuses the parent's directory, which Nextflow `-resume <sessionId>` and Snakemake `.snakemake` need, and how that fits the per-directory mutex (synthesis §5ter.6, l.280); whether the overrides merge with or replace the parent's parameters; whether gates and the manifest carry over; how Resume on a Failed run differs from Relaunch → Resume.
- **Proposal:**
  - api §5 and §7: `relaunch_mode` ∈ {`resume`, `rerun_from`, `fresh`}; body `{mode, from_stage?, params_patch (JSON Merge Patch over the parent's non-default params), gates: inherit|none|inline}`; always a new run with `parent_run_id` (consistent with CH-042 option (b)).
  - `resume` and `rerun_from` reuse the parent's `launch_dir` and `engine_session_id` (CH-043), with a 409 while the parent's head is alive. `fresh` gets a new directory.
  - `:resume` applies only to paused runs.
  - Add `--fresh` to cli §2, and drop "relaunch" from the `launches` comment.
- **Related:** CH-042, SR-062, UX-113 (R12), CH-003 (R4).
- **Found by:** spec-reviewer
- **Status:** inbox, assumed: the `:relaunch` contract follows path B (child run, parent terminal) — pending Thomas (TRIAGE2, 2026-10-27), inbox #32

### SR-064 · major · Parameter history: stored vs resolved values, Snakemake config, response shape

- **Where:** owner api-and-data-model.md §5 (`/params`, `/lineage`), §7 (`run_inputs`); ui-spec.md §4.4, §8; cli §2.
- **Evidence:**
  - "`run_inputs` | run_id, version, kind (params, samplesheet), content (JSON), checksum" (api §7, l.239).
  - "only non-default values stored" (ui §8, l.303) against "**Parameters** — resolved params, diff against the previous run of the lineage" (ui §4.4, l.131).
  - `GET /runs/{id}/params` and `GET /runs/{id}/lineage` have no response shape (api §5).
  - "new config (`--configfile` / `--config`)" (synthesis §5ter.5).
  - The CLI "covers the whole API" (cli, l.12), but `run` has no parameters or compare command (cli §2).
- **Problem:** resolved values need defaults that are not stored: schema defaults, Snakemake `config.yaml`, and params set by profiles. For Snakemake, what `kind = params` holds is undefined. When a gate adds a version, which version is "the run's parameters" is undefined. "Previous run of the lineage" is ambiguous when a run has several children.
- **Proposal:**
  - api §7: store the submitted non-default values (`kind = params`) and the resolved values reported by the bridge (`kind = params_resolved`). The sources are `session.params` for nf-spectio and the workflow config for the logger, both **[to be validated]** in spike T2.
  - api §5: `GET /runs/{id}/params?version=&resolved=` returns `{version, values, changed_vs_parent: [{key, before, after}]}`. The baseline is `parent_run_id`.
  - Compare endpoint per UX-114.
  - cli §2: `run params <id> [--diff <other>]`.
- **Related:** UX-114 (R12, accepted, compare endpoint), UX-249, UX-250.
- **Found by:** spec-reviewer
- **Status:** accepted (TRIAGE2, 2026-10-27)

### SR-067 · major · Engine prerequisites on a laptop: who provides Java and Nextflow, the Snakemake environment and the bridges

- **Where:** owner architecture-plugins-and-packaging.md §7.3 (with §13.4); synthesis.md §5ter.6; api §7; ui-spec.md §4.8. Board: EnvLocal "Engines and software" card (x 670–1036, y 688–925).
- **Evidence:**
  - The install is `spectio[server]` + `init` + `serve`. `spectio doctor` checks "the SQLite version and local disk, … plugin compatibility, runner reachability, proxy variables …", and no engine (architecture §7.3, l.382).
  - "the `snakemake` command line in the workflow's own environment" (synthesis §5ter.6).
  - "`pip install` of the plugin fails, so the runner puts the logger plugin on `PYTHONPATH`" (architecture §13.4). This covers read-only environments only.
  - No field in api §7 names a run's Snakemake environment.
  - EnvLocal's engines card lists Nextflow, Java and Snakemake, but not nf-spectio or the Snakemake logger plugin, which every 0.0.1 run needs, and it has no "not installed" state.
- **Problem:** journey 1 needs Java (minimum version **[to be validated]**), Nextflow ≥ 25.04 and the nf-spectio plugin; where the plugin comes from (plugin registry or a bundled jar) is not stated. Journey 2 needs Snakemake ≥ 9 with the logger plugin. Nothing says what is detected, installed or reported, or where the user picks the Snakemake environment. The environment page hides what fails first on a laptop.
- **Proposal:** architecture §7.3 gets a "0.0.1 prerequisites" list:
  - Java and `nextflow` on PATH, checked as in SR-061;
  - Snakemake ≥ 9 on PATH, or a conda or pixi environment named in `spectio.yml` `launch`;
  - the runner always injects the logger plugin via `PYTHONPATH` from the spectio wheel, one mechanism instead of two;
  - nf-spectio delivery is Thomas's choice: registry, or a jar in the wheel through the plugins directory **[to be validated]** (question 5);
  - `spectio doctor` reports engine and bridge versions.
  - EnvLocal 0.0.1 variant: an "Engines ready" list with Nextflow + Java, nf-spectio, Snakemake and the logger plugin, each with icon, word, version and a fix command when missing (like `spectio doctor`).
- **Related:** SR-055 (absorbs UX-247, the rest of the EnvLocal variant), SR-061, CH-009 (R4, partly applied), CH-001 (R4, assumed).
- **Found by:** spec-reviewer; ux-reviewer (engines card, as part of UX-247)
- **Status:** inbox (TRIAGE2, 2026-10-27), inbox #35 (who provides the engines and how nf-spectio ships, reserved)

### CH-044 · major · The spool forward cursor, replay order and drop policy after a restart are unspecified

- **Where:** owner architecture-plugins-and-packaging.md §13.1, §13.2; api-and-data-model.md §8.2; synthesis.md §8.
- **Evidence:**
  - "The runner tails the spool from the login node and forwards what the server has not acknowledged" (architecture §13.1).
  - The spool "keeps at least 24 h or 200 MB of events, whichever comes first (the bound the ingest contract sets, api §14); beyond it the oldest non-terminal events are dropped first, terminal events never" (architecture §13.2). The reviewer's paraphrase was replaced by the text in this merge.
  - The ingest contract (api §14) is missing (SR-001, SR-054, inbox #11).
- **Problem:**
  - In 0.0.1 the runner is the server. During the downtime nothing forwards, and the bridge's direct posts fail.
  - After the restart the runner must know where each spool file stops being acknowledged, but no cursor is defined: no offset per file, no rule for rotation during the downtime, no rule for direct posts the server stored but the runner never saw acknowledged.
  - Without a cursor the runner either re-sends whole files, which is idempotent through `unique (run_id, event_id)` but is the 100 000-event burst of CH-012 and CH-033, or skips events.
  - Dropping "oldest non-terminal" events during a long downtime can drop the only event for a task that then dies with the head, and that task becomes invisible.
  - Who owns the cursor on the server side (`events.source_seq` per producer?) is not stated.
- **Proposal:**
  - architecture §13.1 (owner of the mechanism): the forwarder keeps `.spectio/events/.cursor` with (file, byte offset, last `source_seq`); on boot it asks the server for the highest stored `source_seq` per (run, producer) and forwards from there; rotation never deletes a file beyond the cursor.
  - api §14, when written, owns the numbers: batch size, replay rate cap, drop counters.
- **Likelihood · impact:** high (every restart with a live run) · medium to high (missing or duplicated work, replay bursts).
- **Cheapest test:** R9 spike 3, extended (spike 4 here). Stop `spectio serve` for 2 and 30 minutes during a 500-job smk-toy run, restart it, and compare the per-task states with `.snakemake` and the Nextflow `execution_trace.txt` (the source the spike note's finding 3 uses).
- **Related:** SR-001 (R1), SR-054, CH-012, CH-033 (R4).
- **Found by:** constraints-hunter
- **Status:** accepted (TRIAGE2, 2026-10-27)

### CH-046 · major · A head that ends with no terminal event leaves the run and its tasks `running` forever on the local launcher

- **Where:** owner api-and-data-model.md §7.1 (and its flags item), §8.2; schedulers-and-monitoring.md §1 ("Head process"), §3.1, §3.5; ui-spec.md §3.1, §11.
- **Evidence:**
  - "`running` → `succeeded` / `failed`: the engine reports completion or failure" (api §7.1, l.270). No other path to a terminal state exists, except `cancelling` → `cancelled`.
  - "**Head process** | neither engine watches its own head job | Spectio's launcher does (§3.1)" (schedulers §1, l.46). §3.1 only describes SLURM head jobs.
  - "an OOM-killed head ends without `onFlowComplete`" (schedulers §3.1, l.64), and the scheduler-side failure-class row "Head out of memory | `oom` | head job `OUT_OF_MEMORY` | head pod `OOMKilled`" (schedulers §3.5, l.140). Neither says what the run's state becomes when no terminal event arrives.
  - ui §11 has "Head silent" as a flag, with no outcome (l.382).
- **Problem:**
  - Killed with the server (CH-041), OOM-killed, `kill -9`, or a crash in the JVM or Python: the head leaves no `spectio.run.failed`.
  - The run never leaves `running`, and its in-flight tasks never leave `running`. The lattice also forbids `running` → `queued`, so the run can never be resumed (CH-042).
  - `head_silent` is a flag, not an outcome, and no timeout turns it into a state.
  - A task process orphaned by a dead Nextflow head on the local executor may keep running **[to be validated]**.
- **Proposal:**
  - api §7.1 (owner) adds the trigger "the runner reports the head exited (`launches.exited_at` set) and no engine terminal event arrived within N s after the replay" → `failed` with `failure_class = engine_fault` or `head_lost`. In-flight tasks of that launch are marked `failed (head lost)` as attempts, not as engine success.
  - schedulers §3.1 adds the local-launcher counterpart of the head-job watch, using CH-041's `head.exit`.
  - The UI copy for this case goes in ui §3.1 ("Engine stopped while Spectio was down · Resume", see CH-041).
- **Likelihood · impact:** high (OOM and kills happen) · high (stuck runs, no resume).
- **Cheapest test:** 30 minutes. Run nf-toy and smk-toy, `kill -9` the head mid-run, and check the projected run and task states with the stub projector (part of spike 1).
- **Related:** CH-041, CH-042.
- **Found by:** constraints-hunter
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### CH-048 · major · Task and run logs on the local executor: sources unspecified, Tasks and Logs tabs never drawn

- **Where:** owner architecture-plugins-and-packaging.md §13.5 (payload content); ui-spec.md §4.4 (Tasks and Logs tabs), §11; api-and-data-model.md §5 (`/tasks/{id}/logs/…`, `/runs/{id}/logs`); architecture §13.2; mvp-0.0.1.md §2. Boards: RunDetail tabs (y 285–318) and RunFailed tabs (y 245–275), where Tasks and Logs link to `#` (RunFailed.dc.html:181); RunFailed "LOG TAIL" blocks (x 308–708, y 607–700 and y 918–1000).
- **Evidence:**
  - "Logs — run log and per-task stdout/stderr (fetched on demand through the runner)." (ui §4.4)
  - "the runner reads `.command.sh` on demand" (architecture §13.5, l.551).
  - "The full trace record goes only with terminal events" (architecture §13.2), and deltas otherwise.
  - The API serves `GET /runs/{id}/tasks`, `/tasks/{id}/attempts` and `/tasks/{id}/logs/{stdout|stderr}` with range requests (api §5).
  - No board renders either tab. RunFailed's tails are SLURM job logs (`slurmstepd: error…`).
- **Problem:**
  - **Nextflow.** The runner needs the task work directory, then `.command.out`, `.command.err` and `.command.log` **[to be validated]**. If `workdir` only travels in the terminal record, a running or lost task (CH-046) has no known path.
  - **Snakemake.** On the local executor, job output goes to the main Snakemake process unless the rule has a `log:` directive **[to be validated]**. There is then no per-job stdout file, only the interleaved head output and the run log under `.snakemake/log/` **[to be validated]**.
  - **Run log.** Its source (`.nextflow.log`, the Snakemake log, or the head's own stdout and stderr) is not specified. Neither is head output capture to a file, which CH-041 needs anyway.
  - **Delivery.** "Through the runner" has no defined path when the runner is in-process. Large logs need range reads, with an encoding and size cap.
  - **Screens.** Journey 3 cannot be completed. Undesigned: a failed filter as the default on a failed run, attempts per task, logs of several MB (range paging), "log not available" (work directory cleaned, or Snakemake jobs without `log:`), loading and error.
- **Proposal:**
  - ui §4.4 links to a new table in architecture §13.5 (owner) giving, per engine: the task log source (Nextflow work directory files, Snakemake `log:` files, or "no per-task log, see the run log at line N"); the run log source; the head stdout and stderr capture (`.spectio/head.out`, see CH-041). Each path is marked **[to be validated]** until T1 confirms it.
  - `workdir` goes in the first task delta (submit or start), not only in terminal events.
  - **RunTasks** board: state chips "Failed 1 · Retried 2 · Cached 288"; a failing-task row opens a side panel with attempts, exit code, command, work directory and the stderr tail.
  - **RunLogs** board: run log plus per-task stdout and stderr; follow mode; range paging; search within the loaded part; download; "not available" and "on hold" states as in ui §11.
  - Add both boards to the mvp §2 monitoring row.
- **Likelihood · impact:** certain (journey 3) · medium (an empty Logs tab for Snakemake rules without `log:`).
- **Cheapest test:** one hour. Run the spike's `tool_error_then_fixed_resume` on both engines and list which files hold the failing command's stderr, and whether the logger event carries their paths (spike 5).
- **Absorbs:** UX-244 (the Tasks and Logs tabs are never drawn).
- **Related:** CH-041, CH-047.
- **Found by:** constraints-hunter as CH-048; ux-reviewer as UX-244
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### CH-049 · major · An open gate across a restart: expired timeouts, interrupted check evaluation, stuck background tasks

- **Where:** owner api-and-data-model.md §7.1 (gate states), §8.2 (clocks); architecture-plugins-and-packaging.md §7.6; admin-and-operations.md §3.1; checking-scenarios.md §7.
- **Evidence:**
  - "`open` → `expired` (the policy timeout passes and `on_timeout` applies)" (api §7.1, l.275).
  - "gate timeouts always use server receive time" (api §8.2, l.340).
  - `background_tasks(… attempts, max_attempts, run_after, idempotency_key, … worker_id, started_at, finished_at, created_at)` has no lease or heartbeat column (architecture §7.6, l.431; admin §3.1, l.121).
  - "`check.dispatch` sends the evaluation of a check's source binding to the runner … and waits for `spectio.check.evaluated`" (admin §3.1, l.140).
- **Problem:**
  - **Timeout.** A gate whose timeout passed while the server was down fires `on_timeout` (for example `stop`) right at boot, before a human can see it. Or it never fires, if the timer lived only in memory. Neither is stated.
  - **Check evaluation.** A `check.dispatch` row left `running` by the crash has no lease to expire. The gate never gets its verdict, and the run stays `awaiting_review` with an empty report. The in-process runner's evaluation died with the server, so `spectio.check.evaluated` never arrives. A re-run evaluation must be idempotent (CH-045's deterministic keys).
  - **Decision.** A decision taken just after boot must wait for CH-041's adoption to finish before `CONTINUE_REQUESTED` (synthesis §5ter.2, l.247) can conclude that "the head is gone".
- **Proposal:**
  - api §7.1 (owner of gate states): timeouts are persisted (`gates.timeout_at`) and evaluated by a sweep. A gate whose `timeout_at` passed while the server was down gets a grace period, the same idea as admin §3.2's three heartbeat intervals after boot, before `on_timeout` applies, and the decision log records "applied after restart".
  - architecture §7.6 (owner of claiming): `background_tasks.lease_until`; on boot, `running` rows of this worker go back to `queued` with `attempts + 1`.
- **Likelihood · impact:** medium · high (an unattended `stop`, or a gate stuck without a verdict).
- **Cheapest test:** one hour with a stub (spike 6). Open a gate with `timeout: 2m`, stop the server for 5 minutes, restart, and observe. Then kill the server during a check evaluation and check that the verdict arrives.
- **Related:** CH-041, CH-045, CH-014 (R4, gate timeout races).
- **Found by:** constraints-hunter
- **Status:** accepted (TRIAGE2, 2026-10-27)

### CH-050 · major · Task identity across launches of one run: cached tasks reported by Nextflow and silent in Snakemake

- **Where:** owner api-and-data-model.md §7 (`tasks`, `attempts`), §8.2 (lattice); synthesis.md §2, §2ter; ui-spec.md §3.1, §3.2, §4.6.
- **Evidence:**
  - `tasks`: "run_id, process_or_rule, stage, tag"; `attempts`: "task_id, n, state, exit, resources" (api §7, l.240). There is no launch column.
  - nf-spectio hooks include `onTaskCached` (synthesis §2, "verified").
  - "a retry creates a new attempt" (api §8.2, l.338).
  - Task states include `cached` (ui §3.1).
- **Problem:**
  - On Resume (journey 3) or Continue, Nextflow re-reports every completed task as cached, possibly with new task IDs **[to be validated]**. If each becomes a new task row, counts double and the gauge shows twice the tasks. If it maps onto the old row, `succeeded` → `cached` is a lattice question that is not answered.
  - Snakemake sends nothing for jobs already done, so their rows must come from launch 1, and the "N reused" figure of ui §4.6 cannot be built from events.
  - The failed task of launch 1 re-running in launch 2 is a new attempt across launches. Its numbering, and whether the task's state returns from `failed` to `running`, is not stated.
  - A burst of 100 000 `onTaskCached` events at resume start adds to CH-005's traffic budget.
- **Proposal:**
  - api §7 (owner): define the logical task key per engine (shared with CH-047) and add `attempts.launch_n`.
  - "Cached in launch k" is an attempt state on the same task. Task state is a function of its last attempt, so `failed` → `running` is legal across launches. The run lattice (CH-042) stays per launch.
  - nf-spectio may send cached tasks as one aggregated event per process (architecture §13.2).
- **Likelihood · impact:** certain on every resume · medium to high (wrong counts, gauge and estimates).
- **Cheapest test:** one hour. From the spike's `gate_qc_then_resume`, capture nf-spectio's and the logger's events for launch 2, and check the task IDs and counts of cached tasks against launch 1 (spike 2).
- **Related:** CH-042, CH-047, CH-005 (R4).
- **Found by:** constraints-hunter
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### SR-059 · major · When every check passes, does the planned stop open a gate or continue automatically?

- **Where:** owner checking-scenarios.md §4, §12.4; api-and-data-model.md §7.1; synthesis.md §5ter.4.
- **Evidence:**
  - "`block` (opens the gate), `warn` (shown, does not open it)" (checking §4, l.93).
  - "A stage boundary is a planned stop, fixed at launch" (checking §11.3, l.355); "the run ends after the gated stage; Continue relaunches with `-resume`" (ui §5.1).
  - `decide`: "`auto_approve`, `timeout`, `on_timeout`" are listed with no meaning (checking §12.4, l.414); "applies the policy (auto-approval under threshold, timeout, escalation)" (synthesis §5ter.4, l.263).
  - "`running` → `awaiting_review`: a gate opens at the end of a stage" (api §7.1). There is no transition for a boundary where no gate opens.
- **Problem:** the specs allow three readings: (a) the gate always opens; (b) the gate opens only when a block check fails, and Spectio otherwise continues by itself; (c) `auto_approve` decides. Reading (b) has no actor, event or gate row for the automatic Continue. Journey 1 needs a gate to approve even when the test data passes.
- **Proposal:**
  - checking §4 and §12.4: a gate row is always created at the boundary. If every `block` check passes and `decide.auto_approve: when_checks_pass` is set, Spectio records `approve` with `actor_kind = service`; otherwise the gate stays open. A failed `warn` never prevents auto-approval.
  - Reword §4 as "`block`: a failure prevents auto-approval".
  - The default for 0.0.1 is a question for Thomas (question 2).
  - api §7.1 records the automatic decision.
- **Found by:** spec-reviewer
- **Status:** inbox, assumed: (c) a gate row is always created; `auto_approve: when_checks_pass` is opt-in and the 0.0.1 default waits for a person — pending Thomas (TRIAGE2, 2026-10-27), inbox #33

### SR-065 · major · The Snakemake launch form and parameter delivery are not specified for 0.0.1

- **Where:** owner ui-spec.md §4.6, with checking-scenarios.md §12.1 (`ui`); synthesis.md §5ter.5.
- **Evidence:**
  - "generated from `nextflow_schema.json` (or the Snakemake config schema plus the `ui:` block of `spectio.yml`)" (ui §4.6, l.157).
  - `ui`: "format still to be drafted" (checking §12.1, l.398); ui §9 lists it as an open item.
  - Snakemake config schema: "`workflow/schemas/config.schema.yaml` (no UI hints)" (ui §8, l.308). That workflows may have no schema file is **[to be validated]**.
  - "`GET /workflow-versions/{id}/schema` is undefined for a workflow with no schema" (UX-119, accepted, Nextflow only).
  - LaunchSnakemake draws a form from the config schema and a `ui:` block that does not exist yet.
- **Problem:** journey 2's form cannot be built: there is no fallback when only `config/config.yaml` exists; the `ui:` block is undrafted; how values reach Snakemake (generated configfile or `--config k=v`, nested keys, lists) is open.
- **Proposal:**
  - ui §4.6: in 0.0.1 the form comes from `config.schema.yaml` when present, otherwise from the value types in `config/config.yaml` (nested maps become sections). The `ui:` block is "later".
  - synthesis §5ter.5: the runner writes the non-default values to `<launch_dir>/.spectio/config.<n>.yaml` and passes it with `--configfile` after the workflow's own configfile, never `--config`.
  - The schema endpoint returns the inferred schema with `inferred: true`.
- **Related:** UX-119 (R12, accepted), UX-243 (Snakemake relaunch variant).
- **Found by:** spec-reviewer
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### UX-243 · major · Relaunch with changed parameters has no parameter editor and no Snakemake variant

- **Where:** RelaunchDialog: "Edit parameters · 2 changed · suggested from the failure · from sacct" (x 102–918, y 600–790); "Edit other parameters…" links to `Launch.dc.html` (RelaunchDialog.dc.html:112); footer "Nextflow -resume … plus the extra config". ui-spec.md §4.6; api-and-data-model.md §5 `:relaunch`.
- **Evidence:**
  - The dialog edits only resource overrides (`withName: 'STAR_ALIGN' { memory = 96.GB }`). R12 UX-113 notes the API has no such field.
  - The 0.0.1 feature is parameter overrides, which `:relaunch` accepts (api §5, l.88), but they are reached only by leaving the dialog for a fresh Launch form. That loses the mode (Resume or Rerun from a stage) and the work directory.
  - Journey 2 changes two Snakemake config keys, and no board shows that.
- **Problem:** the core 0.0.1 relaunch action is undrawn. An implementer would send people to Launch, which creates a new run with no lineage rather than a relaunch.
- **Proposal:**
  - Inside the dialog, replace the resource list with an "Edit parameters" panel. It reuses the Launch form sections: schema groups, search, "Changed only", validation with the disabled reason beside the button, and a diff line "2 changed vs. run #N".
  - Add a Snakemake variant: config keys from the config schema (or the inferred form of SR-065), "`--forcerun` from stage" or "Continue".
  - Show the reused / to-run estimate only when it is available, labelled "estimate" (UX-113). Which stages rerun is R12 UX-109.
  - After submitting, open the new or continued run's RunDetail.
- **Related:** SR-062 (which path the dialog serves at a gate), SR-063, SR-065, UX-109 and UX-113 (R12).
- **Found by:** ux-reviewer
- **Status:** inbox, assumed: the relaunch dialog edits parameters for the child run of path B, with a Snakemake variant — pending Thomas (TRIAGE2, 2026-10-27), inbox #32

### UX-250 · major · RunsCompare cannot be reached from a 0.0.1 run screen, and draws data a local run does not have

- **Where:** RunsCompare header (x 946–1416, y 100–140); "CPU-hours · from sacct TotalCPU" (y 965–1010, footnote y 1064); "Reports · MultiQC · depictio dashboard" (y 930–955). RunDetail Lineage aside (x 1096–1416, y 732–912). RunsTable (no row selection). ui-spec.md §4.3, §4.4 (Lineage), §11 (`n/a`).
- **Evidence:**
  - Links to `RunsCompare.dc.html` exist in Coverage.dc.html:80 and in the Lineage tab of RunFailed, RunLiveChecks and RunOutputs (checked in this merge; the reviewer named Coverage only). None of those four is on the 0.0.1 map.
  - RunDetail, RunsTable and RunsRows, which are on the map, have no Compare action or multi-select. RunDetail's Lineage tab is a plain label.
  - A compare endpoint is R12 UX-114.
- **Problem:** journey 2 ends on a screen the user cannot reach from the 0.0.1 boards. CPU-hours and the depictio link have no source in 0.0.1.
- **Proposal:**
  - "Compare with previous" on the Lineage aside and on the Parameters tab.
  - Row selection (2–4 runs) in RunsTable with a "Compare" bar.
  - A 0.0.1 variant of RunsCompare: Stages, Tasks reused or computed, Parameters (differences or all), Software. CPU-hours shown as "n/a · no scheduler accounting on a local run" (ui §11); no depictio link.
- **Related:** SR-064, UX-114 (R12), UX-227 (R7, boards show features 0.0.1 lacks).
- **Found by:** ux-reviewer
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### CH-045 · major · The projector has no checkpoint: events acknowledged but not projected at a crash, re-projection and catch-up order

- **Where:** owner api-and-data-model.md §8.1, §8.2; synthesis.md §4.
- **Evidence:**
  - "1. Ingest validates the batch, appends it to `events` and acknowledges. 2. One projector, on a dedicated writer thread or process … builds `runs`, `tasks` and the other projections from the log." (api §8.1, l.323–326)
- **Problem:**
  - Moving projection out of the ingest transaction (CH-012) creates a window: after a crash, events are in `events` but not in `runs` or `tasks`.
  - Nothing records how far the projector has gone. There is no `projector_checkpoint (projection, run_id, seq)`, and no rule that the projection update and the checkpoint commit in one transaction.
  - On boot the projector either re-applies the whole log, which is slow at 100 000 events per run (CH-004), or loses the tail.
  - Side effects of projection have no idempotency rule: opening a gate at a stage boundary, emitting `spectio.run.state_changed`, enqueuing `check.dispatch`. A re-applied stage boundary could open a second gate or enqueue a second evaluation.
- **Proposal:** api §8.1 (owner) adds:
  - a per-run projector cursor (`runs.projected_seq`), updated in the same transaction as the projection rows;
  - on boot, project every run with `projected_seq < last_seq` before the run is served as fresh (link CH-051);
  - every side effect is keyed by a deterministic ID (for example a gate keyed on (run_id, stage_index, launch n)), so re-projection is a no-op.
- **Likelihood · impact:** high (every unclean stop) · medium to high (a stale run state, a duplicate gate).
- **Cheapest test:** a one-hour unit test. Kill the projector thread between two batches, restart, and compare the projections with a full rebuild from `events` (part of spike 4).
- **Related:** CH-012, CH-004 (R4), CH-049, CH-051.
- **Found by:** constraints-hunter
- **Status:** accepted (TRIAGE2, 2026-10-27)

### SR-066 · major · How the runner computes the Snakemake `--until` targets from `match` globs is unspecified

- **Where:** owner checking-scenarios.md §12.3; ui-spec.md §5.1.
- **Evidence:**
  - "**Snakemake:** `--until` the last rules of the stage; Continue drops `--until`; rerun from a stage uses `--forcerun`." (checking §12.3, l.405–411)
  - "Stages are defined by `match` globs only" (checking §12.3).
  - `stages[]`: "`match` (globs on process / rule names)" (checking §12.1).
- **Problem:** "last rules" needs this config's rule graph. Undefined: how the runner gets the rule graph; checkpoints, which change the DAG after the stage; rules matched by no stage, or by two stages; stage rules absent from this config's DAG; which rules `--forcerun` targets.
- **Proposal:** checking §12.3:
  - Before launch, the runner does a dry run in the workflow's environment to get the rule graph (`snakemake -n --rulegraph` or equivalent, **[to be validated]** in spike T1/T2).
  - Targets = the rules of stage k that no other rule of stage k consumes.
  - `spectio workflow validate` rejects a rule matched by two stages.
  - A checkpoint inside a gated stage → "gates unavailable", with the reason.
  - `--forcerun` = the stage's rules that have no producer inside the stage.
- **Found by:** spec-reviewer
- **Status:** accepted (TRIAGE2, 2026-10-27)

---

## Minors

### CH-051 · minor · Boot recovery has no defined order and no "catching up" signal in the UI

- **Where:** owner architecture-plugins-and-packaging.md §7.2; api-and-data-model.md §8.1; ui-spec.md §11; admin-and-operations.md §3.2.
- **Evidence:**
  - SQLite runs with one writer connection and `wal_checkpoint(TRUNCATE)` (architecture §7.2).
  - ui §11 defines Reconnecting, Stale, Head silent, Runner offline and the full-page "Spectio is unreachable", but no recovering state.
- **Problem:**
  - At boot, five things compete for the single writer: WAL recovery, projector catch-up (CH-045), spool replay (CH-044), head adoption (CH-041) and the timeout sweep (CH-049). SSE clients reconnect at the same time.
  - Served too early, the UI shows "running" for runs that ended during the downtime, and a user may Resume or Cancel against stale state.
  - A large replay grows the WAL past the checkpoint threshold (CH-013).
- **Proposal:**
  - architecture §7.2 (owner) states the boot order: open the DB, adopt the heads, catch up the projector, replay the spool with a rate cap, then sweep.
  - Until a run is caught up, the API marks it `recovering: true` and refuses state-changing verbs with `409`. ui §11 adds a "Catching up after restart" banner (drawn in CH-041's RunDetailReconnect frames).
- **Likelihood · impact:** high · low to medium.
- **Cheapest test:** with the CH-044 setup, time from boot to correct states, and count user-visible wrong states (spike 4).
- **Related:** CH-041 (absorbs UX-246's UI frames), CH-013 (R4).
- **Found by:** constraints-hunter
- **Status:** inbox, assumed: apply the proposal as written — pending Thomas (TRIAGE2, 2026-10-27), inbox #40

### UX-249 · minor · RunDetail's "Parameters changed vs. previous run" lists a parameter that did not change

- **Where:** RunDetail aside "Parameters changed vs. previous run" (x 1096–1416, y 336–508); RunDetail.dc.html `diff` data. ui-spec.md §4.4 (Parameters tab).
- **Evidence:** the first row is `aligner star_salmon → star_salmon`, struck through in red, then green.
- **Problem:** parameter history is a 0.0.1 feature. The only drawn example teaches implementers to list unchanged keys as changes. "Previous run" is also ambiguous: the lineage parent (ui §4.4) or the last run of the same workflow?
- **Proposal:**
  - List only changed keys, plus "N unchanged hidden · Show all".
  - Label the comparison "vs. run #N (resumed from)".
  - Link to the Parameters tab and to RunsCompare (UX-250).
- **Related:** SR-064 (`changed_vs_parent` with `parent_run_id` as the baseline).
- **Found by:** ux-reviewer
- **Status:** accepted (TRIAGE2, 2026-10-27)

## Cited, not repeated

The reviewers cited these earlier findings instead of raising them again. They are not counted above. Where an R3 finding adds a 0.0.1 angle, it says so in its **Related** line.

| Earlier finding | Round | Cited by | Note |
|---|---|---|---|
| SR-001 · ingest contract (api §14) | R1 (inbox #11) | SR-054, CH-044 | SR-054 asks to split #11 so the driven-run part is written for 0.0.1. |
| CH-001 · head job and compute-node egress | R4 (assumed) | SR-067 | Relevant to nf-spectio delivery (registry against a bundled jar). |
| CH-002 · ingest version header | R4 | SR-054 | One of the items §14 must carry for 0.0.1. |
| CH-003 · Continue racing the previous head | R4 (partly applied, inbox #16) | SR-062, CH-042, CH-043, journey 3 step 13 | The lock wait is specified; `CONTINUE_REQUESTED` pending. |
| CH-005 · bridge traffic budget | R4 | CH-050 | Cached-task bursts on resume add to it. |
| CH-007 · durable runner commands | R4 (assumed) | SR-055, CH-041 | 0.0.1 needs the in-process reading of the same rows. |
| CH-009 · Snakemake logger interface and environment | R4 (partly applied) | SR-067 | |
| CH-010 · gate waits against scratch purge, cache estimate | R4 | journey 3 step 11 | The reuse estimate. |
| CH-012 · projection outside the ingest transaction | R4 | CH-044, CH-045 | CH-045 adds the missing checkpoint. |
| CH-013 · SQLite lock discipline | R4 | CH-051 | |
| CH-014 · gate concurrency and timeout races | R4 | CH-049 | |
| CH-016, CH-017 · gate stop on real nf-core; live-check cost | R4 | SR-058 | |
| CH-018 · resumable stream cursor | R4 | journey 4 step 20 | |
| CH-028 · systemd kills supervised heads | R4 | CH-041 | CH-041 is the in-process case. |
| CH-033 · restart storms | R4 (applied) | CH-044, journey 4 step 11 | |
| FC-002 · generated `ext.when` must wrap the pipeline's own | R2 (accepted) | SR-057 | |
| FC-020 · Nextflow upgrades break the cache | R2 | CH-043 | |
| UX-101 · MultiQC column names | R12 | SR-058 | |
| UX-103 · check `n/a` state | R12 | SR-058 | The state exists; no board draws it. |
| UX-109 · which stages a parameter change reruns | R12 (inbox) | SR-062, UX-243, journey 3 step 11 | |
| UX-112 · adding a gate at launch | R12 | SR-057 | |
| UX-113 · resource overrides and dry-run estimate | R12 (inbox) | SR-063, UX-243, CH-047 | |
| UX-114 · compare endpoint | R12 (accepted) | SR-064, UX-250 | |
| UX-119 · launch form for schema-less workflows | R12 (accepted) | SR-065 | Covers Nextflow only. |
| UX-123 · who clones on import | R12 (inbox) | SR-056 | |
| UX-205 · loading, error and stale states | R7 | CH-041 | Still undrawn. |
| UX-211 · first-run and empty states | R7 (accepted) | SR-055, journey 1 step 3 | |
| UX-216 · launch flow and gate label | R7 (partly applied) | SR-057 | |
| UX-219, UX-236 · keyboard and focus | R7 | ux-reviewer scope note | Not specific to 0.0.1. |
| UX-223 · run actions differ between boards | R7 | ux-reviewer scope note | |
| UX-225 · boards disagree on shared data | R7 | ux-reviewer scope note | |
| UX-227 · boards show features 0.0.1 lacks | R7 | UX-250, journey 1 step 7 | |
| Legend: Pausing and Cancelling not drawn | R1 (pending) | ux-reviewer scope note | |

## Questions for Thomas

1. **Relaunch at a failed gate, and Resume after a failure (SR-062, CH-042, SR-063, UX-243).** Options: (A) the same run continues: gate `apply` or `go_back` carries a parameter change set, and `failed` → `queued` is allowed, with the lattice per launch; (B) a new child run: at a gate, "Relaunch…" records `stop` (reason `relaunched`) and calls `:relaunch` (`rerun_from` the gated stage, parameter overrides); after a failure, Resume creates a child run reusing the parent's launch directory, and the parent stays terminal. **Recommendation: B for both.** It keeps the run lattice and the WES mapping intact, it is what journey 2's "compare the two runs" needs, and it reuses one verb (`:relaunch`). ux-reviewer proposed A (`go_back`) for the gate; A keeps history in one run but needs per-launch lattice rules.
2. **Default when every check passes (SR-059).** Options: (a) the gate always waits for a person; (b) Spectio continues by itself; (c) a gate row is always created, and `decide.auto_approve: when_checks_pass` in the manifest turns on automatic approval. **Recommendation: (c) with the default "wait for a person" in 0.0.1**, because journey 1 needs a gate to approve, and automatic approval stays recorded as a decision by `service`.
3. **How nf-core/rnaseq gets its stages and gate (SR-057, SR-056).** Options: (a) 0.0.1 ships one built-in rnaseq overlay; (b) the user passes a `spectio.yml` at launch (`--gates FILE`, inline in `POST /runs`); (c) the overlay editor UI. **Recommendation: (a) plus (b)**, overlays edited as YAML only and displayed read-only in the UI; the editor is later.
4. **MultiQC in the default install (SR-058).** Options: (a) the documented 0.0.1 install becomes `spectio[server,checks]`; (b) the MultiQC reader moves into `[server]`; (c) keep `[server]` and show `n/a` checks that must be acknowledged. **Recommendation: (a)**, with a missing value mapped to verdict `error` so a gate never auto-approves on missing data.
5. **Engine prerequisites and nf-spectio delivery (SR-067, SR-055, SR-061).** Does the user install Java, Nextflow and Snakemake themselves, with `spectio doctor` and the EnvLocal "Engines ready" list reporting them? Does nf-spectio come from the Nextflow plugin registry, or as a jar in the spectio wheel installed through the plugins directory **[to be validated]**? **Recommendation: the user installs the engines; nf-spectio ships in the wheel**, so its version is pinned with the server and the head can run offline (in line with R4 CH-001); the registry can follow later.
6. **Two 0.0.1 contracts parked or unstated (SR-054, CH-041).** (a) May inbox #11 be split, so the driven-run part of api §14 (envelope, run ID and launch number variables, ack, version header, no credential on loopback) is written for 0.0.1 and only the observed-run credential stays deferred? (b) When `spectio serve` gets SIGTERM in personal mode, do engine heads keep running (detached, re-adopted on boot) or stop? **Recommendation: split #11; heads keep running**, because a restart or upgrade should not fail a multi-hour run.

## Proposed spikes

One ranked list, merged from the three reviewers, ordered by risk removed per hour (likelihood × impact ÷ cost). constraints-hunter's five keep their relative order (1, 2, 4, 5, 6).

| # | Spike | Settles | Cost | Needs |
|---|---|---|---|---|
| 1 | **Head survival and adoption.** A prototype `spectio serve` with a `setsid` wrapper and a `head.exit` file; send `kill -9`, SIGTERM, Ctrl-C and `systemctl --user restart`; check that the head survives, `head.exit` is written, a restarted stub adopts the head without a second launch; then `kill -9` the head alone and check the projected run and task states | CH-041, CH-046 | ½ day | nf-toy, smk-toy, `run_scenarios.py` |
| 2 | **Resume semantics on both engines.** Replay `tool_error_then_fixed_resume` and `gate_qc_then_resume` through a 30-line projector stub under CH-042's options (a) and (b); `-resume` with and without a session ID after a second run in the same directory; Snakemake rerun after `kill -9`, with and without `--unlock` and `--rerun-incomplete`; capture the cached-task events of launch 2 | CH-042, CH-043, CH-050, SR-063 | ½ day | `run_scenarios.py` |
| 3 | **rnaseq gated after alignment.** Run the rnaseq test profile with a generated `ext.when` stop after stage 1; run MultiQC limited to the `star` module on the stage outputs; check that a `star` value comes out, and the cost of the call | SR-058, SR-057 | ½ day | local Docker; overlaps R4 spike 5 and spike 15 |
| 4 | **Restart replay** (R9 spike 3, extended). Stop the server for 2 and 30 minutes during a 500-job smk-toy run, restart, diff the projected task states against `execution_trace.txt` and `.snakemake`; kill the projector between two batches and compare with a full rebuild; record the catch-up time and WAL size | CH-044, CH-045, CH-051 | ½ day | spike 1's wrapper |
| 5 | **Log sources.** On the spike's failure scenarios (`tool_error_then_fixed_resume`, `oom_fatal`, `flaky_retry`, `timeout_fatal`), list per engine which files hold the failing stderr, which logger or trace events carry their paths, and which task the engine names as the cause | CH-048, CH-047 | 1 h | nothing |
| 6 | **Gate across a restart.** With a stub: a `timeout: 2m` gate expiring during a 5-minute downtime, and a check evaluation killed mid-way | CH-049 | 1 h | nothing |
| 7 | **Snakemake rule graph for `--until`.** `snakemake -n --rulegraph` (or equivalent) on smk-toy and a workflow with a checkpoint; compute the stage's last rules and the `--forcerun` set from `match` globs | SR-066 | 2 h | T1 or T2 |
| 8 | **Resolved parameters from the bridges.** Read `session.params` in nf-spectio and the workflow config in the logger; compare with the submitted non-default values and the schema defaults | SR-064 | 2 h | T2 |
