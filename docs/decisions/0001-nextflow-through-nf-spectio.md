# 0001. Nextflow reports through nf-spectio, not the Tower protocol

Date: 2026-10-26 · Status: accepted

## Context

- **Earlier plan.** [`synthesis.md`](../specs/synthesis.md) §1 (item 2) and §2bis planned to implement the five routes of Nextflow's Tower protocol on the server, so that a run launched with `-with-tower` reports to Spectio with nothing to install. A companion plugin (`nf-spectio`) was to add what the protocol does not carry: published files, modules, environments.
- **Weaknesses of that plan:**
  - the protocol is undocumented;
  - it positions Spectio as a Seqera replacement ([adoption note](../research/adoption-and-positioning-2026-10-26.md) §2, inbox #6);
  - `nf-tower` has a single endpoint: `TowerConfig` holds one `final String endpoint` (`plugins/nf-tower/src/main/io/seqera/tower/plugin/TowerConfig.groovy:84`, set at `:117`; nextflow `114f1fe`, 2026-10-26). So a run pointed at Spectio cannot report to Seqera Platform as well.
- **Why a second plugin can coexist.** Nextflow asks **every** `TraceObserverFactoryV2` provided by the loaded plugins for observers, and registers all the observers they return (a factory can return none: `nf-tower` does when it is disabled) (`modules/nextflow/src/main/groovy/nextflow/Session.groovy:581-590`, same commit). `nf-tower` is one of these factories (`TowerFactory.groovy:38`), and `nf-spectio` would be another. Running both in one run is **[to be validated]** in spike T2.
- **Who is affected:** users who already use Seqera Platform and want Spectio's checks and gates on the same runs.

## Options

1. **Tower protocol first, `nf-spectio` optional** (earlier plan).
   - For: zero install.
   - Against: undocumented protocol; one endpoint, so Spectio *or* Seqera; two ingestion gateways to maintain.
2. **Both, with Tower labelled best effort** (inbox #6 recommendation).
   - Against: still two gateways, and the Tower route gives less (no file names, [`checking-scenarios.md`](../specs/checking-scenarios.md) §11).
3. **`nf-spectio` only.**
   - For: one native gateway (`/api/v1/ingest/events`) for both engines, built on public extension points; it runs next to `nf-tower`.
   - Against: one plugin to install, set once by `spectio login`; `TraceObserverV2` is `@Beta` ([`synthesis.md`](../specs/synthesis.md) §10).

## Decision

Option 3 (Thomas, 2026-10-26). Nextflow reports to Spectio only through `nf-spectio`, from the MVP on. The Tower protocol routes are not implemented. Spectio is meant to sit next to Seqera Platform, not to replace it.

## Consequences

- One ingestion gateway for both engines. The specs changed to say so:
  - `synthesis.md` §1, §2bis, §2ter, §5ter (items 4 and 6), §7quater and §9;
  - `api-and-data-model.md` §2, §5 and §10;
  - `ui-spec.md` §6;
  - `schedulers-and-monitoring.md` §0, §3 and §7;
  - `checking-scenarios.md` §11;
  - `cli-and-shared-libraries.md` §2;
  - `dev-environment-and-testing.md` §6, §9 and §14.
- Spike T2 builds a first `nf-spectio` and checks that it runs next to `nf-tower` (`docs/playbooks/next-phase.md`, T2).
- `nf-spectio` must be published in the Nextflow plugin registry before the private alpha. It needs its own heartbeat, batching and local buffer, on the Tower model ([`synthesis.md`](../specs/synthesis.md) §2bis).
- The `@Beta` interface is a tracked risk: pin the Nextflow versions and test both in CI (R4).
- **Follow-up (UI boards):** RunObserved, Profile, WorkflowsCatalog, WorkflowDiscovered and RunScheduler in `design/ui-canvas/` still show the Tower protocol or `-with-tower` as the Nextflow route. They must be updated, and the media rendered from them refreshed, in the next UI step (R7 or the board pass that follows it).
- **Follow-up (agent prompts):** `.claude/agents/test-architect.md`, `.claude/agents/constraints-hunter.md` and `.claude/skills/spike/SKILL.md` still mention Tower protocol payloads. Thomas updates them, or approves the change.
- Still to check: how Seqera Platform shows a run that Spectio stops at a gate and resumes. It probably shows two runs.
