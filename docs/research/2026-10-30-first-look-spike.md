# Spike first-look — the merged code end to end, in a browser (2026-10-30)

**Question.** Can the code merged so far (P1 Tasks 1–4: the spool event contract, the spool reader, the SQLite store and the projector) run end to end and show a runs list and a run detail in a browser, today, with no Nextflow and no bridge?

**Answer in one line.** **Yes.** Synthetic `nf-spectio` spools pass the real `read_spool` with zero drops; the real projector writes runs, tasks and attempts into a real migrated SQLite store; a 400-line throwaway page shows a succeeded run with a retried task, a failed run with its culprit, and a live run that moves every 3 seconds until it succeeds. Four findings on the projector and the data model are listed [below](#findings).

This is a spike, not product code. No spec, plan, inbox entry or `pipeline.yaml` status was changed.

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
uv run python spikes/first-look/demo.py            # then open http://127.0.0.1:8765/
uv run python spikes/first-look/demo.py --port 9000 --period 1   # faster live run
uv run python spikes/first-look/make_spool.py /tmp/fl            # spools only, no server
node spikes/first-look/shoot.js 8765               # screenshots, with the demo running
```

In a Codespace, run the same `uv run` command in the terminal; Codespaces forwards a port that a process opens on localhost and offers to open it in the browser **[to be validated]** (not tried in this spike). Each start creates a fresh `/tmp/spectio-first-look-*` directory (or under `$TMPDIR`) and prints its path; nothing in the repository is written.
