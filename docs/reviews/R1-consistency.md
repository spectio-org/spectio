# R1 · Consistency across specs

**Step page:** [R1](../progress/W1/R1.md)

**Round:** R1 (consistency) · **Date:** 2026-10-26 · **Found by:** spec-reviewer, four instances in parallel · **Status of the round:** triaged (TRIAGE1, 2026-10-27): 13 accepted, 0 rejected, 40 inbox (25 assumed) · triage: [TRIAGE1](../progress/W2/TRIAGE1.md) · APPLY1 (2026-10-27): 11 applied, 26 partly applied, 1 not applied

**Sources.**
- **Branch and commit:** `autopilot/integration` at `3b209d3`. Line numbers ("l.") refer to that commit.
- **Read:** every spec in [`docs/specs/`](../specs/synthesis.md), the decision log ([`log.md`](../decisions/log.md)), decision [0001](../decisions/0001-nextflow-through-nf-spectio.md), the [roadmap page](../roadmap/index.md), [`map.md`](../map.md) and [`next-phase.md`](../playbooks/next-phase.md).
- **Reviewer scopes:**
  - (a) [`synthesis.md`](../specs/synthesis.md) + [`ui-spec.md`](../specs/ui-spec.md);
  - (b) [`api-and-data-model.md`](../specs/api-and-data-model.md) + [`admin-and-operations.md`](../specs/admin-and-operations.md);
  - (c) [`architecture-plugins-and-packaging.md`](../specs/architecture-plugins-and-packaging.md) + [`cli-and-shared-libraries.md`](../specs/cli-and-shared-libraries.md) + [`dev-environment-and-testing.md`](../specs/dev-environment-and-testing.md);
  - (d) [`checking-scenarios.md`](../specs/checking-scenarios.md) + [`schedulers-and-monitoring.md`](../specs/schedulers-and-monitoring.md) + [`depictio-ecosystem-reuse.md`](../specs/depictio-ecosystem-reuse.md).

  Each reviewer also checked its scope against the decision log and the other specs.
- **Reviewer status:** all four reviewers returned output. None failed.
- **Renames checked:** maintainer→editor, agent→runner, Settings→Administration, spectio-runner merged into spectio, broker split into tasks/pubsub. Only the last three left leftovers (SR-039, SR-040, SR-049).
- **Earlier rounds:** findings already open in [R12](R12-ui-scenarios.md) (`UX-`) and [R8b](R8b-depictio-tooling.md) (`DEP-T-`) are cited, not repeated.

**Merge method** (review-round skill, steps 3-4):
- **De-duplication:** the four reviewers returned 82 findings (8 blockers, 50 majors, 24 minors as rated by them). Findings about the same problem were merged into one, crediting every reviewer, with the original IDs listed under "Found by". Where two reviewers rated the same problem differently, the higher rating was kept when the problem touches the 0.1 scope; the reason is given in the finding.
- **Verification:** every quoted passage of every blocker and major was opened at `3b209d3` and confirmed. All of them reproduced, so **0 findings were dropped**. Claims about other tools keep the reviewer's source, or are marked **[to be validated]**.
- **Ranking:** by severity, then by the number of documents the finding touches (specs, the decision log, decision 0001, the roadmap, map.md), shown in the findings table. The "five findings that matter most" are chosen on impact on 0.1, not on that count.
- **Proposed new sections:** where a finding proposes a new section, it uses a number that is free today. Several reviewers proposed the same number for different content (architecture §12), so this file assigns one number per topic:
  - api §7.1: run and gate state machines;
  - api §14: ingest contract;
  - architecture §7.7: runner protocol;
  - architecture §12: compatibility between components;
  - checking §12: `spectio.yml` reference;
  - dev-env §15: what ships in which stage;
  - ui-spec §11: component states.

Format: [`README.md`](README.md). Prefix `SR` (spec reviewer). Specs were not edited in this round.

## Summary

| Severity | Count |
|---|---|
| Blocker | 5 |
| Major | 33 |
| Minor | 15 |
| **Total** | **53** |
| Dropped (not reproducible) | 0 |

**The five findings that matter most:**
1. **SR-001: the engine → server ingest contract does not exist.** Decision 0001 removed Tower's `/trace/create`, and with it the only thing that gave an observed run its ID. Nothing defines the payload, the run handshake, the credential (no ingest scope exists) or the bridge behaviour when the server is down. Both engine plugins, spike T2 and the walking skeleton depend on it. Three of the four reviewers found it independently.
2. **SR-002: the runner ↔ server protocol has no owner and two transports.** api §5 says WebSocket; architecture §7.6, admin §3.2 and the log say outbound HTTPS pull. No command catalogue, ack or replay rule exists, and the runner credential either rotates or lives until revoked. Nothing can be launched without it.
3. **SR-003: check providers run on the server in three specs, on the runner in three others.** The logged rule is "only the runner reads files". The MVP is centred on checks, so this decides which package carries MultiQC, anndata and polars, and whether the 80 MB runner budget holds.
4. **SR-004: `spectio.yml` has four shapes and no owner.** Synthesis, checking §7, checking §11.2 and ui-spec §5.1 disagree on the gate ↔ stage link, the policy block and the evidence form. The parser, the overlay merge, `spectio workflow validate` and the 0.1 gate all need one schema.
5. **SR-007: phase labels do not map to release stages.** "1b" means four different things. Synthesis §9 still describes a tracking-only MVP, against the logged MVP scope. The WES facade has four dates (SR-010). P1 cannot cut the walking skeleton until dev-env §14 owns a "capability → stage" table.

SR-005 (two tables named `tasks`) is also a blocker: the first migration cannot be written. The fix, a rename, is mechanical.

## Findings table

| ID | Severity | Title | Documents touched |
|---|---|---|---|
| SR-001 | blocker | The engine → server ingest contract is undefined | 8 |
| SR-002 | blocker | Runner ↔ server protocol: no owner, two transports, two credential lifetimes | 8 |
| SR-003 | blocker | Check providers run on the server in three specs, on the runner in three others | 6 |
| SR-004 | blocker | `spectio.yml` has four shapes and no owner of its schema | 5 |
| SR-005 | blocker | `tasks` names two different tables, ID spaces and endpoint families | 4 |
| SR-006 | major | The CLI command tree lacks commands that other specs cite | 10 |
| SR-007 | major | Phase labels do not map to release stages, and the phase tables contradict each other | 7 |
| SR-008 | major | How Spectio drives Snakemake: Python API worker or command-line head job | 7 |
| SR-009 | major | Environment-variable and config-file names follow incompatible rules | 6 |
| SR-010 | major | The WES facade has four release dates and is under-specified | 6 |
| SR-011 | major | How a gate stops Nextflow: `--stage` parameter or generated `ext.when` | 6 |
| SR-012 | major | Gate decisions: five verb sets, two resource names, stale MCP tools and scopes | 5 |
| SR-013 | major | Endpoint catalogues duplicated between api §5 and admin §5; three public config endpoints | 5 |
| SR-014 | major | Which Unix account runs a launch on a group-owned environment is undefined | 5 |
| SR-015 | major | Background-task ledger and schedules: two schemas, two locking designs, no Jobs object | 5 |
| SR-016 | major | Run and gate states: five vocabularies, no enum, a 2-of-11 WES mapping | 4 |
| SR-017 | major | Engine bridge behaviour when the server is unreachable: Tower-era text and no testable bound | 4 |
| SR-018 | major | "Pause": immediate stop or after the current stage | 4 |
| SR-019 | major | Principal kinds: guests, plugin and bridge principals are outside the enum | 4 |
| SR-020 | major | The system-admin flag, protected groups and P.I. fields are missing from the schema | 4 |
| SR-021 | major | Launcher instances and Environments are two models of the same cluster | 4 |
| SR-022 | major | No compatibility window between CLI, runners, engine bridges, plugins and server | 4 |
| SR-023 | major | Gate checks depend on the depictio catalogue, but 0.1 has no depictio | 4 |
| SR-024 | major | Tokens are specified twice, differently | 3 |
| SR-025 | major | `launcher` and `reviewer`: rungs on a ladder or capability flags | 3 |
| SR-026 | major | Webhooks are both a project table and a notifier plugin instance | 3 |
| SR-027 | major | The base install's "nothing else" dependency rule is contradicted by the specs' own choices | 3 |
| SR-028 | major | The TypeScript client handles bearer tokens for the UI, which should use HttpOnly cookies | 3 |
| SR-029 | major | Project visibility has three values in the model and two in the UI | 2 |
| SR-030 | major | A restore rewinds the database under runs still executing; token handling is contradictory | 2 |
| SR-031 | major | Single-user mode trusts loopback, but loopback is shared on a login node | 2 |
| SR-032 | major | Built-in plugins are separate distributions, yet one `uv tool install spectio` is said to be enough | 2 |
| SR-033 | major | `on_fail: open_gate` creates a gate with no items, policy or deciders | 2 |
| SR-034 | major | schedulers §8 defines tables, events and endpoints the API spec does not have | 2 |
| SR-035 | major | Push transport needs an inbound Kafka consumer the architecture does not have | 2 |
| SR-036 | major | The `checks_as` preset shape requested from depictio does not match Spectio's check syntax | 2 |
| SR-037 | major | SLURM job names: the head-job pattern and the Snakemake join do not work as written | 1 |
| SR-038 | major | Maintenance mode does not say which writes still work | 1 |
| SR-039 | minor | "Settings" leftovers next to Administration, with a different grouping in api §11/§13.5 | 8 |
| SR-040 | minor | Stale names: agent for runner, `perspectio`, companion plugin, Duplicate | 6 |
| SR-041 | minor | Run and review screens are specified outside ui-spec; two cross-references are broken | 4 |
| SR-042 | minor | The built-in AI assistant has UI and a runner command but no API, data model or CLI entry | 4 |
| SR-043 | minor | "v1" means both the API path and a release; the API rule conflicts with 0.x semver | 4 |
| SR-044 | minor | Superseded merge and staging rules remain in dev-env, map.md and auth | 4 |
| SR-045 | minor | The event catalogue is incomplete, and gate notifications have two paths | 3 |
| SR-046 | minor | Pipeline identifier and workflow version key: `@` vs `/`, no column | 3 |
| SR-047 | minor | Fixture workflows and step numbers in dev-env disagree with the playbook and with §10.1 | 3 |
| SR-048 | minor | Untestable thresholds: "head silent" and the 10,000-file watch limit | 3 |
| SR-049 | minor | api §3 repeats the plugin-kind table with the stale "broker" kind and another engine contract | 3 |
| SR-050 | minor | The backup and restore contract differs between the CLI and admin specs | 2 |
| SR-051 | minor | Kubernetes RBAC differs between specs, and the Nextflow head pod has none | 2 |
| SR-052 | minor | Check-result vocabulary: `state` vs `verdict`, and how severity maps to them | 2 |
| SR-053 | minor | ui-spec contradicts the logged shell and list decisions without a new log entry | 2 |

## Blockers

### SR-001 · blocker · The engine → server ingest contract is undefined

- **Where:** no owner today. The natural owner is api-and-data-model.md (new §14 "Ingest contract", linked from §5). Touches api §2.D, §5, §6; authentication-and-access.md §3; ui-spec.md §4.4, §6; synthesis.md §2bis, §5ter.6, §9; architecture §4, §6; cli §2 (`engine`, `login`); dev-env §6; decision 0001.
- **Evidence:**
  - "`POST /ingest/events` (Nextflow plugin `nf-spectio`, Snakemake logger)" (api §5, l.102) is the only definition. It has no body, batching, response or error codes.
  - "A run started in a terminal with Spectio enabled is attached to the user's default project, or the project given by `SPECTIO_PROJECT`" (api §2.D, l.50). Nothing says how that run is created.
  - Tower's `/trace/create` returned the `workflowId` (synthesis §2bis, l.39). Decision 0001 removed the Tower routes without a replacement.
  - "with the Spectio run ID passed to `nf-spectio` by us (was `TOWER_WORKFLOW_ID` …)" (synthesis §5ter.6). No variable or config key is named.
  - "**Run token** | the run's life + 24 h | … | Issued to a provisioned run (§4) or an engine plugin; ingest only, for that run" (auth §3, l.104), against "a `spectio` config profile/env set once by `spectio login`" (ui-spec §6, l.196) and "one plugin to install, set once by `spectio login`" (0001, l.24). A credential set once at login cannot be a per-run token.
  - The scope list "`runs:read`, `runs:launch`, `gates:decide`, `gates:propose`, `artifacts:read`, `admin`" (api §6, l.155) has no ingest scope. Synthesis §9 (l.377) says "one ingestion token".
  - "`spectio-sdk` contains all interfaces, settings helpers, event schemas" (architecture §4, l.196; §6, l.232) names a package but defines no event.
  - "golden fixtures for `nf-spectio` events" (dev-env §6, l.141) have no schema to be checked against.
  - "`engine` | `nextflow config` (prints the `nf-spectio` plugin config for observed runs …)" (cli §2, l.54); `login` (cli §2, l.44) configures no engine.
  - "Logs … per-task stdout/stderr (fetched on demand through the runner)" (ui-spec §4.4, l.90) against "logs streamed by the engine plugin" (ui-spec §6, l.204).
- **Problem:** both engine bridges are needed in 0.1 ("both engines from the start", synthesis §9 l.386). Spike T2 only captures what the engines emit; nothing says what Spectio accepts. Implementers of `nf-spectio`, the Snakemake logger and `IngestAdapter` would each invent:
  - the envelope and its versioning;
  - how a batch names its run (Spectio run ID, Nextflow `sessionId` + `runName`, Snakemake run UUID);
  - who creates the run for an observed (terminal-started) run, and which credential the plugin uses before a run token can exist;
  - how the runner hands the run ID and token to the engine for a driven run;
  - the response, backpressure and batch limits;
  - whether task logs travel over ingest or through the runner.
- **Proposal:** add api §14 "Ingest contract" as the single owner. The reviewers converge on:
  - **Envelope:** `{schema_version, run_id | client_run_key, events: [{event_id (ULID, idempotency per synthesis §4), seq, ts, engine, engine_version, type, payload}]}`, with the raw engine payload kept. The JSON Schema is published from `spectio-sdk`, and both bridges and T2 golden fixtures validate against it.
  - **Run handshake:** a create-or-attach call (`POST /ingest/runs`, or a first `run.started` event) that returns `run_id`. It is idempotent on (engine, Nextflow `sessionId` + `runName` or Snakemake run UUID, host, launch directory) and creates a `cli-observed` run in the default or `SPECTIO_PROJECT` project.
  - **Driven runs:** the runner passes `SPECTIO_URL`, `SPECTIO_RUN_ID` and `SPECTIO_RUN_TOKEN` (names to fix once); the run token stays "ingest only, for that run".
  - **Observed runs:** a personal token with a new ingest scope, written by a named command (for example `spectio engine nextflow config --install`). The reviewers proposed three names (`runs:ingest`, `runs:report`, `ingest:create`); pick one and register it in auth §3, which owns scopes (SR-024).
  - **Batching and errors:** at most 1,000 events or 1 MB per POST (proposed); response `{run_id, accepted, duplicates, rejected, acked_through}`; `429`/`503` with `Retry-After`.
  - **Logs:** state whether task logs travel over ingest or only through the runner, and fix ui-spec §4.4 / §6 to match.
  - **Bridge behaviour** when the server is down is in this section too (SR-017).

  Then align synthesis §5ter.6, ui-spec §6, cli §2 and 0001 (see also SR-006 for the enabling commands). Related, not duplicates: UX-116 (Tower payload for terminal runs, R12).
- **Found by:** spec-reviewer (a) SR-101, (b) SR-205, (c) SR-301
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-002 · blocker · Runner ↔ server protocol: no owner, two transports, two credential lifetimes

- **Where:** architecture §7.6 vs api-and-data-model.md §5 and §6 vs admin-and-operations.md §3.2, §3.4, §5 vs authentication-and-access.md §3; also synthesis §7quater, checking-scenarios §11.1 and §11.3, ui-spec §4.8, decision log 2026-10-25.
- **Evidence:**
  - "runner channel `WS /runners/{id}/channel` (commands, heartbeats, file streaming)" (api §5, l.92).
  - "**Commands to runners**: launch, cancel, resume | … | runner pulls over outbound HTTPS (long poll or SSE)" (architecture §7.6, l.385). "Commands to runners are pulled over HTTPS, not brokered" (log, l.136).
  - "**Commands are pulled, never pushed** (launch, cancel, "Run diagnostics"). The server records the request and the runner claims it" (admin §3.2, l.146); "`POST /runners/{id}/diagnostics` (pulled by the runner)" (admin §5, l.334); "runners ship their daemon logs over HTTPS in batches" (admin §3.4, l.161).
  - "It opens an **outgoing** …" WebSocket, "same principle as Seqera's Tower Agent" (synthesis §7quater, l.339). The Tower Agent claim is unsourced **[to be validated]**.
  - Commands the specs need but never list: "`S->>R: evaluate check(s) on path`" and `check.evaluated` (checking §11.1, l.278); "a stop file the runner writes" (checking §11.3); directory listing (UX-117); log range reads; drain.
  - Credential: "a one-time registration token becomes a rotating runner credential" (api §6, l.155) vs "**Runner token** | until revoked" (auth §3, l.103).
  - Offline: decisions "queued and applied on reconnect" (ui-spec §4.8, l.137; log 2026-10-25).
- **Problem:** launch, cancel, file streaming for viewers (`GET /artifacts/{id}/content`), `check.evaluated`, stop files, logs and heartbeats all go through this protocol, and it is on the critical path of the 0.1 walking skeleton. Five things are open:
  - the transport (WebSocket, or HTTPS long-poll / SSE), which matters behind HPC proxies and SSH tunnels (synthesis §8);
  - the command catalogue and the result path (`check.evaluated` has no ingestion route; `/ingest/events` is for engines);
  - claim, lease, ack, ordering and idempotency;
  - how file bytes are streamed (long poll alone cannot stream large files back);
  - offline semantics: what happens to pending evaluations, and to a `pause_after_stage` stop file that cannot be written (the run then continues past the boundary).

  R12 UX-117 (list_dir) and UX-124 (token lifetimes) cover only pieces of this. Rated blocker by reviewer (c), major by (a), (b) and (d); kept as blocker because no launch can be built without it.
- **Proposal:**
  - Add architecture §7.7 "Runner protocol" as the owner; api §5, admin §3.2 and checking §11 link to it.
  - **Transport:** the reviewers split. (b) and (c) recommend a runner-initiated WebSocket over 443 with HTTPS long-poll and chunked upload as fallback; (d) recommends HTTPS long-poll claim, as in admin §3.2, and removing the WS route. Either way, keep one primary transport. Whether EMBL proxies block WebSocket upgrades is **[to be validated at EMBL]**. Question for Thomas.
  - **Commands:** a typed catalogue (`run.launch`, `run.cancel`, `run.resume`, `stage.stop_after`, `check.evaluate`, `fs.list`, `fs.read_range`, `diagnostics`, `drain`), each with `command_id`, run, idempotency key, deadline and lease; ack and result messages (or `POST /runners/{id}/results`); at-least-once delivery.
  - **Heartbeat and offline:** heartbeat interval and the offline rule (3 × 30 s, as in admin §3.2); queued commands and evaluations are replayed on reconnect; a missed `pause_after_stage` shows a warning on the run.
  - **Credential:** settle on rotating (api §6) and fix auth §3, or the reverse.
- **Found by:** spec-reviewer (a) SR-110, (b) SR-213, (c) SR-302, (d) SR-406
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-003 · blocker · Check providers run on the server in three specs, on the runner in three others

- **Where:** owner checking-scenarios.md §11.1. Conflicts with architecture §2, §3.6, §6, §7.3, §7.6; api-and-data-model.md §3; admin-and-operations.md §3.1. Agrees with api §13.6 and the log 2026-10-26.
- **Evidence:**
  - Server side: "Check provider | `spectio.check` | server | multiqc, table, json" (architecture §2, l.45); "Check provider | server | … | file → item × metric table for gate checks" (api §3, l.64); the architecture §6 diagram lists "Runner-side plugins: engine, launcher, resolver, secrets" (l.277), so `check` is server-side; `class CheckProvider: def evaluate(self, files, check_spec)` (architecture §3.6, l.187); "evaluate gate checks" is a server background task (architecture §7.6, l.384); task kind `check.evaluate` (admin §3.1, l.134).
  - Runner side: "**The runner is the only component that reads files.** … The server never mounts storage" (checking §11.1, l.261); "computed once, by the runner at gate time" (api §13.6, l.346); "only the runner reads files, and only values travel" (log, l.299).
  - Footprint: the runner base install has "no compiled dependencies" (architecture §7.3, l.335) and must stay "< 80 MB environment, CI-checked" (cli §6, l.170). The bindings need `multiqc -m <module> <file>` (checking §11.2), h5ad readers and `bcftools stats` (checking §7), and polars for depictio recipes ([`depictio-qc-integration-2026-10-26.md`](../research/depictio-qc-integration-2026-10-26.md) §4).
- **Problem:** the MVP's focus is checks and quality control (log 2026-10-26). An implementer following architecture §2 or api §3 would build check plugins that run on the server and cannot reach the files. The placement also decides which package depends on MultiQC, anndata or polars, the import-linter rules in architecture §6, and whether `check.evaluate` is a server task or a runner command.
- **Proposal:**
  - Settle it in checking §11.1, the owner: the **source binding** (file → values) runs on the runner; the **verdict** (values × thresholds → outcome) runs on the server, so a threshold change in an overlay re-evaluates without reading files again.
  - Architecture §2: "Runs on: runner" for `spectio.check`; §6: move `check` to the runner-side plugins and the dependency rules; §3.6: `evaluate(files, check_spec, ctx)` returns values.
  - Admin §3.1: redefine `check.evaluate` as "dispatch to a runner and wait for `check.evaluated`" (or rename it `check.dispatch`).
  - Ship heavy bindings as an extra (`spectio[checks]`) or as separate check plugins so the 80 MB budget holds, and state which extra 0.1 needs (see SR-027).
  - api §3 links to architecture §2 instead of restating the table (SR-049).
- **Found by:** spec-reviewer (b) SR-202, (c) SR-303, (d) SR-401
- **Status:** partly applied (APPLY1, 2026-10-27): admin §3.1; architecture §2, §6, §7.3; checking-scenarios §11.1 (assumed — pending Thomas, inbox #28); pending: architecture §3.6 `CheckProvider` signature and §7.6 'evaluate gate checks' (inbox #25); footprint of `spectio[checks]` (spike runner-footprint)

### SR-004 · blocker · `spectio.yml` has four shapes and no owner of its schema

- **Where:** no owner today. Shapes in synthesis.md §5ter.1; checking-scenarios.md §7 and §11.2; ui-spec.md §5.1, §9; api-and-data-model.md §6 and §13.3. Consumers in cli §2.
- **Evidence:**
  - **Gate ↔ stage link:** `gates: <id>: … after_stage: align` (checking §7, l.157) vs `stages: - id: align … gate: false # a gate stays optional (§7)` (checking §11.2, l.300) vs "`stages` (id, name, `match` globs …, optional `gate`, …)" (ui-spec §5.1, l.187).
  - **Stage → engine mapping:** `snakemake: { until: [qc_report] }` and `nextflow: { params: { stage: preprocess } }` (synthesis §5ter.1, l.208) vs `match` globs (checking §11.2, ui-spec §5.1).
  - **Policy:** `intervention: { type, evidence, params_schema, policy: { mode: agent_proposes_human_confirms, timeout: 48h, on_timeout: stop } }` (synthesis §5ter.1, l.212-213) vs `decide: {item_actions, per_item, rules, constraints, humans, agents}` (checking §7) vs "`decide` (auto_approve, humans, agents: propose | approve | none, timeout)" (ui-spec §5.1, l.187).
  - **Evidence:** a list of globs under `intervention` (synthesis) vs `evidence: - { kind: report, per_item: true, path: … }` (checking §7, l.172).
  - **Other keys:** `depictio:` (api §13.3), a Snakemake `ui:` block ("draft its format alongside `spectio.yml`", ui-spec §9, l.253), and `workflow`, `reports`, `launch` (ui-spec §5.1), defined nowhere else.
  - **Consumers:** `workflow validate spectio.yml` (cli §2, l.49) and `run launch --gates spectio.yml` (cli §2, l.47).
- **Problem:** the parser, the overlay merge rules ("can add watches, never remove an author's `block` check", checking §11.1), the CLI validator and the `WorkflowOverlay` board would each follow a different source. ui-spec also duplicates content, against the one-owner rule. Rated blocker by (d) and major by (a); kept as blocker because the 0.1 gate is defined in this file.
- **Proposal:**
  - Add checking-scenarios §12 "`spectio.yml` reference" as the single owner, backed by a JSON Schema in `spectio-sdk` that `spectio workflow validate` uses.
  - Choose **one** gate ↔ stage link. (d) recommends `stages[].gate: <gate_id>` and dropping `after_stage`; (a) only asks for one. Decide at triage.
  - One policy block (`decide.humans / agents / auto_approve / timeout / on_timeout`), the object form of `evidence`, the keys of each check kind (SR-036), the `depictio:` and `ui:` keys, and the overlay merge rules.
  - Synthesis §5ter.1 gets a "superseded" note; ui-spec §5.1 keeps only "where stages come from"; api §6 and §13.3 link to §12.
- **Found by:** spec-reviewer (a) SR-107, (d) SR-402
- **Status:** partly applied (APPLY1, 2026-10-27): api §13.3; checking-scenarios §12 (new, §12.1–§12.7); cli §2; synthesis §5ter.1; ui-spec §5.1, §9 (assumed — pending Thomas, inbox #29); pending: api §6 gate-policy sentence (inbox #13, #14, #15); checking §7 example keys (inbox #16, #19); overlay precedence (inbox #19); tool: JSON Schema in `spectio-sdk` and `spectio workflow validate`

### SR-005 · blocker · `tasks` names two different tables, ID spaces and endpoint families

- **Where:** api-and-data-model.md §5 and §7 vs admin-and-operations.md §3.1, §3.4, §4.3, §5; architecture §7.2 and §7.6; depictio-ecosystem-reuse.md §1.1.
- **Evidence:**
  - Engine tasks: "`tasks`, `attempts`, `scheduler_jobs`, `attempt_jobs` | run_id, process_or_rule, stage, tag …" (api §7, l.224); "`GET /runs/{id}/tasks`, `GET /tasks/{id}`, `GET /tasks/{id}/attempts`" (api §5, l.94).
  - Background ledger: "The `tasks` table is the source of truth whatever the backend" (admin §3.1, l.121) with "`id` (`task_…`), `kind`, `queue`, `priority`" (l.127); "**New tables.** These extend [api] §7: `tasks`, `schedules` …" (admin §5, l.344-345); "`tasks(id, kind, project_id, created_by, state: queued|running|…`" (architecture §7.6, l.391); "`tasks` table + jobs view" (reuse §1.1, l.45).
  - Spill-over: "Logs and task ledgers (derived or self-expiring data)" are excluded from backups (admin §4.3, l.248); `log_records` has a `task_id` field (admin §3.4, l.164).
- **Problem:** the first Alembic revision cannot hold two tables with one name and incompatible columns. The ambiguity spreads:
  - read literally, excluding "task ledgers" from a backup drops every run's engine tasks;
  - `log_records.task_id` and the `task_…` prefix are ambiguous;
  - `GET /tasks/{id}` vs `GET /admin/tasks/{id}`, `spectio run tasks` vs `spectio admin tasks`;
  - "jobs" also clashes with `scheduler_jobs`.

  Rated blocker by (b), major by (d). Kept as blocker because the schema cannot be created; the fix is a mechanical rename.
- **Proposal:**
  - Keep `tasks` / `attempts` and `task_` for engine tasks: they match synthesis §2ter/§4, WES `/tasks` and the UI Tasks tab.
  - Rename the ledger `background_tasks`, prefix `btask_`, API `/admin/background-tasks`, UI label "Background tasks".
  - Define the user-facing "Jobs" as a view (`created_by = caller`) with no table of its own; see SR-015 for tying it to the api §4 `Operation`.
  - Split `log_records.task_id` into `engine_task_id` and `background_task_id`.
  - Update architecture §7.2/§7.6, admin §3.1/§4.3/§5 and reuse §1.1.
- **Found by:** spec-reviewer (b) SR-201, (d) SR-407
- **Status:** partly applied (APPLY1, 2026-10-27): map (reading order 8); admin §1, §3.1, §3.4, §4.3, §5; api §5; architecture §7.2, §7.6; cli §2; ui-spec §2, §4.9 (assumed — pending Thomas, inbox #29); pending: depictio-ecosystem-reuse §1.1 (inbox #26); boards AdminTasks and AdminNav labels → 'Background tasks'

## Majors

### SR-006 · major · The CLI command tree lacks commands that other specs cite

- **Where:** cli-and-shared-libraries.md §2 vs api-and-data-model.md §6; depictio-ecosystem-reuse.md §2.1; authentication-and-access.md §2; ui-spec.md §6; architecture §7.2; schedulers-and-monitoring.md §6; admin-and-operations.md §0.2, §5; decision 0001; log 2026-10-25.
- **Evidence:** the CLI "covers the whole API" (cli §0.1, l.12) and "Nothing an admin can do is UI-only" (admin §0.2, l.16). These are cited elsewhere and missing from cli §2:
  - `spectio auth enable oidc --issuer …` (api §6, l.163). Auth §1 treats OIDC as a method, not a mode.
  - `spectio user import --from depictio` (reuse §2.1, l.128); cli §2 `user` has only `list, create, deactivate, set-admin` (l.56).
  - `spectio login --print-link` (auth §2, l.66).
  - `spectio run nextflow …` / `spectio run snakemake …` (ui-spec §6, l.198), and `login` writing engine config ("set once by `spectio login`", ui-spec §6 l.196, 0001 l.24). cli §2 has `run launch|list|show|…|adopt|watch` and `engine nextflow config`, and `login` (l.44) writes no engine config.
  - `spectio serve --tls` (architecture §7.2, l.317).
  - `spectio ai serve` (log, l.110; ui-spec §4.9).
  - The foreground daemon command that `spectio-runner@.service` executes (schedulers §6, l.208). `runner` has only `connect, status, list, drain, logs` (cli §2, l.46).
  - Plugin-instance management, announcements, log capture level (admin §5), share links (auth §2).
- **Problem:** implementers of the CLI, the systemd unit and the onboarding docs have nothing to wire, and there are three inconsistent ways to enable Spectio on a terminal run.
- **Proposal:**
  - Add these commands to cli §2. Name OIDC `auth method enable oidc`.
  - For terminal runs, cli §2 owns the choice: either add `run nextflow|snakemake -- <args>` and a `login --configure-engines` option, or drop them from ui-spec §6 and 0001 in favour of `engine nextflow config --install` / `engine snakemake profile --install`. ui-spec §6 links to the result; the credential follows SR-001.
  - Add a CI check that every admin OpenAPI operation maps to a CLI command.
- **Found by:** spec-reviewer (a) SR-115, (c) SR-313, (d) SR-418 (CLI part)
- **Status:** partly applied (APPLY1, 2026-10-27): cli §2, §6; ui-spec §6 (assumed — pending Thomas, inbox #28); pending: api §6 `spectio auth method enable oidc` (inbox #13, #14, #15); share-link CLI commands (inbox #18, #19); ingest credential written by `login` (inbox #11); CI: admin-operation → CLI-command test

### SR-007 · major · Phase labels do not map to release stages, and the phase tables contradict each other

- **Where:** synthesis.md §7quinquies and §9; architecture §9; schedulers-and-monitoring.md §11; api-and-data-model.md §5, §10; ui-spec.md §4.9; dev-environment-and-testing.md §7.4 and §14 (owner of release stages, per synthesis §9); decision log 2026-10-26 ("MVP scope").
- **Evidence:**
  - Synthesis §9 table: "**1 (MVP)** | Snakemake agent …" (l.377), "**1b** | Nextflow agent (V2 plugin) …", "**1c** | … QC gates". The same section says "The MVP covers **both engines from the start**" (l.386), then "I propose to **start with read-only tracking of both engines**, then add steering (phase 1c)" (l.391).
  - The 0.1 entry condition is "launch, observe, check, gate, resume" (dev-env §14, l.421).
  - "1b" means "Nextflow agent, `sacct`" (synthesis §9), "RO-Crate export and import, WES facade" (synthesis §7quinquies, l.321), "instances and scopes …, OIDC, SQL task workers on Postgres, backup and restore, sinks (RO-Crate, depictio)" (architecture §9, l.437) and "capacity (L4), quotas, reservations, pre-flight" (schedulers §11).
  - OIDC: "phase 2" (api §10; synthesis §9) vs 1b (architecture §9). Postgres: "**3** | Postgres, WES facade, …" (synthesis §9, l.381) vs Postgres task workers in 1b and Postgres in the Compose `team` profile (architecture §9, §7.4).
  - Kubernetes: schedulers §11 MVP has "head Job, watch, pod reasons and OOMKilled"; architecture §2 lists built-in launchers "local, slurm" (l.42) with `kubernetes` optional, and no row of architecture §9 lists the Kubernetes launcher; the Helm chart is phase 2 (l.438). The 1.0 gate requires "Nextflow and Snakemake on SLURM and on Kubernetes" (dev-env §14, l.429), and the public instance uses the Helm chart at the beta (dev-env §7.4).
  - Kafka: phase 2 (schedulers §11) vs phase 3 (architecture §9, l.439).
  - Architecture §9 puts "sinks (… depictio)" in 1b; the log says "automatic hand-off to depictio comes later, not in 0.1" (l.318).
  - MCP: "MCP or REST" is the MVP default for agents (ui-spec §4.9, l.148); no phasing table lists MCP.
- **Problem:** two calendars (MVP/1b/1c/2/3 and 0.1/alpha/beta/1.0) with no mapping, and feature lists that contradict each other. The closing sentence of synthesis §9 still describes a tracking-only MVP, against the logged MVP scope. P1 cannot cut the walking skeleton, and P2 milestones cannot place features.
- **Proposal:**
  - Add dev-env §15 "What ships in which stage": one capability × stage table (0.1, alpha 0.2-0.4, beta 0.5-0.9, 1.0, unscheduled), the single owner. Cover at least: engines, launchers (local, SLURM, Kubernetes), Postgres, Compose, Helm, OIDC/SAML, MCP, WES (SR-010), embedded elements, depictio hand-off, TRS/DRS, Kafka, capacity/pre-flight, background-task kinds (SR-043).
  - Synthesis §7quinquies and §9, architecture §9 and schedulers §11 either rename their rows to stages or are marked "historical (23/10)" with a link. Strike the closing sentence of synthesis §9.
  - api §5 gets a "From" column; api §10 links to the table.
  - Reviewer recommendations to settle at triage: local + SLURM in 0.1; Kubernetes launcher, Postgres, Compose and OIDC in the alpha; Helm in the beta; depictio sink after 0.1; Kafka unscheduled (SR-035).
- **Found by:** spec-reviewer (a) SR-103, (b) SR-203 (partly), (c) SR-305, (d) SR-412 (partly)
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-008 · major · How Spectio drives Snakemake: Python API worker or command-line head job

- **Where:** synthesis.md §2, §5ter.3, §5ter.6; ui-spec.md §4.6, §5.1, §6; architecture §3.6; dev-environment-and-testing.md §10.1; cli-and-shared-libraries.md §6; schedulers-and-monitoring.md §3.1; decision log (technical constraints).
- **Evidence:**
  - "**Clean steering**: one Python worker per run that calls the API (`SnakemakeApi`, `DAGSettings(until=…)`, `ConfigSettings`) rather than a `subprocess` on the CLI" (synthesis §2, l.29); "Snakemake launches the stage with `DAGSettings(until=[…])` via the Python API" (synthesis §5ter.3, l.230). The log's constraint: "**no** ad hoc log parsing or Python `subprocess` that would degrade the UX" (log, l.78).
  - "Snakemake — `--until` the last rules of the stage; Continue drops `--until`; rerun from a stage uses `--forcerun`" (ui-spec §5.1, l.189); "Snakemake: `--until qc_report` … then a plain rerun" (dev-env §10.1, l.262).
  - "`def plan(self, launch: LaunchSpec) -> ExecutionPlan  # command, env, generated config`" (architecture §3.6, l.174); `submit(plan) -> Handle # local process, sbatch, Kubernetes Job…` (l.180).
  - On HPC "the engine's head process is run as a **head job**: `sbatch` …" (schedulers §3.1, l.64).
  - The runner is "`uv tool install spectio` | CLI + Python client + runner" (cli §6, l.170) in its own environment, not in the workflow's Snakemake environment.
- **Problem:** the two designs differ in process model, in which Snakemake version runs (the runner's or the workflow's) and in how to stop (API call vs SIGINT). The API worker would have to run inside the user's Snakemake environment, in the head job, which no spec describes. The CLI route breaks the logged "no subprocess" constraint as worded.
- **Proposal:** Thomas picks one. Reviewer (a) recommends a CLI head job, which matches the boards, the synthetic suite and `ExecutionPlan.command`. Record the choice in the log, revise synthesis §2, §5ter.3 and §5ter.6, and restate the constraint as "no parsing of process output for tracking".
- **Found by:** spec-reviewer (a) SR-106
- **Status:** applied (APPLY1, 2026-10-27): synthesis §2, §5ter.3, §5ter.5, §5ter.6 (merged with CH-009); choice recorded in decisions/log.md (APPLY1 entry) (assumed — pending Thomas, inbox #28)

### SR-009 · major · Environment-variable and config-file names follow incompatible rules

- **Where:** architecture §0.4, §3.2, §7.3; cli §3; api-and-data-model.md §13.1; authentication-and-access.md §1; admin-and-operations.md §4.1, §4.3; telemetry-and-analytics.md §0.4.
- **Evidence:**
  - "`SPECTIO_NOTIFIER_MATTERMOST_WEBHOOK_URL`" with config table `[notifier.mattermost.<instance>]` (architecture §3.2, l.126).
  - "`SPECTIO_*` env vars, with `__` for nesting" (architecture §7.3, l.339).
  - "switched by `DATABASE_URL`" (architecture §0.4, l.13), with no prefix.
  - Flat names elsewhere: `SPECTIO_AUTH_MODE` (auth §1, l.39), `SPECTIO_AUTH_PUBLIC_ACCESS_CODE`, `SPECTIO_BRANDING_PRESET` (admin, l.211), `SPECTIO_BACKUP_*`, `SPECTIO_TELEMETRY_ENABLED` (telemetry, l.32), `SPECTIO_EXTRA_PLUGINS`.
  - CLI config: `~/.config/spectio/servers.yaml` (cli §3, l.106) vs "`~/.spectio/config.yaml`, `SPECTIO_*`" (api §13.1, l.297).
- **Problem:** with pydantic-settings and `__` nesting, none of the flat names resolve. The plugin env var has no slot for a tagged instance. Two CLI config paths are documented.
- **Proposal:** architecture §7.3 states one rule:
  - flat `SPECTIO_<AREA>_<FIELD>` names through explicit aliases, since they are already user-facing in six specs;
  - `DATABASE_URL` accepted as an alias of `SPECTIO_DATABASE_URL`;
  - plugin env vars set only the default (untagged) instance, as Snakemake does; tagged instances come from the file or the UI;
  - api §13.1 points to cli §3 for the CLI file.
- **Found by:** spec-reviewer (c) SR-309
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §0 item 4, §7.3; pending: api §13.1 CLI config row → cli §3 (inbox #21); architecture §3.2 derived-forms table (inbox #25; covered by the §7.3 rule)

### SR-010 · major · The WES facade has four release dates and is under-specified

- **Where:** synthesis.md §7quinquies, §9, §11 Q5; docs/roadmap/index.md; api-and-data-model.md §0, §1, §2.B, §5, §7, §10; ui-spec.md §4.1; architecture §6, §9; log 2026-10-26.
- **Evidence:**
  - "Phase 1b: RO-Crate export and import, WES facade" (synthesis §7quinquies, l.321).
  - "**3** | Postgres, WES facade, …" (synthesis §9, l.381).
  - "Is a WES facade needed from the MVP, or later?" is still open (synthesis §11, l.409).
  - "GA4GH WES and TES interfaces" under "Ideas, not scheduled" (roadmap, l.42).
  - With no phase: "the MCP server, the WES facade … are all clients of the same public API" (api §0.1, l.8); "Headless | … only API, WES, webhooks, MCP" (api §1, l.20); "Facades | `/ga4gh/wes/v1/*` (WES 1.1 + `x-spectio` extensions)" in the "Endpoint catalogue (v1)" (api §5, l.103); api §10 gives TRS/DRS "phase 2" (l.265) and WES no phase; `runs.origin` already includes `wes` (api §7, l.222); "API: REST, SSE, WES, MCP, ingest" (architecture §6 diagram, l.267), with no WES row in architecture §9.
  - The public landing page has a "works-with strip (… GA4GH WES)" (ui-spec §4.1, l.72).
  - "When the WES facade ships is inconsistent across docs … That is left to review R1" (log, l.326).
  - Under-specification: "Spectio maps it to a native run in the caller's default project" (api §2.B, l.44), but a WES `RunRequest` has no field for Spectio's required `environment_id` (WES 1.1.0 schema, ga4gh/workflow-execution-service-schemas, **[to be validated]**). The `workflow_type` values `NFL` / `SMK` are **[to be validated]** against Sapporo's `service-info` (https://github.com/sapporo-wes/sapporo-service).
- **Problem:** P1 cannot decide whether `/ga4gh/wes/v1` is in the walking skeleton; an implementer reading api §1 or architecture §6 would build it into the first server. The landing page would advertise an interface that the roadmap calls unscheduled.
- **Proposal:**
  - Thomas picks one stage, recorded once in the dev-env §15 table (SR-007). Reviewer recommendations differ: public beta (0.5-0.9) with `service-info`, `POST/GET /runs`, `/status`, `/cancel`, `/tasks`, and `x-spectio` gate extensions later ((a), (c)); before the public beta ((b)); unscheduled until a design partner needs it ((d)). All agree: **not in 0.1**, because LabID and design partners use the native API.
  - Replace the two synthesis phase cells with a link and close §11 Q5; move the roadmap item to that stage (TES stays under Ideas); mark api §0, §1, §5, §10 and architecture §6/§9 "from `<stage>`" (or "when enabled").
  - Drop "GA4GH WES" from the landing strip until it ships.
  - When the facade is specified, api §2.B says how the environment is chosen (`workflow_engine_parameters.spectio_environment`, or a per-token default).
- **Found by:** spec-reviewer (a) SR-102, (b) SR-203, (c) SR-304, (d) SR-412
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-011 · major · How a gate stops Nextflow: `--stage` parameter or generated `ext.when`

- **Where:** synthesis.md §5bis, §5ter.1, §5ter.3, §5ter.5; ui-spec.md §4.6, §5 vs §5.1; checking-scenarios.md §11.3; architecture §3.6; dev-env §3, §10.1; log 2026-10-25 "UI review round 2".
- **Evidence:**
  - "Nextflow launches with the `--stage` parameter, and the pipeline tests `params.stage` in its `workflow` block … **the pipeline must cooperate**" (synthesis §5ter.3, l.231); `nextflow: { params: { stage: preprocess } }` (§5ter.1, l.208); "next `--stage`" (§5ter.5, l.243); "`--stage` parameter for Nextflow" (§5bis, l.187).
  - "Nextflow: stages through a `stage` parameter" (ui-spec §5, l.181) vs "Nextflow — a generated config sets `ext.when = false` on the processes of later stages (nf-core modules honour `task.ext.when`)" (ui-spec §5.1, l.189).
  - "Gates stop Nextflow via a generated `ext.when = false` config" (log, l.108); architecture §3.6 (l.174, "gates → ext.when / --until"), dev-env §3 (l.88) and §10.1 (l.261) and checking §11.3 (l.323) agree with the log. checking §11.3 cites synthesis §5ter for this mechanism, which describes the other one.
  - Rerun from a stage: "Forcing a specific stage requires a 'salt' parameter … **[to be validated]**" (synthesis §5ter.5) vs "Nextflow stage override + `-resume`" (ui-spec §4.6, l.122). Neither is specified.
- **Problem:** synthesis comes first in the reading order and still requires pipelines to cooperate through `params.stage`, which unmodified nf-core pipelines do not do. ui-spec contradicts itself. An implementer of `Engine.plan` could build either mechanism, and rerun-from-stage has no Nextflow mechanism at all.
- **Proposal:**
  - Record `ext.when` as the only Nextflow boundary (unconditional for gates; the stop-file closure for live checks), owned by checking §11.3 or the new checking §12 (SR-004).
  - Add a "Revised on 25/10 (log)" note to synthesis §5bis, §5ter.1, §5ter.3 and §5ter.5, as was done for decision 0001; fix the ui-spec §5 bullet to "stages from `match` globs, stopped by a generated `ext.when` config (§5.1)".
  - The claim that nf-core modules honour `task.ext.when` needs a source (nf-core modules template, file:line) or **[to be validated]**.
  - Specify rerun-from-stage for Nextflow, for example a generated per-process `ext` key that enters the task hash, **[to be validated]** in spike T2.
- **Found by:** spec-reviewer (a) SR-105, (d) SR-403
- **Status:** applied (APPLY1, 2026-10-27): checking-scenarios §11.3, §12.3; synthesis §5, §5bis, §5ter.1, §5ter.3, §5ter.5; ui-spec §4.6, §5, §5.1

### SR-012 · major · Gate decisions: five verb sets, two resource names, stale MCP tools and scopes

- **Where:** owner checking-scenarios.md §5. Also synthesis.md §5, §5bis, §5ter.2, §7bis; api-and-data-model.md §5, §6, §7; ui-spec.md §2, §4.5; cli-and-shared-libraries.md §2.
- **Evidence:**
  - Checking: "Gate | approve · stop · go back to a stage · reassign · wait for a signal" (checking §5, l.114), with item verbs "keep · exclude · redo · flag · replace input".
  - api: "`POST /gates/{id}/decisions` (approve, apply, go back, stop …)" (api §5, l.96); `POST /gates/{id}/signals` (api §2, l.53); scopes `gates:decide`, `gates:propose` (api §6, l.155); `/mcp` with no tool list (api §5); `decisions.action` and `gates.state` with no values (api §7).
  - Synthesis: `POST /interventions/{id}/signal` (§5bis, l.181); MCP tools `list_interventions`, `get_intervention`, `propose_decision`, `submit_decision` (l.176); scope `interventions:resolve` (§7bis, l.280); decisions `continue`, `params_changed`, `rerun_all` (l.223), `reject` → `STOPPED` (§5ter.2); lifecycle `pending → awaiting_review → approved | rejected | params_changed` (§5, l.140); modes `human_only`, `agent_proposes_human_confirms`, `agent_auto`, `system` (§5bis, l.168).
  - ui-spec: "approve / change params / rerun / reject" (§2, l.21) vs "Approve and continue / Apply and continue / Discard changes; More: go back, stop the run here, reassign" (§4.5, l.111).
  - CLI: "`decide <gate> --approve|--reject|--hold`" (cli §2, l.48).
- **Problem:** the `decisions.action` CHECK values, the `gates.state` values, the MCP tool names, the token scopes and the CLI flags cannot be derived from the specs. `reject` and `hold` (CLI), `rerun_all` (synthesis) and `apply` (api) map to nothing. `reassign` and "wait for a signal" are listed as decisions but change no run state.
- **Proposal:**
  - checking §5 stays the owner and enumerates `decisions.action`: `approve` (continue unchanged), `apply` (continue with the change set), `go_back` (+ stage), `stop`. `reassign` and `wait` become gate operations, not decisions.
  - api §5/§7 own the `decisions.action` and `gates.state` enums (with SR-016) and the MCP tool list, named after gates (`list_gates`, `get_gate`, `propose_decision`, `decide_gate`).
  - cli §2 becomes `decide <gate> approve|apply|stop|go-back --stage S` with `--keep/--exclude/--redo/--flag` item options and `--rule`; `--reject` maps to `stop`, `--hold` is dropped or defined.
  - Synthesis §5/§5bis/§5ter/§7bis get "Intervention = Gate; names superseded by api §5"; `interventions:resolve` becomes `gates:decide`. ui-spec §2 uses the same verbs.
  - Related, not duplicates: UX-106, UX-107 (more verbs), UX-110 (waiting for a signal), R12.
- **Found by:** spec-reviewer (a) SR-109, (c) SR-312, (d) SR-404
- **Status:** partly applied (APPLY1, 2026-10-27): api/index.md; api §5, §7; cli §2; synthesis §5, §5bis, §5ter.2, §7bis; ui-spec §2 (assumed — pending Thomas, inbox #29); pending: checking §5 decision verbs (inbox #19); MCP tool names in api §5 and synthesis §5bis (inbox #19); gate assignment fields (inbox #14)

### SR-013 · major · Endpoint catalogues duplicated between api §5 and admin §5; three public config endpoints

- **Where:** api-and-data-model.md §5 vs admin-and-operations.md §5; authentication-and-access.md §1; telemetry-and-analytics.md §4; architecture §5.
- **Evidence:**
  - At the root in api §5: "`GET/POST /users`, `GET/PATCH /users/{id}`, `GET/POST /groups`, `GET/POST/DELETE /groups/{id}/members`" (l.88); "`GET/PATCH /settings`, `GET /audit-log`, `GET /plugins`, `GET /health`" (l.101).
  - Under `{root}/api/v1/admin` in admin §5 (l.330), with other shapes: `/groups/{id}/members/{principal}` (l.332); `GET /health` "(all checks)" (l.336); `GET /plugins` (l.338). admin §5 has no audit-log endpoint although Audit log is one of its sections (admin §1, l.48).
  - Public config: "public `GET /public-config`" inside the admin-prefixed table (admin, l.337); `GET /api/v1/public-config` (telemetry, l.132); `GET {root}/api/v1/auth/config` (auth §1, l.52).
  - `GET /api/v1/plugins/ui-manifest` (architecture §5, l.219) is missing from api §5.
- **Problem:** two owners give the same resources different paths, so the generated clients diverge. Group admins, who are not system admins, must manage members (admin §2.2), but no path is defined for them.
- **Proposal:**
  - Rule: `/api/v1/admin/*` is for system admins only and owned by admin §5. Everything a non-admin may call (group admins managing members, the plugin UI manifest, a project's audit log for owners) lives at the root and is owned by api §5.
  - Remove the duplicated rows from the api §5 Admin row and keep the link; add `ui-manifest` and the admin audit-log endpoint.
  - One public `GET /api/v1/public-config` with sections `auth`, `branding` and `analytics`; `/auth/config` goes or becomes an alias.
- **Found by:** spec-reviewer (b) SR-211, (c) SR-310 (endpoint part)
- **Status:** partly applied (APPLY1, 2026-10-27): admin §5; api §5 (assumed — pending Thomas, inbox #29); pending: auth §1 `GET /api/v1/auth/config` → `GET /public-config` section `auth` (inbox #15, #21); logout and session endpoints (inbox #20)

### SR-014 · major · Which Unix account runs a launch on a group-owned environment is undefined

- **Where:** schedulers-and-monitoring.md §0.2, §3.2, §6, §10; checking-scenarios.md §11.1; api-and-data-model.md §6; admin-and-operations.md §3.2; ui-spec.md §4.8, §6.
- **Evidence:**
  - "A runner asks the scheduler once per interval about all jobs of its user" (schedulers §0.2, l.21).
  - "It runs on the cluster under the user's account" (checking §11.1, l.261).
  - "Clusters and their credentials belong to groups, not to users" (api §6, l.141) and "a rotating runner credential bound to one environment" (api §6, l.155); the heartbeat lists "environments" (admin §3.2).
  - "Unix user / service account" (ui-spec §4.8, l.132); "a runner running as the same user on that host" (ui-spec §6).
  - "Service or VM node … the runner submits through `ssh login` or REST" (schedulers §6, l.210).
  - EnvCapacity shows "your limits and fairshare" (schedulers §10).
- **Problem:** when user B launches on an environment whose runner runs as user A, the jobs, quota, fairshare and file permissions are A's. Nothing routes a launch to a runner, and the runner ↔ environment cardinality conflicts between specs.
- **Proposal:**
  - Add `execution_identity` to environments: `per_user` (one runner per principal × environment; a launch goes to the launching user's runner or is refused with a reason) or `shared` (a service account, stated in the UI).
  - Add `runners.principal_id` and `unix_user`. api §6 owns this.
- **Found by:** spec-reviewer (d) SR-410
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-015 · major · Background-task ledger and schedules: two schemas, two locking designs, no Jobs object

- **Where:** admin-and-operations.md §3.1, §5 vs architecture §7.2, §7.6; api-and-data-model.md §4 (`Operation`); docs/map.md (items 5 and 7 both claim "tasks").
- **Evidence:**
  - Fields differ: `error {type, message, traceback_ref}` (architecture §7.6, l.393) vs `error {type, message}`, `traceback_ref` as its own field, plus `logs`, `duration_ms`, `expires_at` (admin §3.1, l.131).
  - Scheduling: "an atomic database claim per slot decides who runs it … unchanged with one SQLite process or several Postgres replicas" (admin §3.1, l.140); "`schedules` (slot claims)" (admin §5, l.345); "schedules by atomic DB claim (no beat)" (log, l.136) vs "Scheduled jobs | … worker, Postgres advisory lock" (architecture §7.2, l.313) and "run scheduled tasks under a Postgres advisory lock" (§7.6, l.401).
  - Which processes run the loops: "each process runs the loops" (admin §3.1) vs workers only (architecture §7.6).
  - "**Jobs (users).** The user-facing view of a task the user started" (admin §3.1, l.122) has no table or endpoint; api §4 has "an `Operation` resource (`/operations/{id}`)" (l.78).
  - map.md gives "tasks" to architecture (l.9) and to admin (l.11).
- **Problem:** two schemas and two locking designs for one thing; advisory locks are per-session and do not exist on SQLite. The user-facing record is a third, undefined object. Each spec defers to the other.
- **Proposal:** admin §3.1 owns the ledger schema (renamed per SR-005) and the screen; architecture §7.6 owns the mechanism and links to admin for the columns. Use one mechanism, a unique insert into `schedules(schedule_key, slot_start)`, portable to SQLite; only `worker` and `all` roles run the loops. Define "Jobs" as the api §4 `Operation`: a projection of the ledger that the caller created. Update map.md so that each aspect has one owner.
- **Found by:** spec-reviewer (b) SR-214, (c) SR-315
- **Status:** partly applied (APPLY1, 2026-10-27): map (reading order 6, 8); admin §3.1, §5; api §4; architecture §7.2, §7.6 (assumed — pending Thomas, inbox #29); pending: architecture §7.6 link to admin §3.1 and worker-role rule (inbox #25)

### SR-016 · major · Run and gate states: five vocabularies, no enum, a 2-of-11 WES mapping

- **Where:** owner api-and-data-model.md §7 (new §7.1) and §10; ui-spec.md §3.1; synthesis.md §4, §5, §5bis, §5ter.2; schedulers-and-monitoring.md §7.
- **Evidence:**
  - ui-spec §3.1 (l.40-46): Queued, Running, Awaiting review, Paused, Succeeded, Failed, Cancelled.
  - "a common subset with WES (11 states), plus internal states: `AWAITING_QC`, `PAUSED`" (synthesis §4, l.134); "The platform holds the `AWAITING_INTERVENTION` state" (§5bis, l.187); "`QUEUED → RUNNING(stage k) → STAGE_DONE → AWAITING_INTERVENTION`" (§5ter.2, l.220), `STOPPED`, "`PAUSING → PAUSED`" (l.226); gate lifecycle `pending → awaiting_review → …` (§5, l.140).
  - "`AWAITING_REVIEW` and `PAUSED` → `PAUSED`" (api §10, l.264) is the whole WES mapping.
  - `runs` has `state` (api §7, l.222) and `gates` has `state` (l.227), both without values, although §7 requires "`CHECK` constraints instead of enums" (l.170). The launch example returns lower-case "`state: queued`" (api §5, l.130).
  - "head silent" (schedulers §7, l.218) and "runner offline" appear as run conditions.
  - WES 1.1.0 defines 11 states: UNKNOWN, QUEUED, INITIALIZING, RUNNING, PAUSED, COMPLETE, EXECUTOR_ERROR, SYSTEM_ERROR, CANCELED, CANCELING, PREEMPTED (`openapi/workflow_execution_service.openapi.yaml:659-673`, tag `1.1.0` of ga4gh/workflow-execution-service-schemas, fetched 2026-10-26 by reviewer (b)).
- **Problem:** four names exist for "stopped at a gate" (`AWAITING_QC`, `AWAITING_INTERVENTION`, `AWAITING_REVIEW`, "Awaiting review"). `STAGE_DONE`, `PAUSING` and `STOPPED` have no UI rendering, and the UI does not say whether a gate `stop` shows as Cancelled or Failed. The CHECK constraints, `spectio.run.state_changed` payloads, `?state=` / `--state` filters and the WES facade cannot be written.
- **Proposal:**
  - api §7.1 "Run and gate state machines" owns two lower-snake-case enums, their transitions and the triggering event per transition:
    - `runs.state`: `queued`, `running`, `pausing`, `paused`, `awaiting_review`, `cancelling`, `succeeded`, `failed`, `cancelled`;
    - `gates.state`: `open`, `decided`, `expired`, `superseded`.
  - "Head silent" and "runner offline" are flags on the run, not states. Waiting for an external signal is a gate condition (UX-110).
  - api §10 gets the full WES table: `queued`→QUEUED; `running`→RUNNING; `pausing`/`paused`/`awaiting_review`→PAUSED; `succeeded`→COMPLETE; `failed`→EXECUTOR_ERROR or SYSTEM_ERROR by failure class (schedulers §3.5); `cancelling`→CANCELING; `cancelled`→CANCELED.
  - ui-spec §3.1 maps every value to icon, word and colour, including the transient states. Synthesis §4, §5, §5bis and §5ter.2 link to §7.1 and are marked superseded.
- **Found by:** spec-reviewer (a) SR-104, (b) SR-204, (c) SR-306, (d) SR-404 (state part)
- **Status:** partly applied (APPLY1, 2026-10-27): api §7, §7.1 (new), §10; synthesis §4, §5, §5bis, §5ter.2; ui-spec §3.1 (assumed — pending Thomas, inbox #29); pending: boards: Legend and run lists (Pausing, Cancelling, head-silent and runner-offline flags); pause verbs (inbox #16, SR-018)

### SR-017 · major · Engine bridge behaviour when the server is unreachable: Tower-era text and no testable bound

- **Where:** synthesis.md §8, §10 risk 2; decision 0001 "Consequences"; checking-scenarios.md §11.1; schedulers-and-monitoring.md §3.2.
- **Evidence:**
  - "Keep the spool fallback. On the Nextflow side, a server outage during `create`, `begin` or `progress` aborts the run" (synthesis §10 risk 2, l.396). This is the `nf-tower` `AbortRunException` behaviour (synthesis §2bis, l.46), no longer used.
  - "It needs its own heartbeat, batching and local buffer, on the Tower model" (0001, l.41).
  - "Agents: disk buffer, batched sending, retry with exponential backoff, never block the workflow if the server is unreachable" (synthesis §8, l.369).
  - "Fallback: the agent writes JSONL to the shared file system, and a server-side forwarder reads it" (synthesis §8, l.367), against "The server never mounts storage" (checking §11.1, l.261).
  - "Without the Nextflow plugin, Spectio only knows the task's work directory" (checking §11.1, l.259). Under 0001, without `nf-spectio` Spectio knows nothing about a Nextflow run.
  - "only if a future companion plugin feeds states back; that is not planned" (schedulers §3.2, l.84). `nf-spectio` is that plugin.
- **Problem:** "on the Tower model" can be read as copying Tower's abort-on-error, and risk 2 says the new plugin may abort runs. "Never block" has no measurable bound. The spool fallback puts file access on the server, which the architecture forbids. Whether an exception thrown inside a `TraceObserverV2` hook aborts the run is **[to be validated]** in T2. Decision 0001's list of changed sections does not include synthesis §10 or checking §11.1.
- **Proposal:** in the ingest contract (SR-001, api §14), state as testable requirements (values proposed):
  - plugin hooks never throw and return in ≤ 50 ms (enqueue only);
  - the on-disk buffer keeps at least 24 h or 200 MB, whichever comes first, then drops the oldest progress events and keeps lifecycle events;
  - backoff is capped at 5 min, and a run never fails because of Spectio;
  - with the server down for 30 min, the run completes and every event is delivered after reconnect;
  - the spool is read by the **runner**, not the server.

  Rewrite synthesis §10 risk 2 accordingly (or mark the last sentence Tower-only); reword checking §11.1 l.259 ("for `when: task_done`, until reading declared outputs through the handler is validated, the runner lists the task work directory"); reword schedulers §3.2 ("only if `nf-spectio` fed scheduler states back into Nextflow; not planned").
- **Found by:** spec-reviewer (a) SR-111, (b) SR-222, (d) SR-416
- **Status:** partly applied (APPLY1, 2026-10-27): checking-scenarios §11.1 (reconciled with FC-034); schedulers §3.2; synthesis §8 (rest superseded by CH-001) (assumed — pending Thomas, inbox #28); pending: api §14 bridge bounds (inbox #11)

### SR-018 · major · "Pause": immediate stop or after the current stage

- **Where:** synthesis.md §5ter.2-3; api-and-data-model.md §5 (Runs); ui-spec.md §3.1, §4.4, §4.8, §4.11, §5.1; checking-scenarios.md §11.3, §11.5.
- **Evidence:**
  - "For an unplanned pause ("Pause" button): `PAUSING → PAUSED`" (synthesis §5ter.2, l.226) and "**Unplanned**: SIGINT to Snakemake …, SIGTERM to Nextflow … Running tasks are lost" (§5ter.3, l.232).
  - "`:pause` (after current stage)" (api §5, l.93).
  - "Pause after stage" on the phone Run detail (ui-spec §4.11, l.174); the desktop actions are "(Resume, Relaunch…, Cancel, Duplicate)" (ui-spec §4.4, l.86), with no Pause.
  - "Live checks never kill a running task and never stop the run in the middle of a stage" (checking §11.3, l.329). A conditional Nextflow stage boundary is **[to be validated]** (checking §11.3). Runs without stages show "task quarters" (ui-spec §5.1).
- **Problem:** two meanings. "After current stage" is undefined for a run with no declared stages, for a Nextflow run launched without a stop-file closure, and when stages overlap as dataflow (checking §11.5). The desktop UI has no Pause at all.
- **Proposal:**
  - api §5 (with the state machine of SR-016) defines two verbs: `:pause` (after the stage; needs a boundary generated at launch; refused with a problem+json reason otherwise) and `:stop` (immediate, running tasks lost, cache kept).
  - Synthesis §5ter links to them. ui-spec §4.4 adds "Pause after stage", disabled with the reason when no boundary exists.
- **Found by:** spec-reviewer (a) SR-108
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-019 · major · Principal kinds: guests, plugin and bridge principals are outside the enum

- **Where:** api-and-data-model.md §6, §7, §13.2 vs authentication-and-access.md §1-§2; architecture §3.4, §7.6; admin-and-operations.md §2.1, §2.3.
- **Evidence:**
  - "`kind ∈ {user, service, agent, runner, system}`" (api §6, l.137); `service_accounts` with "owning_group_id, purpose (`lims`, `ci`, `robot`, `agent`)" (api §7, l.214).
  - "Visitors get temporary principals (`kind=guest`, sliding 24 h expiry …)" (auth §1, l.45); "The recipient becomes a **guest principal bound to that link**" (auth §2, l.67).
  - "acting as the plugin instance's service principal" (architecture §3.4, l.154); "the bridge instance's service principal" (architecture §7.6, l.416).
  - "Non-human principals: LIMS, CI, robots, event bridges" (admin §2.3, l.106); the Users kind filter is "People · Service accounts · Agents · Runners" (admin §2.1, l.83), with no guests.
- **Problem:** api §7 mandates CHECK constraints, so guest rows and plugin or bridge principals fail to insert. Instance-scoped plugins have no group for `owning_group_id`. Admins cannot list or expire guests.
- **Proposal:** add `guest` to `principals.kind` with `expires_at` and `share_link_id`; add purposes `plugin` and `bridge`; make `owning_group_id` nullable for instance-scoped principals, owned by `system`; add "Guests" to the admin §2.1 filter; state in api §13.2 that guests are never mirrored to depictio.
- **Found by:** spec-reviewer (b) SR-207
- **Status:** partly applied (APPLY1, 2026-10-27): api §7 service_accounts (assumed — pending Thomas, inbox #18); pending: `guest` principal kind, admin §2.1 'Guests' filter and api §13.2 mirroring rule (inbox #18, #21); api §6 kind list (inbox #13, #14, #15)

### SR-020 · major · The system-admin flag, protected groups and P.I. fields are missing from the schema

- **Where:** api-and-data-model.md §6, §7, §13.1 vs admin-and-operations.md §1, §2.1, §2.2, §5; authentication-and-access.md §1; cli §4.
- **Evidence:**
  - "`User.is_admin` bypasses permissions | same flag and meaning" (api §13.1, l.294), but `users` has "principal_id, email, username, default_project_id, preferences (JSON)" (api §7, l.213) and `groups` has "name, parent_id".
  - Admin uses: "System admin" in the create-user form (admin §2.1, l.79); "`PATCH` state, admin flag" (admin §5, l.332); "`admin` and `users` are protected and cannot be deleted" (admin §2.2, l.100); "`<email>` becomes P.I. and group admin at their first sign-in" (admin §2.2, l.94); `/groups/{id}/pending-pi` (admin §5, l.332).
  - `pending_pi_email` (cli §4, l.132) and `must_change_password` (auth §1, l.143) appear only outside the schema.
  - Single-user start creates only "a group `personal`" (api §6, l.158).
- **Problem:** the root of authorisation has no column. Open: is "admin" the flag, membership of the `admin` group, or the `admin` token scope? Are `admin` and `users` created in single-user mode? Can one `group_members.role` say "P.I. and group admin"? May an admin's token without the `admin` scope reach `/admin/*`?
- **Proposal:** api §7 adds `users.is_admin`, `must_change_password`, `email_verified_at`, `last_login_at`, and `groups.description`, `sso_managed`, `pi_principal_id`, `pending_pi_email`; `group_members.role` ∈ {`member`, `admin`}. `is_admin` is the only source of admin rights; the `admin` group is a mirror kept for depictio. `/admin/*` requires `is_admin` and the `admin` scope. Single-user start sets `is_admin=true` and creates the protected groups.
- **Found by:** spec-reviewer (b) SR-210
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-021 · major · Launcher instances and Environments are two models of the same cluster

- **Where:** architecture §3.3, §5; api-and-data-model.md §5, §7; admin-and-operations.md §5; schedulers-and-monitoring.md §3.2.
- **Evidence:**
  - "One plugin can have several configured **instances**: … or two SLURM clusters" (architecture §3.3, l.135).
  - "`environments` | owning_group_id, kind (slurm, k8s, local…), config (JSON)" (api §7, l.219); observer settings live "in the environment settings" (schedulers §3.2, l.83).
  - The scope rules cover "Notifier, sink, resolver, check, viewer and AI provider" (architecture §3.3, l.142) but not engine, launcher, analytics, API or CLI extensions.
  - Scoped instances have only `GET/POST/PATCH/DELETE /plugin-instances` under the admin prefix (admin §5, l.338).
- **Problem:** an implementer cannot tell where a SLURM cluster's settings and secrets live (`plugin_instances` or `environments`). A group admin cannot add the group's own Slack instance.
- **Proposal:** an Environment **is** the launcher instance: `environments.config` is validated by the launcher's settings model, launchers are excluded from `plugin_instances`, and the "two SLURM clusters" example goes. Complete the scope rules for every kind. Add `/projects/{id}/plugin-instances` and `/groups/{id}/plugin-instances`, guarded by owner or group admin. (The `/plugins` vs `/admin/plugins` and `ui-manifest` parts are in SR-013.)
- **Found by:** spec-reviewer (c) SR-310
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-022 · major · No compatibility window between CLI, runners, engine bridges, plugins and server

- **Where:** cli §1, §2 (exit code 6); admin-and-operations.md §3.2; dev-env §12; architecture §2, §3.1, §3.2, §4.
- **Evidence:**
  - "`GET /version` at start, warning on skew, error past the supported window" (cli §1, l.31). The window is never defined.
  - "**Version skew** beyond one minor version shows a warning" (admin §3.2, l.147).
  - "**Pre-1.0 policy:** minor versions may break the API" (dev-env §12, l.377).
  - "the previous major stays supported for one Spectio minor release" (architecture §4, l.198).
  - A plugin declares `spectio-sdk>=1.2,<2` (architecture §3.1, l.81) and a per-kind `api` range while the core is 0.x. `nf-spectio` and the Snakemake logger are released separately (architecture §2).
- **Problem:** a 0.3 runner on a login node against a 0.4 server, which is allowed to break, only gets a warning. Three version axes (SDK package, per-kind API, core) have no stated relation.
- **Proposal:** add architecture §12 "Compatibility between components": a table for CLI ↔ server, runner ↔ server, bridge ↔ ingest `schema_version` (SR-001) and plugin ↔ SDK. Before 1.0, the runner and CLI must match the server's minor (otherwise refuse with exit 6 and an upgrade hint); from 1.0, N−1 minor. Plugins declare only the per-kind range; the SDK package version is independent. Question for Thomas (lag tolerance before 1.0).
- **Found by:** spec-reviewer (c) SR-314
- **Status:** partly applied (APPLY1, 2026-10-27): admin §3.2; architecture §4, §12 (new); cli §1 (assumed — pending Thomas, inbox #28); pending: architecture §3.1 example dependency (inbox #25); bridge ↔ ingest `schema_version` contract in api §14 (inbox #11)

### SR-023 · major · Gate checks depend on the depictio catalogue, but 0.1 has no depictio

- **Where:** api-and-data-model.md §13.6 (rules 1 and 6); checking-scenarios.md §7, §11.2; depictio-ecosystem-reuse.md §0, §3.8; log 2026-10-26 ("MVP scope").
- **Evidence:**
  - "A check that has a catalogue binding uses it. The runner runs the recipe on the partial outputs at gate time … Spectio never re-implements a recipe that the catalogue has" (api §13.6 rule 1, l.352).
  - The catalogue layer is "the source of gate checks: `depictio:<module>/<output>#<column>`" (api §13.6, l.345). checking §7 has no `depictio:` binding, and checking calls per-file recipes a future request to depictio (l.348).
  - "Running that campaign through Spectio, with the depictio hand-off at the end, is the first real test" (reuse §0, l.34).
  - "automatic hand-off to depictio comes later, not in 0.1" (log, l.318).
- **Problem:** for nf-core/rnaseq, rule 1 makes the 0.1 gates require a depictio recipe runtime on the runner. That runtime does not exist yet (reuse §3.8) and has no install path (DEP-T-016). Nothing says which binding wins when both exist.
- **Proposal:** 0.1 uses only the checking §7 bindings. Add `depictio:` to checking §7 as optional, active when a recipe runtime is declared on the environment, with precedence "catalogue first when available". Rephrase rule 1 accordingly; reuse §0 labels the joint use case "after 0.1". Question for Thomas.
- **Found by:** spec-reviewer (d) SR-413
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-024 · major · Tokens are specified twice, differently

- **Where:** api-and-data-model.md §5, §6, §7 vs authentication-and-access.md §1-§4; synthesis §7bis. Auth says "This spec owns the *sign-in methods, sessions, tokens and links*" (auth, l.8).
- **Evidence:**
  - **Format:** "Personal tokens, service-account tokens and agent tokens share one format (`spk_<kind>_<random>`, stored hashed)" (api §6, l.155) vs "Access token … bearer JWT (EdDSA or RS256)" (auth §3, l.99) and "Refresh token … **rotated on every use**" (l.100).
  - **Runner credentials:** "rotating runner credential" (api §6, l.155) vs "Runner token | until revoked" (auth §3, l.103) (also SR-002).
  - **Scopes:** api §6 list vs `principals:provision` (auth §4, l.111) vs `interventions:resolve` (synthesis §7bis, l.280); no ingest scope (SR-001).
  - **Endpoints:** api §5 lists only "`POST /auth/device` + `POST /auth/token` (CLI device flow, phase 2)" (l.87). Missing: `POST /auth/magic-links` (auth l.65), `POST /share-links` (l.67), `POST /principals:provision` (l.112), `GET /auth/config` (l.52), `/.well-known/jwks.json` (l.99), and the login endpoint.
  - **Table:** `tokens` has "principal_id, hash, scopes (JSON), project_id (nullable), expires_at, last_used_at" (api §7, l.216): no name, kind, family / rotation, revoked_at or IP. Sessions (server-side rows, auth §3 l.98) and share links have no table.
- **Problem:** two specs give different formats, lifetimes and scope lists for the same credentials. Neither the token tables nor the OpenAPI can be written.
- **Proposal:** auth §3 owns token kinds, formats, lifetimes and a single scope registry (including the ingest scope of SR-001 and `principals:provision`). api §6 "Tokens and scopes" becomes a link; api §5 "Session & me" lists auth's endpoints or links to auth §2; api §7 gets `tokens`, `sessions`, `refresh_tokens(family_id, rotated_from)` and `share_links` columns taken from auth. Decide whether runner credentials rotate.
- **Found by:** spec-reviewer (b) SR-206, (c) SR-302 (credential part)
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-025 · major · `launcher` and `reviewer`: rungs on a ladder or capability flags

- **Where:** api-and-data-model.md §6, §7 vs admin-and-operations.md §2.4 vs cli-and-shared-libraries.md §2 (`project share`) and §4 (`Role`).
- **Evidence:**
  - "role ∈ `viewer < launcher < reviewer < editor < owner` … `launcher` and `reviewer` are Spectio-only steps between viewer and editor" (api §6, l.140), with a cumulative table; `project_grants` holds a single `role` (api §7, l.218).
  - "They appear as an 'Advanced' row of capabilities on top of Editor" (admin §2.4, l.114).
  - "`share --user|--group … --role owner|editor|viewer [--launcher] [--reviewer]`" (cli §2, l.51); "`Role` (owner / editor / viewer)" in `bioplatform-models` (cli §4, l.132).
- **Problem:** ladder vs flags. With the ladder, every reviewer can launch, so an external QC reviewer who must not launch on the cluster cannot be expressed. `--role viewer --reviewer` has no meaning in api §6, "on top of Editor" contradicts "between viewer and editor", and the shared `Role` model cannot hold Spectio's grants.
- **Proposal:** api §6 decides; admin §2.4 and cli link to it. The reviewers disagree:
  - (b): base role ∈ {viewer, editor, owner} as in depictio, plus capabilities `launch` and `review` on viewer grants (editor and owner imply both); `project_grants.capabilities` (JSON); the depictio mirror carries the base role only.
  - (c): keep the five-step ladder; the CLI takes `--role viewer|launcher|reviewer|editor|owner`; admin §2.4 says "between Viewer and Editor"; `bioplatform-models` carries depictio's three roles plus a Spectio extension enum with the api §13.2 downgrade rule.

  Question for Thomas.
- **Found by:** spec-reviewer (b) SR-209, (c) SR-311
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-026 · major · Webhooks are both a project table and a notifier plugin instance

- **Where:** api-and-data-model.md §5, §6, §7, §8, §13.5 vs architecture §2, §3.3, §3.5, §9; admin-and-operations.md §1.
- **Evidence:**
  - "`webhooks`, `deliveries` | project_id, url, secret_hash, event_types (JSON)" (api §7, l.232); the project owner manages webhooks (api §6, l.150).
  - "**One delivery path.** An outgoing webhook is just an instance of the built-in `webhook` notifier" (architecture §3.5, l.165); instances live in `plugin_instances` (architecture §3.3); the MVP lists "notifier (email, webhook)" (architecture §9, l.436).
  - Admin IA: "Events & webhooks" under Activity (admin §1, l.45) and "Notifications: notifier instances and routing" under Instance (l.52); api §13.5 puts "Webhooks" under Instance.
- **Problem:** two storage models, two permission models (project owner vs plugin-instance scope) and two UIs for one object; the outbox worker has two sources of subscriptions.
- **Proposal:** webhooks stay first-class (the `webhooks` table and `/webhooks` API, project-scoped, owned by api §8) and the outbox worker delivers them. Remove the `webhook` notifier from architecture §2/§9, or define it as the delivery code that reads the `webhooks` table. api §13.5 links to admin §1 (SR-039).
- **Found by:** spec-reviewer (b) SR-212
- **Status:** applied (APPLY1, 2026-10-27): architecture §2 (Notifier row), §3.5 (assumed — pending Thomas, inbox #29)

### SR-027 · major · The base install's "nothing else" dependency rule is contradicted by the specs' own choices

- **Where:** cli §0.3, §3, §5, §6; architecture §3.1, §4, §6, §7.3; api §5.
- **Evidence:**
  - "`pip install spectio` is the CLI, the Python client and the runner: httpx, pydantic, typer, rich and nothing else" (cli §0.3, l.19); the same list in architecture §6.
  - The same specs also require: "Configuration has one layered model (pydantic-settings)" (architecture §7.3, l.336); YAML for `~/.config/spectio/servers.yaml` (cli §3, l.106); `token: keyring:spectio/embl` (cli §3, l.115); "`spectio plugin new` … renders a Copier template" (architecture §4, l.204); a WebSocket channel (api §5, l.92); `spectio-sdk`, which the runner needs to load engine and launcher plugins (architecture §3.1); check providers on the runner (SR-003).
  - The runtime dependencies of `openapi-python-client`'s generated code (cli §5) are **[to be validated]**.
- **Problem:** the base-install CI job and import-linter would encode a rule the design already breaks.
- **Proposal:** cli §6 lists an explicit allow-list (`spectio-sdk`, pydantic, pydantic-settings, httpx, typer, rich, a YAML parser, and a WebSocket client if SR-002 picks WebSocket). keyring goes in `[keyring]`; Copier runs through `uvx copier`; check-provider dependencies are named. The < 80 MB budget stays the testable rule. Architecture §6 links to the list.
- **Found by:** spec-reviewer (c) SR-308
- **Status:** partly applied (APPLY1, 2026-10-27): architecture §4, §6; cli §0 item 3, §3, §6; pending: CI: base-install job and import-linter rule enforcing the allow-list; WebSocket client (inbox #12)

### SR-028 · major · The TypeScript client handles bearer tokens for the UI, which should use HttpOnly cookies

- **Where:** cli §5 vs authentication-and-access.md §3; depictio-ecosystem-reuse.md §1.3.
- **Evidence:**
  - "The wrapper handles the bearer token, refresh on 401 and retry, as depictio's `authFetch` does … Used by the UI, the embeddable elements and host plugins" (cli §5, l.163).
  - "HttpOnly, Secure, `SameSite=Lax` cookie; a CSRF token on writes … Not readable by JavaScript, unlike depictio's localStorage bearer" (auth §3, l.98).
  - "`authFetch` (bearer token, refresh on 401, retry) | **Copy** into `@spectio/client`" (reuse §1.3, l.80).
- **Problem:** following cli §5 rebuilds depictio's token-in-JavaScript pattern, which auth §3 rejects.
- **Proposal:** cli §5 defines two modes: `session` (same origin, cookies, CSRF header, no token in JavaScript; used by the UI) and `bearer` (embed tokens and host plugins). reuse §1.3 copies only the retry logic.
- **Found by:** spec-reviewer (c) SR-316
- **Status:** partly applied (APPLY1, 2026-10-27): cli §5; pending: depictio-ecosystem-reuse §1.3 `authFetch` row (inbox #26)

### SR-029 · major · Project visibility has three values in the model and two in the UI

- **Where:** api-and-data-model.md §6, §12, §13.2 vs admin-and-operations.md §2.4.
- **Evidence:**
  - "Visibility `private` (grants only), `group` (all members of the owning group) or `instance` (everyone can read)" (api §6, l.139); "Default visibility for new projects (`group` is proposed)" (api §12, l.282); "`group` ↔ `group_viewers` of the owning group" (api §13.2, l.306).
  - "**Visibility.** A Public / Private switch, with the same sentences as depictio" (admin §2.4, l.112).
- **Problem:** the proposed default, `group`, cannot be selected or shown in the sharing UI. Because `group` mirrors to a depictio group grant, it duplicates a viewer grant to the owning group: two ways to express the same access.
- **Proposal:** two values, `private` and `instance`, as depictio does. "Group" access becomes a default viewer grant to the owning group, created with the project. Update api §6, §12 Q3 and §13.2. Question for Thomas.
- **Found by:** spec-reviewer (b) SR-208
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-030 · major · A restore rewinds the database under runs still executing; token handling is contradictory

- **Where:** admin-and-operations.md §4.3; authentication-and-access.md §3.
- **Evidence:**
  - "Tokens. As in depictio, they are not restored, so the admin's session survives a restore" (admin §4.3, l.247).
  - "each table is wiped and replaced, with rollback if anything fails" (l.277).
  - "A restored run whose directory is gone shows as archived" (l.246).
  - Sessions are server-side rows (auth §3, l.98).
- **Problem:**
  - The admin's session survives only if `sessions` and `tokens` are not wiped, but neither is listed as excluded; kept tokens can then point to principals absent from the backup.
  - Into a fresh server, every runner credential, service-account token and run token is gone, so runners and LIMS integrations break silently.
  - Runs launched after the backup are still executing; their events arrive for run IDs that no longer exist, and nothing says what happens.
- **Proposal:** list the tables preserved across a restore (`tokens`, `sessions`, `runners`) and revoke rows whose principal is absent. The dry run reports runners and integrations that will need new credentials. A final restore step asks each runner for its live handles; unknown runs are adopted as "orphaned after restore" or cancelled, as chosen in the wizard. Ingest for an unknown run returns `409` with a problem type, and bridges keep buffering until adoption. Question for Thomas (default: adopt or cancel).
- **Found by:** spec-reviewer (b) SR-216
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-031 · major · Single-user mode trusts loopback, but loopback is shared on a login node

- **Where:** api-and-data-model.md §1, §6; authentication-and-access.md §1, §6. To cross-check with security-reviewer (R5).
- **Evidence:**
  - "**Personal** | `spectio serve` on a laptop or a login node, bound to `127.0.0.1`, auth mode `single`" (api §1, l.18).
  - "Requests from `127.0.0.1` / a Unix socket without a token are treated as that user" (api §6, l.159).
  - "binds to `127.0.0.1` by default. On any other interface it requires a token … (depictio's own risk note on shared login nodes)" (auth §1, l.43).
- **Problem:** on a multi-user login node any local account can connect to 127.0.0.1 and, through the local runner, submit jobs under the owner's cluster account. api §1 names the login node as a supported place for this mode.
- **Proposal:** in `single` mode, accept requests without a token only on a Unix socket in a 0700 directory, or after a peer-credential check (`SO_PEERCRED`, [unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html)); TCP loopback requires a cookie set from a one-time URL printed by `spectio serve`. Update the auth §6 tests. Or restrict the mode to laptops and service nodes. Question for Thomas.
- **Found by:** spec-reviewer (b) SR-217
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-032 · major · Built-in plugins are separate distributions, yet one `uv tool install spectio` is said to be enough

- **Where:** architecture §0, §2, §3.1, §6, §7.3, §7.4, §7.6, §9; cli §6.
- **Evidence:**
  - "Built in: … local, slurm" (architecture §2, l.42); `plugins/` holds "first-party plugins, each its own distribution" (`engine-nextflow/ engine-snakemake/ launcher-slurm/ …`, architecture §6, l.238-239), while `spectio/` is the "CLI + generated Python client + runner daemon and local launcher" (l.233).
  - "a login node needs one `uv tool install spectio`" (cli §6, l.175).
  - Extras: "`[postgres]`, `[s3]`, `[oidc]` (Authlib), `[saml]`, `[redis]`, `[all]`" (architecture §7.3, l.333) vs "`[postgres]`, `[s3]`, `[oidc]`, `[saml]`, `[celery]`" (cli §6, l.172).
  - The image runs `uv pip install "spectio[postgres,s3,oidc,saml]==X.Y.Z"` (architecture §7.4, l.347), with no server extra, while cli §6 has `spectio[server]` (l.171) and architecture §9 ships a separate `spectio-server` (l.436).
  - The Celery plugin is "`spectio-plugin-celery`" (architecture §7.6, l.402) and directory `tasks-celery/` (§6, l.243); the rule is `spectio-plugin-<name>` (§3.1, l.75). DEP-T-030 (R8b) covers only the depictio plugin.
- **Problem:** nobody can tell which wheels a login node or the image needs, whether an extra installs a library or a plugin distribution, or what the plugin packages are called. As written, the image contains no server.
- **Proposal:** in architecture §6, built-ins ship as modules inside `spectio` (runner side) and the server package (server side) and register entry points there; `plugins/` holds optional plugins only. Each auth or backend extra pulls its plugin distribution (`spectio[oidc]` → `spectio-plugin-oidc`). Directory name = `<name>`. Align the extras in architecture §7.3 and cli §6, decide between `spectio[server]` and `spectio-server`, and fix the image line.
- **Found by:** spec-reviewer (c) SR-307
- **Status:** applied (APPLY1, 2026-10-27): architecture §0, §2, §6, §7.3, §7.4, §8; cli §6 (assumed — pending Thomas, inbox #29)

### SR-033 · major · `on_fail: open_gate` creates a gate with no items, policy or deciders

- **Where:** checking-scenarios.md §11.3 vs §7; api-and-data-model.md §6, §7.
- **Evidence:**
  - "`open_gate` | A gate is opened at the end of the stage, even if the stage declares none, with the failed items preselected" (checking §11.3, l.320).
  - A declared gate needs `items.source/key` and `decide.humans/agents` (checking §7); `gates` rows carry `policy (JSON)` (api §7, l.227); "the decision endpoint checks both the role and the policy" (api §6, l.152).
- **Problem:** an implicit gate has no item set beyond the failed files, no policy and no view. Nobody can tell who may decide it, or whether agents may.
- **Proposal:** define the implicit gate in checking §11.3: items are the `{key}` values seen by the watch; checks are the watch's checks; the view is the item table; the policy is "project reviewers and above, `agents: none`", overridable by the overlay's run-level `decide`. Store it with `policy.source = implicit` (see UX-111 `gate_source`).
- **Found by:** spec-reviewer (d) SR-405
- **Status:** inbox (TRIAGE1, 2026-10-27)

### SR-034 · major · schedulers §8 defines tables, events and endpoints the API spec does not have

- **Where:** schedulers-and-monitoring.md §3.4, §3.5, §8 vs api-and-data-model.md §5, §7, §8.
- **Evidence:**
  - "links: `run_id`, `task_attempt_id`" on `scheduler_jobs` (schedulers §8, l.231) vs "the parent job ID plus each array element … are stored n:m with engine attempts" (schedulers §3.4, l.104) and the n:m `attempt_jobs` table (api §7, l.224).
  - `environment_snapshots` (l.237), `spectio.task.waiting_changed` (l.239), `spectio.environment.capacity_low` (l.241), `GET /runs/{id}/scheduler`, `GET /environments/{id}/capacity` and `POST /environments/{id}/preflight` (l.245) appear nowhere in api §5, §7 or §8 (checked: zero occurrences). UX-121 asks for "a pre-flight endpoint" without knowing this one exists.
  - `failure_class` values are prose only (schedulers §3.5).
- **Problem:** the single `task_attempt_id` link contradicts the n:m model. The API catalogue, which is the OpenAPI source, misses three endpoints, two events and a table.
- **Proposal:** api §5, §7 and §8 own the contracts: add the three endpoints, the two events, `environment_snapshots`, and `failure_class` on `spectio.task.failed`. Drop `task_attempt_id` in favour of `attempt_jobs`. schedulers §8 keeps the meaning and links to api. Define `failure_class` as an enum: `oom`, `timeout`, `preempted`, `node_failure`, `cancelled_external`, `image`, `tool_error`, `engine_fault`.
- **Found by:** spec-reviewer (d) SR-408
- **Status:** partly applied (APPLY1, 2026-10-27): api §5, §7, §8; schedulers §3.5, §8 (assumed — pending Thomas, inbox #29); pending: `GET /environments/{id}/capacity` and `POST /environments/{id}/preflight` in api §5 (inbox #20)

### SR-035 · major · Push transport needs an inbound Kafka consumer the architecture does not have

- **Where:** schedulers-and-monitoring.md §0.3, §3.3, §9, §11 vs architecture §2, §7.6, §9.
- **Evidence:**
  - "Slurm's `jobcomp/kafka` read through Spectio's Kafka bridge" (schedulers §0.3, l.25); jobcomp records are Slurm job JSON with a "topic [that] defaults to the cluster name" (schedulers §3.3, l.92, citing https://slurm.schedmd.com/jobcomp_kafka.html).
  - `def stream(self, ctx) -> AsyncIterator[JobRecord] | None: ...   # push transports (Kafka, …)` on the runner-side `SchedulerObserver` (schedulers §9, l.264).
  - "Bridges read from the same outbox as webhooks" (architecture §7.6, l.421): bridges are outbound, inbound is described only for MQTT robot signals; bridges run on the server (architecture §2) and come in phase 3 (architecture §9, l.439), while schedulers §11 puts Kafka in phase 2.
- **Problem:** it is unclear whether the server bridge or the runner observer consumes the topic. The topic carries every user's jobs on the cluster and nothing filters them per tenant. The phases disagree.
- **Proposal:** in schedulers §3.3, make the Kafka consumer a transport of the runner's `SchedulerObserver`, filtering to the runner's own user before anything leaves the cluster; it is not an event bridge. Align its stage in dev-env §15 (SR-007; reviewer (d) suggests unscheduled).
- **Found by:** spec-reviewer (d) SR-409
- **Status:** inbox, assumed: the Kafka consumer is a transport of the runner's `SchedulerObserver`, filtered to its own user; its stage follows SR-007 — pending Thomas (TRIAGE1, 2026-10-27); not applied (APPLY1): blocked by inbox #25 (schedulers §0 item 3 and §3.3)

### SR-036 · major · The `checks_as` preset shape requested from depictio does not match Spectio's check syntax

- **Where:** depictio-ecosystem-reuse.md §1.4, §3.7 vs checking-scenarios.md §4, §7.
- **Evidence:**
  - "check presets such as `{kind: outlier, column: pct_mito, by: sample, k: 3}`, validated against `OUTPUT_SCHEMA` like `renders_as`. Spectio reads them as its presets (checking §4)" (reuse §3.7, l.153).
  - Checks use `{ id, from: "<binding>", min/max, severity, kind, scope }` (checking §7); `outlier` is "robust deviation from the batch (median ± k·MAD), per group if given" (checking §4, l.84), with no key names. The presets table has no file format.
  - "evidence `match` globs" (reuse §1.4) vs `evidence: - { kind, path, per_item }` (checking §7).
- **Problem:** depictio would build and validate a shape Spectio cannot read (`column` vs `from`; `by` and `k` undefined). Changing a contract across two projects later is costly.
- **Proposal:** define the keys of each check kind in checking §4/§7 (or the new §12, SR-004), for example `outlier: {k, by}`, `relative: {against}`, and the preset file format. Send depictio that exact shape, without `from` (it comes from the catalogue output). Fix "match" to "path" in reuse §1.4.
- **Found by:** spec-reviewer (d) SR-414
- **Status:** partly applied (APPLY1, 2026-10-27): checking-scenarios §4.1 (new); depictio-ecosystem-reuse §3 row 7 (assumed — pending Thomas, inbox #27); pending: depictio-ecosystem-reuse §1.4 `match` → `path` (inbox #26); checking §7 example (inbox #16, #19); sending the request to depictio (Thomas, inbox #27)

### SR-037 · major · SLURM job names: the head-job pattern and the Snakemake join do not work as written

- **Where:** schedulers-and-monitoring.md §3.1, §3.4.
- **Evidence:**
  - The head job is "named `spectio-<run_id>`" (schedulers §3.1, l.64); reconciliation uses "`squeue --me --name 'spectio-*'`" (l.67).
  - "Spectio sets `--slurm-jobname-prefix spectio-<run_id>`, then `sacct --name` / `squeue --name`" (schedulers §3.4, l.102).
  - The plugin joins prefix and UUID: `self.run_uuid = "_".join([jobname_prefix, self.run_uuid])` (snakemake-executor-plugin-slurm `8c2af56`, `snakemake_executor_plugin_slurm/__init__.py:481-496`, cited by reviewer (d)). Task jobs are therefore named `spectio-<run_id>_<uuid4>`.
  - "`-n, --name=<name_list>` … a comma separated list of job names" (https://slurm.schedmd.com/squeue.html). Wildcards are not documented **[to be validated on sind]**.
- **Problem:** `--name spectio-<run_id>` matches only the head job, and the UUID is known only from a log line. `'spectio-*'` probably matches nothing; if it did, it would also match Snakemake task jobs and treat them as head jobs.
- **Proposal:** name head jobs `spectio-head-<run_id>`. Reconcile from the batched `squeue --me --json` / `sacct --json` snapshot, filtered client-side on the name prefix and on `--comment=spectio:<run_id>`. For Snakemake, join on the prefix `spectio-<run_id>_` client-side; do not use `--name`. Validate in T3.
- **Found by:** spec-reviewer (d) SR-411
- **Status:** partly applied (APPLY1, 2026-10-27): schedulers §3.1 (head-job prefix, Runner restart); pending: none; the §3.4 Snakemake cell was superseded by FC-007

### SR-038 · major · Maintenance mode does not say which writes still work

- **Where:** admin-and-operations.md §4.3, §4.4.
- **Evidence:**
  - "Choices: block new launches and gate decisions, or make the API read-only. Runners keep executing running jobs either way" (admin §4.4, l.306).
  - "Used automatically by restore and migrations" (l.308).
  - "maintenance mode turns on, runners stop picking up new launches" (admin §4.3, l.276).
- **Problem:** "read-only" is not testable. Engines keep sending events, so it is undefined whether `POST /ingest/events`, runner heartbeats and the runner channel, `check.evaluated`, robot signals (`/gates/{id}/signals`), sign-in, webhook delivery and the scheduled loops keep working; which status code a refused request gets; whether gate timeouts keep counting; and how long the bridges must buffer.
- **Proposal:** add to admin §4.4 a table of endpoint families against the modes `normal`, `no-launch`, `read-only` and `restoring`. Ingest and the runner channel stay open in every mode except `restoring`. Refused writes return `503` with `Retry-After` and problem type `…/maintenance`. Gate timeouts pause during maintenance. Bridges must buffer at least the announced maximum window (proposed 2 h; see SR-017).
- **Found by:** spec-reviewer (b) SR-215
- **Status:** partly applied (APPLY1, 2026-10-27): admin §4.4; pending: restore wizard step → mode `restoring` (inbox #24); bridge buffer bounds in api §14 (inbox #11)

## Minors

### SR-039 · minor · "Settings" leftovers next to Administration, with a different grouping in api §11/§13.5

- **Where:** api-and-data-model.md §11, §13.5; ui-spec.md §2, §4.5, §4.11; architecture §3.1, §4, §10; telemetry-and-analytics.md §0.4, §2; depictio-ecosystem-reuse.md §1.1; authentication-and-access.md §5. Owners: admin-and-operations.md §1 and ui-spec.md §4.9.
- **Evidence:**
  - "Settings tabs: Users & groups, Projects, Service accounts, Tokens, Webhooks, Plugins" (api §11, l.275); Tokens moved to Profile (log, l.134).
  - "**Activity** (Runs, Events, Logs, Health) · **Instance** (Branding, AI & agents, Webhooks, Settings)" (api §13.5, l.335) vs admin §1 (l.43-55): Activity = Tasks, Runners, Events & webhooks, Logs, Health, Audit log; Instance adds Plugins, Notifications, Backups, Maintenance.
  - "Settings → Plugins" three times in architecture; "Settings → Telemetry" (telemetry); "Settings → Version check" (reuse §1.1); "Settings → Sign-in" (auth §5). admin §4.5 lists none of these sub-panels.
  - ui-spec: "Auto-approve rules (Settings)" (§4.5, l.100); the phone More sheet lists "Settings" (§4.11, l.164); a bare "settings" control in the top bar (§2, l.28). Auto-approve rules live in the gate's `decide` policy, not in an admin page.
- **Proposal:** write paths as "Administration → `<group>` → `<section>`"; api §11 and §13.5 link to admin §1 and ui-spec §4.9 instead of listing tabs; admin §4.5 lists Sign-in, Telemetry and Version check sub-panels; ui-spec §4.5 says "(from the gate's `decide` policy)"; the phone More sheet and the top bar say "Administration" (admins only).
- **Found by:** spec-reviewer (a) SR-113, (b) SR-218 (Settings part), (c) SR-318, (d) SR-418 (Settings part)
- **Status:** partly applied (APPLY1, 2026-10-27): admin §4.5; api §11, §13.5; architecture §3.1, §4, §10; auth §5; telemetry §0, §2.3; ui-spec §2, §4.5, §4.11; pending: depictio-ecosystem-reuse §1.1 (inbox #26); boards AppTopbar, MMore and admin boards titled Settings

### SR-040 · minor · Stale names: agent for runner, `perspectio`, companion plugin, Duplicate

- **Where:** synthesis.md §1, §7quater, §8, §9; ui-spec.md §4.4, §5, §6; admin-and-operations.md §0.4.
- **Evidence:**
  - "Each engine has its own small agent" (synthesis §1, l.11); "server and agent run in the same process (`perspectio serve`)", "via the agent", "outgoing agent" (§7quater, l.339-348); "Agents: disk buffer" and "the agent writes JSONL" (§8, l.367-369); "Snakemake agent", "Nextflow agent (V2 plugin)" (§9, l.377-378); "agents that heartbeat and claim 'Run now' requests" (admin §0.4, l.22). The log says "**agent** means AI agent only" (2026-10-25, l.101) and `principals.kind=agent` is AI only.
  - "`spectio runner connect <token>`" (synthesis §7quater) vs "`runner connect <server> --token …`" (cli §2, architecture §7.3).
  - "shown as 'not scheduled' (companion plugin)" (ui-spec §5, l.181), although `nf-spectio` is the only plugin.
  - Run detail action "Duplicate" (ui-spec §4.4, l.86; §6, l.208) vs "'Duplicate' becomes the secondary 'Copy to a new launch'" (§4.6, l.124).
- **Proposal:** "runner" for the Spectio process, "engine plugin" (`nf-spectio`, Snakemake logger) for the in-engine reporters, `spectio serve --with-runner` for the combined process, the cli §2 syntax for `runner connect`, "runners (depictio's watcher agents)" in admin §0.4, "`nf-spectio`" in ui-spec §5, and "Copy to a new launch" in ui-spec §4.4 and §6.
- **Found by:** spec-reviewer (a) SR-112, (b) SR-218 (agent part), (c) SR-319, (d) SR-418 (agent part)
- **Status:** partly applied (APPLY1, 2026-10-27): admin §0; synthesis §1, §7quater, §8, §9; ui-spec §4.4, §5, §6; pending: boards RunDetail and Main still labelled 'Duplicate'

### SR-041 · minor · Run and review screens are specified outside ui-spec; two cross-references are broken

- **Where:** ui-spec.md §4.4, §4.5, §10.2; schedulers-and-monitoring.md §3.1, §10; checking-scenarios.md §11.4; api-and-data-model.md §13.6.
- **Evidence:**
  - "**Run detail → Scheduler tab**" (schedulers §10, l.271); "The run detail shows a **Live checks** panel" (checking §11.4, l.335); a gate review "Dashboard" tab (api §13.6 rule 3, l.354). None is in ui-spec §4.4 (9 tabs) or §4.5.
  - "Every pattern has the states of §3: empty, loading, error, permission" (ui-spec §10.2, l.303). §3 is the run status system and defines none of these.
  - "No run is lost (synthesis §7 risk register)" (schedulers §3.1, l.67). The risks are in synthesis §10.
- **Proposal:** add Scheduler and Live checks to ui-spec §4.4 and Dashboard (conditional) to §4.5, each linking to its owning spec; add ui-spec §11 "Component states" (empty, loading, error, permission, n/a) and point §10.2 to it; fix the schedulers reference to synthesis §10.
- **Found by:** spec-reviewer (a) SR-116
- **Status:** partly applied (APPLY1, 2026-10-27): schedulers §3.1; ui-spec §4.4, §4.5, §10.2, §11 (new) (assumed — pending Thomas, inbox #29); pending: boards RunDetail tab bar (Scheduler, Live checks), ReviewReport / ReviewDashboard tab bar (Dashboard)

### SR-042 · minor · The built-in AI assistant has UI and a runner command but no API, data model or CLI entry

- **Where:** ui-spec.md §4.9; api-and-data-model.md §5, §7; cli §2; architecture §2 (AI provider kind).
- **Evidence:**
  - "the runner starts the model server as an ordinary GPU job (`spectio ai serve --env … --model … --gpus 1 --idle-stop 2h`), registers it as an endpoint" (ui-spec §4.9, l.149).
  - "Lists: model endpoints (kind, where it runs, data policy, state), connected agents …, default limits for agents (… read evidence ≤ 50 MB …)" (l.151).
  - No `ai` command in cli §2; no model-endpoint or agent-limit endpoint or table in api §5 or §7.
- **Proposal:** architecture §2 (AI provider kind) owns model endpoints; add `/admin/ai/endpoints` and agent-limit fields to api §5/§7 and `spectio ai serve` to cli §2 (SR-006). Or mark ui-spec §4.9 item 2 as post-1.0. Per-agent launch limits overlap UX-126.
- **Found by:** spec-reviewer (a) SR-117
- **Status:** applied (APPLY1, 2026-10-27): admin §5; api §7; architecture §2; cli §2 (`ai` row); no stage claim (owned by dev-env §15) (assumed — pending Thomas, inbox #29)

### SR-043 · minor · "v1" means both the API path and a release; the API rule conflicts with 0.x semver

- **Where:** api-and-data-model.md §4, §5; admin-and-operations.md §3.1, §4.2; dev-env §12, §14; log 2026-10-26 (versioning).
- **Evidence:**
  - "only additive changes within v1; breaking changes go to v2" (api §4, l.80) vs "a breaking change also bumps the minor (`bump-minor-pre-major`)" (log, l.257) and the OpenAPI frozen only at 1.0 (dev-env §14, item 6).
  - "Kinds in v1: … `sink.depictio`, `sink.labid`, … `bridge.publish`" (admin §3.1, l.134). The depictio hand-off is after 0.1 (log, l.318); LabID and bridges come in phases 2 and 3 (architecture §9).
- **Proposal:** api §4: "During 0.x, `/api/v1` may break in a minor release, announced in the changelog; the additive-only rule starts at 1.0.0." Elsewhere write "API v1" for the path and "0.1" / "1.0" for releases. Tag each background-task kind with its stage (SR-007).
- **Found by:** spec-reviewer (b) SR-221
- **Status:** partly applied (APPLY1, 2026-10-27): admin §3.1, §4.2; api §4, §5 heading, §12; architecture §11; pending: api §6 'Flat in v1' (inbox #13, #14, #15); stage tag per background-task kind (inbox #16)

### SR-044 · minor · Superseded merge and staging rules remain in dev-env, map.md and auth

- **Where:** dev-env §0.6, §8; docs/map.md (item 10); authentication-and-access.md §2. Owners: documentation-system.md §8 and the log (2026-10-26, inbox #3).
- **Evidence:**
  - "Humans merge." (dev-env §0.6) and "A human merges." (dev-env §8) vs "On `autopilot/integration`: auto-merge is always on" (documentation-system §8) and "Claude may merge into `main` for now" (log; inbox #3).
  - "eight reviewers and builders" (dev-env §8); CLAUDE.md lists twelve agents.
  - "staging behind Tailscale Funnel" (map.md) and "For staging and demos" (auth §2, l.65). Staging was dropped (log, "Dev previews without a server").
- **Proposal:** dev-env §0.6 and §8 say "Merges follow documentation-system §8" and link to the CLAUDE.md agent table; map.md says "dev previews (Cloudflare Pages, Codespaces), public instance from the beta"; auth §2 says "dev previews and demos".
- **Found by:** spec-reviewer (c) SR-322
- **Status:** partly applied (APPLY1, 2026-10-27): map (reading order 11); dev-env §0, §8; pending: auth §2 'For staging and demos' (inbox #20, #21)

### SR-045 · minor · The event catalogue is incomplete, and gate notifications have two paths

- **Where:** api-and-data-model.md §8 vs §13.3, §13.4; architecture §3.4, §3.5; admin-and-operations.md §3.1.
- **Evidence:**
  - `spectio.run.dashboard_ready` is emitted and bridged (api §13.3, l.321; §13.4, l.330) but missing from the §8 table.
  - `spectio.ext.<plugin>.*` (architecture §3.4) and the SSE-only `check.evaluated` (api §8, l.248) have no schema.
  - The `gate.notify` background-task kind (admin §3.1, l.134) vs notifiers that subscribe through the outbox (architecture §3.5, l.164).
- **Proposal:** api §8 lists every type (webhook, SSE-only, extension); `dashboard_ready` is marked after 0.1; drop `gate.notify` or define it as the outbox delivery to notifiers. See SR-052 for the `check.evaluated` name.
- **Found by:** spec-reviewer (b) SR-219
- **Status:** applied (APPLY1, 2026-10-27): admin §3.1; api §8

### SR-046 · minor · Pipeline identifier and workflow version key: `@` vs `/`, no column

- **Where:** cli §2, §4, §5; api-and-data-model.md §7, §13.4; depictio-ecosystem-reuse.md §2.4.
- **Evidence:**
  - "`launch <org/name@version>`" and `workflow="nf-core/rnaseq@3.27.0"` (cli §2, l.47; §5).
  - "`PipelineRef` (`<org>/<name>/<version>`)" (cli §4); "**Pipeline identifier**: `<org>/<name>/<version>` everywhere" (api §13.4); depictio template IDs and Spectio workflow version keys are the same string (reuse §2.4).
  - `workflow_versions` has only "revision, commit" (api §7). Git, local and Snakemake-catalog workflows have no `<org>`.
  - The CLI takes names (`--env embl-slurm`, `--project liver-tc`); the API takes prefixed IDs. How a name resolves is not specified.
- **Proposal:** canonical form `<org>/<name>/<version>`; the CLI accepts `@` as input only and prints the canonical form. Add `workflow_versions.key` (unique per project) with a defined form for git and local sources. Define name → ID resolution: a project or environment slug unique per instance, or an error listing the candidates.
- **Found by:** spec-reviewer (c) SR-320, (d) SR-420
- **Status:** applied (APPLY1, 2026-10-27): api/index.md; api §7; cli §2, §5 (assumed — pending Thomas, inbox #29)

### SR-047 · minor · Fixture workflows and step numbers in dev-env disagree with the playbook and with §10.1

- **Where:** dev-env §1, §3, §9, §10.1 vs docs/playbooks/next-phase.md (D4, T1, T2) and pipeline.yaml; checking-scenarios.md §11.5.
- **Evidence:**
  - `doctor.sh` runs "`nextflow run tests/fixtures/workflows/nf-toy`" (dev-env §1); §3 defines `nf-toy` and `smk-toy` with stages "A → gate → B → C" (l.88). `tests/fixtures/workflows/` does not exist at `3b209d3`; `tests/pipelines/synthetic/` (§10.1, "`qc` → gate → `align` → gate → `quant`") exists and is verified.
  - "**D4:** build the fixture workflows and record the first golden fixtures" (dev-env §9) vs "D4 · CI and Claude in GitHub" and "T1 · Fixture workflows" / "T2 · Engine event capture" on `nf-toy` (next-phase).
  - checking §11.5 validates the stop-file closure "on `nf-toy`".
- **Proposal:** declare the §10.1 synthetic pipelines the fixture workflows; §3 becomes a pointer and keeps its number. `doctor.sh`, T1/T2 and checking §11.5 use `tests/pipelines/synthetic`. dev-env §9 links to `pipeline.yaml` instead of numbering steps itself.
- **Found by:** spec-reviewer (c) SR-323
- **Status:** partly applied (APPLY1, 2026-10-27): next-phase T1–T4, P1; dev-env §1, §3, §9 (assumed — pending Thomas, inbox #28); pending: checking §11.3 `nf-toy` (inbox #19); tool: `dev/doctor.sh` paths

### SR-048 · minor · Untestable thresholds: "head silent" and the 10,000-file watch limit

- **Where:** schedulers-and-monitoring.md §7; checking-scenarios.md §11.5; decision 0001 (Consequences).
- **Evidence:**
  - "When they stop while the head job is still `RUNNING`, the run shows as 'head silent'" (schedulers §7, l.218); "It needs its own heartbeat" (0001, l.41), with no interval.
  - "A watch on 10,000 per-cell files is refused at save time" (checking §11.5). The number of matching files is unknown at save time.
- **Proposal:** bridges send a heartbeat every 60 s when idle, as the Tower model does (synthesis §2bis); "head silent" = no event for 5 min while the last `squeue` shows the head job `RUNNING` (put the heartbeat in api §14, SR-001). A watch is refused at save time when `{key}` binds to a `children` kind; at run time, evaluation stops after N files per watch (for example 2,000) with the state "suspended: too many files".
- **Found by:** spec-reviewer (d) SR-417
- **Status:** partly applied (APPLY1, 2026-10-27): checking-scenarios §11.5; schedulers §7 (assumed — pending Thomas, inbox #28); pending: api §14 idle heartbeat (inbox #11)

### SR-049 · minor · api §3 repeats the plugin-kind table with the stale "broker" kind and another engine contract

- **Where:** api-and-data-model.md §3 vs architecture §2, §3.6; log 2026-10-25.
- **Evidence:**
  - "adds the launcher, AI provider, file store, broker, API and CLI extension kinds" (api §3, l.57). Architecture §2 split the broker into `spectio.tasks` and `spectio.pubsub` (plus `spectio.bridge`, `spectio.backup`, `spectio.analytics`).
  - api §3 gives the engine contract as "launch, stop at stage, resume, cancel, event source"; in architecture §3.6, `cancel` belongs to `Launcher`, and `Engine` has `detect / describe / plan / plan_resume / collect / ingest`.
- **Proposal:** replace the api §3 table with one sentence and a link to architecture §2; word the kinds as "task backend, pub/sub, event bridge". The log is append-only, so the "broker" wording of 2026-10-25 is corrected by a new log entry, not an edit.
- **Found by:** spec-reviewer (b) SR-218 (broker part), (c) SR-317
- **Status:** applied (APPLY1, 2026-10-27): api §3 (table removed, kinds owned by architecture §2); 2026-10-25 'broker' wording corrected in decisions/log.md (APPLY1 entry)

### SR-050 · minor · The backup and restore contract differs between the CLI and admin specs

- **Where:** admin-and-operations.md §4.3, §4.4, §5 vs cli-and-shared-libraries.md §2.
- **Evidence:**
  - "`restore (--dry-run default, --tables, --force)`", "`validate`" and "`migrate project … --mode all|metadata|files`" (cli §2, l.61-62).
  - vs "each table is wiped and replaced" (admin §4.3, l.277), "Verify" / `POST /backups/{id}/verify`, and no mode on the project migration (l.290).
  - "the three wizards in §4.3" (admin §4.4, l.311) vs four migrations listed (l.287-290).
  - "the manifest signature" (l.268), although the manifest (l.239) has no signature field or signing key.
- **Proposal:** decide whether partial restore by table exists (recommended: no, which removes `--tables`); use one verb, `verify`; fix the wizard count; define the signature (Ed25519 with the instance key, verifiable without the archive's own `keys/`).
- **Found by:** spec-reviewer (b) SR-220
- **Status:** partly applied (APPLY1, 2026-10-27): admin §4.3, §4.4; cli §2 (assumed — pending Thomas, inbox #24); pending: restore wizard steps and encryption rules, cli §2 backup example (inbox #24)

### SR-051 · minor · Kubernetes RBAC differs between specs, and the Nextflow head pod has none

- **Where:** schedulers-and-monitoring.md §1, §4 vs architecture §7.5.
- **Evidence:**
  - "a Role that lets it create Jobs and Pods" (architecture §7.5).
  - "`pods` … get, list, watch; `jobs`: create, get, list, watch, delete" (schedulers §4).
  - Nextflow "creates one Kubernetes `Job` per task (default since 26.10; `Pod` before)" (schedulers §1, l.43); dev-env also tests 25.10. That is done by the head pod, whose ServiceAccount is never specified. Nextflow's required permissions are **[to be validated]** (https://docs.seqera.io/nextflow/kubernetes); 25.10 needs `pods: create` **[to be validated on k8s-mini]**.
- **Proposal:** schedulers §4 owns RBAC and defines two ServiceAccounts: the runner's (creates the head Job and watches) and the engine head's (create / delete / get / list / watch on pods and jobs, `pods/log`, by Nextflow version), validated in T4. Architecture §7.5 links to it.
- **Found by:** spec-reviewer (c) SR-321, (d) SR-419
- **Status:** applied (APPLY1, 2026-10-27): next-phase T4; architecture §7.5; schedulers §4

### SR-052 · minor · Check-result vocabulary: `state` vs `verdict`, and how severity maps to them

- **Where:** checking-scenarios.md §4, §11.3, §11.4; api-and-data-model.md §7, §8, §13.6.
- **Evidence:**
  - "state (`ok`, `warn`, `fail`, `provisional`, `too_large`, `error`)" (checking §11.4) vs "check_key … verdict (…)" (api §7).
  - Severities are `block`, `warn`, `info` (checking §4); "When a `warn` or `block` check fails" (checking §11.3).
  - The SSE event is "`check.evaluated`" (api §8, l.248), while every other type is `spectio.*`.
- **Proposal:** store the outcome (`pass` / `fail` / `provisional` / `too_large` / `error`) and the severity separately, and display warn / fail as outcome × severity. Name the column `verdict` in both specs; rename the event `spectio.check.evaluated` (SSE only). Extra states are covered by UX-103.
- **Found by:** spec-reviewer (d) SR-415
- **Status:** applied (APPLY1, 2026-10-27): api §7, §8; checking-scenarios §11.1, §11.4 (assumed — pending Thomas, inbox #29)

### SR-053 · minor · ui-spec contradicts the logged shell and list decisions without a new log entry

- **Where:** ui-spec.md §1.1, §2, §7 vs decision log 2026-10-25 "UI review round 2".
- **Evidence:**
  - "**Shell**: sidebar copied from depictio (logo on top, …, footer with theme, runners, server, profile), fixed and full height; top bar without logo" (log, l.102).
  - "**Top bar** across the full width: animated logo (home) …, **colour mode** (only here)" and "**Sidebar** below it" (ui-spec §2, l.28-29). The AppTopbar board follows ui-spec.
  - "Card grid dropped" (log, l.104; ui-spec §4.3) vs "list patterns (card grid / table toggle)" (ui-spec §1.1, l.8) and "List pattern: card/table toggle (`ViewPicker`)" (§7, l.220).
- **Proposal:** add a dated log entry recording the full-width top bar with logo and colour mode, and the sidebar below it. In ui-spec §1.1 and §7, say "table / rows toggle".
- **Found by:** spec-reviewer (a) SR-114
- **Status:** applied (APPLY1, 2026-10-27): ui-spec §1, §7; shell revision recorded in decisions/log.md (APPLY1 entry) (assumed — pending Thomas, inbox #29)

## Questions for Thomas

These need a decision before the related findings can be applied. Reviewer recommendations are given where they agree.

1. **WES facade (SR-010):** 0.1, private alpha, public beta, or unscheduled? All reviewers say not in 0.1; two recommend the public beta, one before the beta, one unscheduled. Same question for MCP and OIDC (SR-007).
2. **Stage contents (SR-007):** is the Kubernetes launcher in 0.1 or the alpha? Are Postgres and OIDC needed for the design-partner alpha?
3. **Observed runs (SR-001):** are terminal-started runs part of 0.1 or the alpha? Do they get a long-lived user token with an ingest scope on the login node, or must every observed run go through a wrapper (`spectio run nextflow …`) so that it gets a run token?
4. **Runner transport (SR-002):** WebSocket (with long-poll fallback) or HTTPS long-poll / SSE? Does any EMBL proxy or SSH-tunnel constraint decide it?
5. **Snakemake steering (SR-008):** may the runner launch Snakemake as a command-line head job (`--until`, `--forcerun`), relaxing the "no Python `subprocess`" constraint of the first session notes, or must it use the Python API inside the workflow's environment?
6. **Nextflow boundary (SR-011):** confirm that the generated `ext.when` config (no pipeline change) is the only mechanism and that `--stage` cooperation is dropped.
7. **Pause (SR-018):** is an immediate "stop now, keep the cache" in scope next to "pause after stage", and is either needed in 0.1?
8. **Roles (SR-025):** may a reviewer decide gates without being allowed to launch (for example an external QC reviewer)? This decides ladder vs capability flags.
9. **Project visibility (SR-029):** drop `group` and use depictio's two-value model?
10. **Shared clusters (SR-014):** does each user run their own runner, or is a site service account acceptable?
11. **Checks in 0.1 (SR-023):** only Spectio's own bindings, or depictio catalogue recipes on the runner as well?
12. **Version skew before 1.0 (SR-022):** may runners on clusters lag the server by one minor, at the cost of keeping the API backward compatible during 0.x?
13. **Restore (SR-030):** when runs launched after the backup are found, adopt or cancel by default?
14. **Single-user mode on shared login nodes (SR-031):** supported deployment, or laptops and service nodes only?

## Proposed spikes

| Spike | Validates | Findings | Where |
|---|---|---|---|
| Extend **T2** (engine event capture) | capture against a draft api §14 envelope; whether an exception in a `TraceObserverV2` hook aborts the run; hook latency; Snakemake run UUID and Nextflow `sessionId` availability for the run handshake; idle heartbeat | SR-001, SR-017, SR-048 | `spikes/engine-events/` (T2 already planned) |
| **Nextflow stage boundary** | generated `ext.when = false` stops after a stage on 25.10 and 26.10; nf-core modules honour `task.ext.when` (source it); stop-file closure; rerun-from-stage through a generated `ext` key that enters the task hash | SR-011, SR-018 | `spikes/nf-stage-boundary/`, on `tests/pipelines/synthetic` |
| **Snakemake steering** (only if Thomas wants evidence first) | CLI head job vs `SnakemakeApi` worker in the workflow environment: stop via SIGINT vs API, version coupling, logger hookup | SR-008 | `spikes/smk-steering/` |
| **Runner transport** | WebSocket upgrade and long-poll / SSE through the EMBL proxy and an SSH tunnel; streaming a large file both ways | SR-002 | needs EMBL access; otherwise a local proxy mock in `spikes/runner-transport/` |
| **Runner footprint with check bindings** | install size of the base runner plus MultiQC, anndata and polars against the 80 MB budget; which bindings fit in an extra | SR-003, SR-027 | `spikes/runner-footprint/` |
| Extend **T3** (sind) | `squeue --name` with wildcards; the Snakemake SLURM job-name join; filtering on `--comment` | SR-037 | T3 profiles |
| Extend **T4** (kind) | the Nextflow head pod's minimal RBAC for 25.10 (Pods) and 26.10 (Jobs) | SR-051 | T4 profiles |
