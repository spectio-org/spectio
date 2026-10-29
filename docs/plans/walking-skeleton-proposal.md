# Walking skeleton: proposal (one page)

*Draft, 2026-10-28. Waiting for Thomas: [inbox #52](../reviews/inbox.md). Nothing here is decided, and no product code is written until he answers.*

*Note 2026-10-29: Thomas answered #52 with option (b) and gave the GO for P1, M1 to M8 ([log](../decisions/log.md#2026-10-29-go-for-the-whole-p1-plan-with-five-changes)).*

## Goal

This is the smallest Spectio that runs end to end on one machine. It launches a Nextflow or Snakemake run, receives the engine's events as they happen, stores the run's state, and serves that state through a small API and the CLI. It is built on what W3 already proved, so that the first questions of the product are answered by running code, not by more specs:
- T2 captured both engines' event streams ([spike](../research/spike-engine-events-2026-10-28.md));
- T1 provides pipelines that fail on demand;
- D3 pins the engines.

## Scope

| In | Out (later, when code needs it) |
|---|---|
| `spectio run <pipeline>` on the local launcher | SLURM and Kubernetes launchers (T3 and T4 give their fixtures and RBAC) |
| Nextflow events through `nf-spectio` (`TraceObserverV2`, from the T2 spike); Snakemake events through a logger plugin | Gates, QC checks, AI decisions |
| One server process: FastAPI, SQLite, an ingest endpoint and `GET /runs`, `GET /runs/{id}` with task states | Auth beyond one local token, multi-tenancy, depictio integration |
| `spectio status <run>` reading the API | Web UI (the boards stay the target), Playwright (T6) |
| Run states: queued, running, succeeded, failed, with retries and resume visible | Scenario isolation (T5), previews, versioned docs |

The package layout follows [architecture §6](../specs/architecture-plugins-and-packaging.md#6-code-layout), but only `spectio-sdk` (the event schema), `spectio` (CLI and local launcher), `spectio-server` and `engine-bridges/nf-spectio` are created.

## Done when

- The T1 synthetic scenarios `happy`, `flaky_retry`, `oom_fatal` and `tool_error_then_fixed_resume` run through `spectio run`, on Nextflow 26.10.4 and Snakemake 9.27.1. For each one, the API reports the same final task states as the T1 golden fixtures, and an integration test in CI checks that.
- `nf-core/demo -profile test,docker` runs through `spectio run` in CI and is reported `succeeded`.
- A run killed mid-way is reported `failed`. Resuming it shows its cached tasks.

## Steps (each a PR to `main`, tests first)

1. **Event schema** in `spectio-sdk`, written from the T2 fixtures (`spikes/engine-events/fixtures/`), and unit-tested against them.
2. **Ingest and store:** a FastAPI endpoint, SQLite tables for runs and tasks, and replay of the T2 fixtures as the test.
3. **Bridges:** `nf-spectio` from the spike, plus the Snakemake logger plugin, both posting to the ingest endpoint.
4. **Local launcher and CLI:** `spectio run` and `spectio status`.
5. **CI:** a scenarios job that runs the "Done when" list.

## Process for this phase

- Product code gets one `code-reviewer` and one `security-reviewer` pass per PR, plus tests in CI.
- Tooling and test changes get tests and one review, with no separate review record.
- The docs are the PR body plus the spec section the code implements. A Progress page is written per milestone, not per PR.
- When the code contradicts a spec, the spec changes in the same PR.
