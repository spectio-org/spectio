# Spike first-look — the merged code end to end, in a browser (2026-10-30)

**Question.** Can the code merged so far (P1 Tasks 1–4: the spool event contract, the spool reader, the SQLite store and the projector) run end to end and show a runs list and a run detail in a browser, today, with no Nextflow and no bridge?

**Answer in one line (part 1).** **Yes.** Synthetic `nf-spectio` spools pass the real `read_spool` with zero drops; the real projector writes runs, tasks and attempts into a real migrated SQLite store; a 400-line throwaway page shows a succeeded run with a retried task, a failed run with its culprit, and a live run that moves every 3 seconds until it succeeds. Four findings on the projector and the data model are listed [below](#findings).

This is a spike, not product code. No spec, plan, inbox entry or `pipeline.yaml` status was changed. [Part 2](#part-2-a-real-nextflow-launched-from-the-page) (same day) replaces the synthetic events with a real Nextflow run and the spike T2 plugin, launched from the page or the shell.

## Setup

- **Branch** `spike/first-look`, from `adfb924` (tip of `autopilot/P3-t04`: Task 4's projector on top of Tasks 1–3). The files are in `spikes/first-look/` on that branch:

  | File | What it does |
  |---|---|
  | `make_spool.py` | writes three launch directories, each with `.spectio/events/nf-spectio-1-0001.jsonl` (directories 0700, file 0600), for a FASTQC → TRIM → ALIGN → MULTIQC pipeline; `--follow` appends the live run over time |
  | `demo.py` | creates a private temp directory, writes the spools, opens the store with `open_db` (migrations included), seeds what the launch API would write, then every 3 s reads each spool with `read_spool` and ingests it with `ingest` on the one `Writer`; serves two read-only pages on `127.0.0.1:8765` |
  | `shoot.js` | Playwright screenshots of the running demo into `shots/` |

- **Real code exercised:** `spectio_sdk.events` (envelope and allow-lists), `spectio.runner.spool.read_spool`, `spectio_server.store.db.open_db` (SQLite 3.53.1, WAL, private directory checks, Alembic to head), `spectio_server.store.writer.Writer`, `spectio_server.projector.ingest.ingest` / `load_cursor` and the Nextflow mapping.
- **The three runs** (event shapes copied from the T2 fixtures, `tests/fixtures/engine-events/nextflow-26.10.4_plugin_flaky.spool.jsonl`):
  - `rnaseq-pilot`: 4 samples, 13 tasks, `ALIGN (S03)` attempt 1 fails with exit 137 and `errorAction: RETRY`, attempt 2 succeeds; `onFlowComplete success: true`.
  - `wgs-cohort-12`: 3 samples, `TRIM (NA12891)` fails with `errorAction: TERMINATE`, then `onFlowError` and `onFlowComplete success: false`; one TRIM task is still running at that point.
  - `atac-limb-e11`: 6 samples, 19 tasks, one retry; 6 steps are written at start, the rest one step every 3 s (about 90 s in all).
- Every trace record carries `script: "… --secret-flag"` and `env: "API_TOKEN=must-never-be-stored"`, as Nextflow's trace record does.

## Results

| Check | Result |
|---|---|
| `read_spool` on the three spools | 67, 32 and 25 events on the first read, `drops` empty |
| Live run | ingested in increments of 1–6 events; `runs.last_seq == projected_seq` after every read |
| Run states | `succeeded`, `failed`, and `running` → `succeeded` for the live run |
| `runs.task_counts` | `{"succeeded": 13}`; `{"aborted": 1, "failed": 1, "succeeded": 4}`; `{"succeeded": 19}` at the end of the live run |
| Retry | `ALIGN (S03)`: one task, attempts `#1 failed · exit 137` and `#2 succeeded · exit 0` |
| Failure | `runs.failure = {class: tool_error, task_id: <TRIM (NA12891)>, attempt_n: 1, message: "Process …terminated with an error exit status (1)"}`; the other running TRIM attempt was closed `aborted` by `onFlowComplete` |
| Allow-list | `SELECT count(*) FROM events WHERE payload LIKE '%must-never%' OR … '%secret-flag%' OR … '"script"' OR … '"env"'` → **0** |
| `launches` | `engine_session_id` from `onFlowCreate`, `head_state` `succeeded` / `failed` from `onFlowComplete` |
| Spool drops | none stored for any launch |

Screenshots (on the branch, `spikes/first-look/shots/`): `runs.png` (runs list, desktop), `runs-phone.png` (390 px), `run-atac-limb-e11.png` (live run, mid-way), `run-rnaseq-pilot.png` (succeeded, with the retry), `run-wgs-cohort-12.png` (failed, with the culprit and the aborted task). The look follows `LiteRuns.dc.html` and `LiteRunDetail.dc.html` loosely: state bar on the left of each row, state chips, a processes table in first-seen order, attempts per task, the last 12 events of the log.

Everything on the pages comes from the database the projector wrote: `runs`, `launches`, `tasks`, `attempts`, `events`, `spool_drops`, and the seeded `workflows` / `workflow_versions`. The process order is read from the logged `onProcessCreate` events.

## What is faked

- **Events are synthetic.** No Nextflow ran and the `nf-spectio` bridge (P1 Task 6) does not exist. The shapes follow the T2 captures, but timings, hashes and trace values are made up.
- **No launch.** `demo.py` inserts the project, environment, workflows, the `queued` runs and their `launches` rows directly, standing in for the launch API (Task 17). Run names are seeded there.
- **No head report.** Nothing calls `apply_head_report` (Task 9 runner loop), so `head_state` stays empty until `onFlowComplete` and `exit_code` stays empty.
- **No server.** No `spectio serve`, token, cookie, host allow-list or Origin checks (Tasks 11–16); the page is a stdlib `http.server` on 127.0.0.1 with no API (Task 18). Not safe to expose.
- **No stages** (Task 27), no logs, no parameters, no Cancel.

## Findings

1. **Run times use the ingest clock, so a backlog collapses durations.** `Projection.load` takes `now = datetime.now(UTC)` once per batch (`packages/spectio-server/src/spectio_server/projector/runs.py:69`), and `move` writes it to `runs.started_at` and `ended_at` (`runs.py:95-97`). The two finished runs were read in one batch each, so both show `started_at == ended_at` (duration 0 s) although their events span 4 min 24 s and 2 min 04 s of engine time. The same happens to any run whose spool is read after the fact: a server restarted after the run ended, or the boot rebuild of Task 11. api §7 defines duration as `ended_at − started_at` and §8.2 says to "compute durations from one clock source"; neither says which clock fills these two columns. Open question for Thomas: should they come from the first and last `engine_time` of the launch, or should duration be computed from `events.engine_time`?
2. **A retried failure keeps no class and no error action.** `failure_class` is set only for `errorAction: TERMINATE` (`projector/nextflow.py:68-72`); the attempt that failed with exit 137 and `RETRY` is stored as `failed · exit 137`, with no class and no record of the action. api §7 lists `oom` among the attempt classes and the boards show retries with their cause. Whether exit 137 maps to `oom` is a classification rule not yet written (`schedulers-and-monitoring.md` §3.5); for now the UI can count retries only as attempts with `n > 1`.
3. **Processes and their order exist only in the event log.** `onProcessCreate` and `onProcessTerminate` are logged but not projected: a process with no task yet (`ALIGN` and `MULTIQC` in the failed run) is in no table. Tasks and attempts of one batch share one `created_at`, and `new_id` ULIDs are random within a millisecond (`spectio_server/ids.py`), so neither gives the first-seen order the board uses. The demo reads both from `events`. `GET /runs/{id}/processes` (api §5, Task 18) will need either that query or a projected process list.
4. **Attempts keep no timings or resources.** The trace's `submit`, `start`, `complete`, `duration`, `realtime` and `peak_rss` are logged in the event payload but not projected: `attempts.resources` is never written and attempts have no start or end column. The run detail board's per-task duration and the `peak_rss_bytes` of `/processes` cannot be served from the projection yet. This may be planned for a later task **[to be validated]** against P1 Task 18.

No bug blocked the flow: every event was accepted, projected and kept in order, and ingesting the same batch twice leaves the log at 69 events and `last_seq` 69 (event IDs make a replay a no-op).

## Commands

```bash
git fetch origin spike/first-look && git checkout spike/first-look
uv run python spikes/first-look/demo.py --synthetic            # then open http://127.0.0.1:8765/
uv run python spikes/first-look/demo.py --synthetic --port 9000  # another port
uv run python spikes/first-look/make_spool.py /tmp/fl            # spools only, no server
node spikes/first-look/shoot.js 8765               # screenshots, with the demo running
```

In a Codespace, run the same `uv run` command in the terminal; Codespaces forwards a port that a process opens on localhost and offers to open it in the browser **[to be validated]** (not tried in this spike). Each start creates a fresh `/tmp/spectio-first-look-*` directory (or under `$TMPDIR`) and prints its path; nothing in the repository is written.

## Part 2: a real Nextflow, launched from the page

**Question.** Thomas asked for a script or README an agent can follow to start the service locally, run a lightweight dummy Nextflow pipeline (not nf-core), see the result, and launch it from the UI. Does the merged code hold up against real engine events?

**Answer in one line.** **Yes**, with three new findings. A real `nextflow run` (26.10.4) with the spike T2 plugin, launched from a "New run" form, goes through the real `read_spool`, projector and store with zero drops; a 3-sample run ends `succeeded` (10 / 10 tasks) and a run with an injected failure ends `failed` with the right culprit, retry and aborted task.

### What was built

On `spike/first-look`, after merging `origin/autopilot/integration` (so the final Task 4 code of `6dc5cce` is in):

| File | What it does |
|---|---|
| `spikes/first-look/run-local.sh` | downloads the Nextflow `26.10.4` `-dist` launcher (sha256 from `dev/versions.env`), builds the plugin into a private `NXF_HOME`, runs `uv sync`, starts the demo; `--cli` registers a run with `POST /api/launches` and runs Nextflow from the shell |
| `spikes/first-look/launch.py` | registers a run (project, run and launch rows), starts `nextflow run nf/main.nf -plugins nf-spectio@0.0.1` with `SPECTIO_ENDPOINT` set, reports the head with `apply_head_report`, and appends each plugin POST as one spool line through `convert_t2.convert_line` |
| `spikes/first-look/nf/main.nf` | FASTQC → TRIM → ALIGN per sample, then MULTIQC; sleeps 3 s per task; `--fail` makes ALIGN of the last sample exit 1 on both attempts (`errorStrategy` retry once, then terminate) |
| `spikes/first-look/nf-spectio/` | the prototype plugin of spike T2 (`spike/engine-events` at `3b4f654`), unchanged |
| `spikes/first-look/launch-ui.js` | Playwright: fills the form, waits for the end of each run, takes the screenshots |
| `spikes/first-look/AGENT.md` | the brief: prerequisites, commands, expected output, cleanup, troubleshooting, what is real |

The demo binds 127.0.0.1 only. The form's `POST /runs` needs a `Host` of `127.0.0.1:<port>` or `localhost:<port>`, an `Origin` equal to it and no cross-site `Sec-Fetch-Site`; the plugin posts to `/spectio/events/<token>`, a 32-character random token per launch; `POST /api/launches` takes JSON with no `Origin` only. Checked with curl: a foreign `Origin`, `Origin: null`, no `Origin`, a foreign `Host` and `Sec-Fetch-Site: cross-site` all get 403; an unknown token gets 404.

### What was run (in a Claude Code cloud container, 2026-10-30)

- OpenJDK 21.0.12, uv 0.11.32; Nextflow `26.10.4 build 14435` downloaded from `https://github.com/nextflow-io/nextflow/releases/download/v26.10.4/nextflow-26.10.4-dist`, sha256 `2cbda6e7…fdec4` as pinned in `dev/versions.env`. The plugin compiled in about 1 s with the Groovy compiler inside that jar.
- `run-local.sh` from an empty `$SPECTIO_FIRST_LOOK_HOME`, then `node spikes/first-look/launch-ui.js 8765`: run 1 (3 samples) `succeeded`, run 2 (2 samples, "Fail a task") `failed`, in 35 s in all.
- `run-local.sh --cli --samples 2`: Nextflow output in the shell (`[SUCCESS] completed=7 failed=0`), the run `succeeded` on the page with origin `cli-observed`.
- `demo.py --nextflow /bin/false`: the head exits 1 with no events and the run ends `failed · engine_fault` through `apply_head_report`. With an empty plugin directory Nextflow stops with `Plugin with id nf-spectio not found in any repository`.
- `demo.py --synthetic` without `--nextflow`: part 1's three runs, the form replaced by a note.

| Check | Run 1 (3 samples) | Run 2 (2 samples, failure) |
|---|---|---|
| Events (store seq) | 53, drops none | 42, drops none |
| `runs.state`, `task_counts` | `succeeded`, `{succeeded: 10}` | `failed`, `{aborted: 1, failed: 1, succeeded: 5}` |
| Attempts | one per task, `exit 0` | `ALIGN (S02)`: `#1 failed · exit 1`, `#2 failed · exit 1 · tool_error`; `MULTIQC` `#1 aborted` |
| `runs.failure` | none | `{class: tool_error, task: ALIGN (S02), attempt_n: 2, message: "injected failure"}` |
| `launches` | `head_state succeeded`, `exit_code 0`, head pid | `head_state failed`, `exit_code 1` (the engine's end kept over the head's `exited`) |
| Allow-list | no `script` or `env` key in any stored payload | same |

Screenshots in `spikes/first-look/shots/`: `launch-form.png`, `live-run.png` (run 1 with FASTQC done and TRIM running), `run-done.png`, `run-failed.png`, `runs-local.png`.

### Findings (part 2)

5. **Running and aborted attempts store exit 2147483647.** Nextflow's trace record carries `exit: "2147483647"` (Java `Integer.MAX_VALUE`, the task's "no exit status yet") on `onTaskPending`, `onTaskSubmit` and `onTaskStart`, and on the `onTaskComplete` of an aborted task. The T2 plugin already maps the task's own `exitStatus` of that value to `null`, but the projector falls back to `trace.exit` when `exitStatus` is null (`_exit`, `packages/spectio-server/src/spectio_server/projector/nextflow.py:136`), so `attempts.exit` is 2147483647 for every running attempt and for the aborted MULTIQC. The T2 spool fixtures hide this: `normalise.py --slim` drops the trace from the three non-final hooks, and only one fixture line (`nextflow-25.10.9_plugin_toolerr`, an aborted COMPARE) carries the value. Suggested fix, for a review: treat 2147483647 as no exit in `_exit`, and add a fixture with the full trace. The demo shows the stored value as `exit 2147483647 (none yet)`.
6. **`runs.failure.message` is the failing task's stderr.** On 26.10.4, `onFlowComplete.errorMessage` (from `session.workflowMetadata.errorMessage`) was `injected failure`, the text the tool wrote to stderr, and the projector stores it as the failure message (capped at 4096 characters). Snakemake's error text has its command hidden (`_hide_command`), Nextflow's has no such step. Whatever a tool prints on stderr, a token included, reaches `runs.failure` and every reader of the run. Worth a look in the security review of the allow-lists (api §14.1) **[to be validated]** on a real tool error with a longer stderr.
7. **The order spike T2 reported holds, and the projector copes.** `onFlowComplete` (success false) came before `onFlowError` (no task data), and MULTIQC got `onTaskPending` after the failure and nothing more; the projector ended the run on `onFlowComplete`, logged `onFlowError` only, and closed MULTIQC `aborted`. Store `seq` differs from the plugin's `seq` because the projector logs its own `spectio.run.state_changed` events in the same sequence: fine, but a reader that compares the two must not assume they match.

Part 1's finding 1 (run times from the ingest clock) is milder live: `started_at` is when the head report moved the run to `running` (09:02:05 for run 1, its first engine event at 09:02:07) and, with a read every second, `ended_at` is within a second of the last engine event. It still applies to any spool read after the fact.

### What is still not real

The server and its security (P1 Tasks 11–16), the launch API (Task 17), the head launcher (no head script, no tmux, no scheduler; a `subprocess.Popen` stands in), and the Task 6 `nf-spectio`: the prototype plugin of T2 posts each event over HTTP and the demo writes the spool, where the Task 6 plugin is to write the spool itself. A run launched with `--cli` gets no head report: nothing watches that process, so its state comes from engine events only.

### Commands (part 2)

```bash
git fetch origin spike/first-look && git checkout spike/first-look
spikes/first-look/run-local.sh                     # http://127.0.0.1:8765/, "New run"
spikes/first-look/run-local.sh --cli --samples 2 --fail
node spikes/first-look/launch-ui.js 8765           # with the demo running: launch two runs, screenshots
rm -rf ~/.cache/spectio-first-look                 # clean up
```
