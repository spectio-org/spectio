# Spike: OpenAPI 3.1 draft for 0.0.1 (review round R6-contract)

- **Purpose.** Test whether `docs/specs/api-and-data-model.md` holds enough to write the 0.0.1 API contract, and list what is missing.
- **Scope.** Only the 0.0.1 cut (`dev-environment-and-testing.md` §15.1, `mvp-0.0.1.md` §2): workflows, launch, runs, tasks and logs, stages, events (SSE and engine ingest), relaunch with overrides, parameter history and lineage, and one-stage checks and gates. Auth mode is `single`: loopback without a token, bearer `spk_*` otherwise (api §6). Left out: pause/resume, manifest, change sets, artefacts, webhooks, summaries.
- **How it was made.** Written by hand from the specs. It reuses their names, fields and enums. Every path has `x-spec-ref`. Where the specs are silent or contradict each other, the draft writes the smallest guess and marks it `x-spec-gap`. It was checked with PyYAML and `openapi-spec-validator`, and both pass.
- **Throwaway.** This is not the contract and not product code. The findings go to `docs/reviews/R6-contract.md`.
- **x-spec-gap entries** (43 in `openapi.yaml`). The main themes:
  - Ingest: api §14, cited by architecture §12–§13, does not exist. Missing: batch envelope, how a batch names its run, ack body, version header, heartbeats, bridge auth.
  - SSE and events (§5, §8, §8.3): the coalesced delta is not in the catalogue; stream filters, `event:` name and the "task open" signal are missing; no per-type `data` schemas; `GET /events` envelope or table row is not said; `spectiosequence` type is open.
  - Stages, tasks, logs (§5, §7, §8.2, ui §3.1, §3.2): no stages endpoint or stage-state enum; a stage is an id or an index; no task or attempt state enum; which attempt a log is, runner offline, run log format.
  - Relaunch, params, lineage (§5, §7, ui §4.4, synthesis §5ter): new run or new launch is contradictory; `relaunch_mode` values and field names; params and lineage response shapes, "what changed".
  - Gates and checks (§4, §5, §7): no `run` filter; how 0.0.1 "relaunch with changed params" maps to a decision; missing If-Match and quorum rule; response body; checks shape and paging; `actor_kind` given as labels; `value` type.
  - Workflows and launch (§5, §7): no `POST /workflows` body, no `local` source, no name column; no default `environment_id`; `gates` values; `links` format.
  - Conventions and security (§4, §6, auth §1, §3): list envelope key, field-error shape, other ID prefixes, `limit` default, sortable fields, `Idempotency-Key` required or not, `:cancel` result; no Origin, Host or DNS-rebinding rule for token-less loopback.
