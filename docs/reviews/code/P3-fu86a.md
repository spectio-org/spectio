# Code review · FU-P3-86a: the run's own environment snapshot

`review-code` on `autopilot/P3-fu86a`, 2026-11-09. The step is FU-P3-86a of [inbox #133](../inbox.md#133-assumed-environments-local-slurm-define-a-new-one-fu-p3-86); the behaviour is owned by [api-and-data-model §5.4](../../specs/api-and-data-model.md) ("The database is not the source of any run's environment", Resume). Format: [`README.md`](../README.md). This record holds the round 2 fix; the rest of the record is written with the step's docs.

## Round 2 fix

Base `ad5e2719`. Each finding of round 2, and the round 1 finding that was still open:

- **CR-P3FU86A-02 (major), SEC-P3FU86A-01 (minor).** A run whose `runs.environment` is not `recorded` was read as local. New `spectio.environments.read_as(column, settings)` applies the spec's Resume rule: `recorded` is the run's own snapshot, `not_recorded` the built-in of the server's kind (today's behaviour), `not_readable` and a run started from a terminal nothing. `failure.on_slurm` and `resume._slurm` read through it, so on a SLURM server a `not_recorded` run is asked of `sacct` and its copied command is the SLURM one with `--local-cores 2`. A `not_readable` run gets `command: null` and the existing reason `not_found` for its resources, never `local`; its jobs are never asked. Tests: `test_req18_snapshot_read_as`, `test_req18_snapshot_not_recorded_is_the_server_kind` (replaces `test_req18_snapshot_unknown_executor_is_not_slurm`, rewritten to the decided rule), `test_req18_snapshot_not_readable_has_no_command`; the docstrings of `test_eff_unavailable` and the `Run` helper say the `local` case is a `not_recorded` run on a local server.
- **SEC-P3FU86A-02 (minor).** `--local-cores 2` is now the last argument of every Snakemake SLURM launch, after `extra_args`, with a workflow profile too, so `extra_args` cannot lift it. Test: `test_snakemake_slurm_local_cores_last`; `test_snakemake_concurrency_without_a_profile` expects `extra_args` just before it.
- **CR-P3FU86A-04 (round 1) and the round 1 security finding.** `nextflow_config` passes partition and account through `slurm_name(...)` before `_groovy`, as the Snakemake path does. `test_nextflow_config_on_slurm` expects a `ValueError` for `lab'x` and `h'tc`.
- **CR-P3FU86A-04 (round 2).** `web/src/api.ts`: the `Run` schema comment is back directly above `export interface Run`.
- **CR-P3FU86A-03 (round 2).** A bad `[slurm]` value makes `Settings()` raise, and that stays. The `except ValidationError` branch of `environments._slurm` says that only a hand-built Settings reaches it.
- **CR-P3FU86A-05.** Recorded in inbox #133, no code change: 0.0.1 may hold one `environments` row per built-in kind, with runs referencing the oldest.

No API shape changed: the OpenAPI snapshot is unchanged.
