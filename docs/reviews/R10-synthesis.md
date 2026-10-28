# R10 · Synthesis and go / no-go

Draft · 2026-10-28 · waiting for Thomas (GO gate after P1)

![R10 funnel: 450 review findings read, 123 still open, 70 of the 82 open blockers and majors deferred with features that left 0.0.1, 12 touching 0.0.1 of which 7 already decided, ending at the GO gate](../assets/diagrams/r10_synthesis_light.png#only-light)
![R10 funnel: 450 review findings read, 123 still open, 70 of the 82 open blockers and majors deferred with features that left 0.0.1, 12 touching 0.0.1 of which 7 already decided, ending at the GO gate](../assets/diagrams/r10_synthesis_dark.png#only-dark)

Step page: [Progress · R10](../progress/W4/R10.md).

What, among the open review findings, stands between today and the narrowed 0.0.1 ([dev-env §15.1](../specs/dev-environment-and-testing.md#151-capabilities-by-version), [§15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts), [mvp-0.0.1](../specs/mvp-0.0.1.md), [log 2026-10-28](../decisions/log.md#2026-10-28-001-narrowed-launch-and-monitor-an-ultra-simple-ui)). Short answer: little, and most of it is decided. This page edits no spec.

## 1. Scope and method

- **Read:** the twelve round files (R1–R9, R8b, R11, R12), [spikes.md](spikes.md), [inbox.md](inbox.md), and the [log](../decisions/log.md) entries APPLY1–APPLY3, "Inbox answers #5 to #37" and the three 0.0.1 entries. Not counted: `code/` (per-step code reviews, closed in their PRs) and R2's verification table.
- **Counted** on 2026-10-28 by a script over each `### ID · severity · title` heading and its **Status** line: 450 findings. "Open" = status `inbox` or `accepted` (not applied). Owning spec = the **Where** line's "owner", else its first spec (board-only UX → ui-spec); the per-spec split is approximate, the totals exact.
- **Status lines vs APPLY entries.** The 286 IDs that APPLY1 and APPLY2 list match their status lines (0 mismatches); APPLY3 wrote its result into spikes.md. Staleness comes from later decisions instead: 52 open findings sit on inbox entries Thomas decided on 2026-10-27, whose spec text waits for the inbox-answers apply pass after W3 (log, "Applied later"); they stay counted as open. Four open findings already have their 0.0.1 part in the specs: SEC-102, SR-031, SR-091 (dev-env §15.3) and SR-067 (architecture §7.3).

| Status | Blocker | Major | Minor | Total |
|---|---|---|---|---|
| Applied | 0 | 32 | 82 | 114 |
| Partly applied (doc done; a board, tool or blocked part remains) | 10 | 119 | 71 | 200 |
| **Open: inbox** | **8** | **65** | **20** | **93** |
| **Open: accepted, not applied** | **0** | **9** | **21** | **30** |
| Rejected | 0 | 1 | 11 | 12 |
| Closed without edit (FC-021, already fixed by CH-001 and CH-006) | 0 | 0 | 1 | 1 |
| **Total** | 18 | 226 | 206 | 450 |

Where the 123 open findings wait:
- 52 on decided inbox entries (spec text pending);
- 14 on deferred entries (#17, #18);
- 35 on entries still open or only assumed;
- 22 need no decision: board-only fixes (R7), docs-site fixes (R11), and the R12 findings that no apply step covered yet.

## 2. Open findings by severity and spec

| Owning spec | Blocker | Major | Minor | Partly applied (residue) |
|---|---|---|---|---|
| [api-and-data-model](../specs/api-and-data-model.md) | 3 | 20 | 3 | 43 |
| [checking-scenarios](../specs/checking-scenarios.md) | 2 | 8 | 1 | 4 |
| [architecture-plugins-and-packaging](../specs/architecture-plugins-and-packaging.md) | 1 | 8 | 1 | 16 |
| [synthesis](../specs/synthesis.md) | 1 | 6 | 1 | 17 |
| [authentication-and-access](../specs/authentication-and-access.md) | 1 | 5 | 3 | 2 |
| [ui-spec](../specs/ui-spec.md) and boards | 0 | 15 | 17 | 55 |
| [schedulers-and-monitoring](../specs/schedulers-and-monitoring.md) | 0 | 7 | 1 | 9 |
| [admin-and-operations](../specs/admin-and-operations.md) | 0 | 3 | 0 | 11 |
| [documentation-system](../specs/documentation-system.md) | 0 | 1 | 8 | 12 |
| [dev-environment-and-testing](../specs/dev-environment-and-testing.md) | 0 | 1 | 4 | 19 |
| [depictio-ecosystem-reuse](../specs/depictio-ecosystem-reuse.md) | 0 | 0 | 2 | 4 |
| cli, playbooks / CI, other | 0 | 0 | 0 | 8 |
| **Total** | **8** | **74** | **41** | **200** |

**All 18 blockers** are applied (fully or in their 0.0.1 part) or deferred with a reason. "0.0.1" means P1 acts on it (§3a).

| Blocker | Round | Status (counted) | Disposition |
|---|---|---|---|
| SR-001 ingest contract | [R1](R1-consistency.md) | inbox (#11, #36 decided) | **0.0.1**: driven-run part (spool format, caps) decided (#36 a), api §14 not written; observed-run part deferred |
| SR-054 ingest contract for 0.0.1 | [R3](R3-journeys.md) | inbox (#36 decided) | **0.0.1**: same as SR-001 |
| SEC-102 tokenless loopback on a login node | [R5](R5-security.md) | inbox (#15 open) | **0.0.1** part applied in dev-env §15.3 (token link); rest deferred (#15) |
| SR-055 no local environment / runner record | R3 | partly (APPLY2) | **0.0.1**: one environment record at `spectio init` (api §6 residue) |
| CH-041 head fate on server stop | R3 | partly (APPLY2) | **0.0.1**: heads adopted by name (schedulers §3.1); residue a board |
| CH-042 run state machine | R3 | partly (APPLY2) | **0.0.1**: api §7.1 applied; pause and stop residue deferred (#16) |
| CH-001 head job and compute-node egress | [R4](R4-constraints.md) | partly (APPLY1) | **0.0.1**: solved by the spool; residue api §14 and egress (§4 Q7) |
| DEP-T-002 release-please with `GITHUB_TOKEN` | [R8b](R8b-depictio-tooling.md) | partly (APPLY1) | **0.0.1 tag**, not P1: needs the GitHub App (#8) |
| SR-002 runner ↔ server protocol | R1 | inbox (#12 open) | Deferred: no remote runner in 0.0.1 |
| SEC-101 runner account vs principals | R5 | inbox (#14 open) | Deferred: one user on their own Unix account (§15.3) |
| SR-057 rnaseq stage and gate | R3 | inbox (#34) | Deferred: no gates (#34 answer) |
| SR-058 MultiQC bindings at gate time | R3 | inbox (#34) | Deferred: no gates |
| DL-101 runner-side `depictio-cli ingest` | [R8](R8-depictio.md) | inbox (#22 decided) | Deferred: no depictio hand-off |
| SR-003 where check providers run | R1 | partly (APPLY1) | Residue deferred with checks |
| SR-004 `spectio.yml` schema | R1 | partly (APPLY1) | Residue (gate policy, overlays) deferred with gates |
| SR-005 `tasks` vs `background_tasks` | R1 | partly (APPLY1) | Applied; residue (boards, reuse §1.1) deferred |
| SR-062 relaunch from a failed gate | R3 | partly (APPLY2) | Deferred: gates and relaunch are out (#61) |
| DEP-T-001 path-filtered required checks | R8b | partly (APPLY1) | Tooling: `ci-ok` exists; protection waits for #8 |

Blockers that touch 0.0.1: **8** (3 with an open status: SR-001, SR-054, SEC-102; 5 partly applied: SR-055, CH-041, CH-042, CH-001, DEP-T-002). Deferred by the cut: **10**.

## 3. The 0.0.1 cut checked against the open findings

The cut: one user, `spectio serve` on a SLURM login node behind an SSH tunnel and a token link, SQLite on node-local disk, heads through `sbatch`, events through the spool (`nf-spectio`, Snakemake logger plugin); three screens, text and tables only; no gates, Kubernetes, visualisation or relaunch (#61, assumed).

### 3a. What P1 must handle (as tasks or tests)

Of the 82 open blockers and majors, 12 touch the cut (3 blockers, 9 majors); partly-applied findings whose residue lands in it are listed with them.

| # | Topic | IDs | Owning spec | P1 action |
|---|---|---|---|---|
| 1 | Spool event contract: format, caps, cursor and replay, planned-task count | SR-054, SR-001 (driven part), SR-080; residue of CH-001, CH-044, CH-005, CH-011, SR-084, UX-272 | api §14 (to write, #36 a); [dev-env §15.3](../specs/dev-environment-and-testing.md#153-001-on-a-cluster-architecture-and-safety-without-accounts) req. 6; architecture §13.1 | Write the driven-run part of api §14 first; test it by replaying the T2 fixtures |
| 2 | Token link and the seven §15.3 security requirements | SEC-102, SR-031, SR-091 (0.0.1 parts applied; status lines stale) | dev-env §15.3 | One task and one test per requirement; spike sec-single-mode for the three browser behaviours marked **[to be validated]** |
| 3 | How a workflow reaches the launch form | SR-056 (#34, open); UX-119 (minor) | api §5; ui-spec §4.6, §8 | Needs Thomas (§5, D2) |
| 4 | What engine events may carry into SQLite on a shared login node | SPK-T2-11, SPK-T2-23 (#55, reserved) | architecture §13.5; admin §3.4 | Needs Thomas (§5, D3) |
| 5 | Engine install and plugin delivery | SR-067 (#35 decided, applied in architecture §7.3; status stale); residue of FC-039, FC-040, CH-006, CH-009 | architecture §7.3, §13.3, §13.4 | `spectio doctor`; jar from the wheel (read-only `NXF_PLUGINS_DIR` **[to be validated]**); Snakemake range test; logger added, not replacing; bridge failure never fails the run |
| 6 | Server restart while heads run | CH-041 | schedulers §3.1 | Restart test on `slurm-mini`: head adopted by name, spool read from its cursor |
| 7 | Run and task states | CH-042; SPK-T2-09 (`aborted`, #56 assumed) | api §7.1, §7.2 | Implement the subset without pause and resume |
| 8 | The one environment and the runs root at `spectio init` | SR-055 | api §6; architecture §7.2 | Init task and test |
| 9 | Read API for the three screens: stages, counts, timestamps, logs, failure cause, Snakemake launch body | residue of SR-082, SR-088, SR-089, UX-273, CH-047, UX-277 | api §5, §5.2, §7 | OpenAPI for the 0.0.1 routes only |
| 10 | Files the server reads (spool, logs) stay inside the run root | residue of SEC-105 | checking-scenarios §11.1 (rule); architecture §13.7 (log sources) | Path and symlink confinement test |
| 11 | SQLite discipline, and SQLite on node-local disk | residue of CH-013, CH-015 | architecture §7.2, §7.3 | WAL and lock settings as specified; §4 Q4 |
| 12 | Keeping `spectio serve` up on a login node | CH-028 (accepted; blocked by #14 and #25) | schedulers §6 | Manual start plus adoption on restart; §4 Q1 |
| 13 | Empty and first-run state of the runs list | UX-211 | ui-spec §4.3 | One UI state |

The [P1 prompt](../playbooks/next-phase.md) already covers rows 1, 2, 6 and 8; P1 should add 5, 7, 9–13. Rows 3 and 4 need Thomas.

A gap that no finding names: dev-env §15.3 req. 7 cites `:cancel`, but §15.1 has no cancel row (D4 in §5; if yes, the drain rule of schedulers §2, row L1, and FC-001 apply).

### 3b. What the narrowed cut defers

The other 70 open blockers and majors, by the feature that left the cut:
- **QC checks and gates** (16): SR-057, SR-058, SR-023, SR-033, UX-101, UX-102, UX-104, UX-105, UX-106, UX-108, UX-110, UX-129, FC-002, SEC-111, SEC-114, DL-104.
- **Relaunch, parameter history, pause** (3): UX-109, UX-113, SR-018.
- **Users, sign-in, roles, tokens, sharing, observed runs** (17): SR-020, SR-024, SR-025, SR-029, SEC-104, SEC-108, SEC-113, SEC-117, SEC-121, SEC-122, UX-126, UX-201, UX-202, UX-204, UX-206, UX-217, CH-030.
- **Shared server, remote runners, runner identity, plugins** (11): SR-002, SEC-101, SR-014, SR-021, SR-035, SEC-106, SEC-115, SEC-116, SEC-118, SEC-124, UX-117.
- **Kubernetes and slurmrestd** (6): SPK-T4-01, SPK-T4-03, SPK-T4-12, SPK-T4-14, SPK-T3-15, DEP-T-015.
- **depictio hand-off and co-hosting** (6): DL-101, DL-102, FC-003, SEC-109, SEC-120, DEP-T-013.
- **Later features: WES, batches, chaining, image viewer** (4): SR-010, UX-120, UX-122, UX-128.
- **Operations, packaging, scale, process** (7): SR-030, SEC-119 (backup); CH-004 (scale model); DEP-T-003 (images); DEP-T-008 (auto-merge paths); SR-007 (old phase tables, which §15 already marks as historical); UX-222 (boards).

The 41 open minors (board, docs-site and later-feature items) are not listed; none is a precondition. UX-119 joins row 3; UX-227 matters only if boards serve as the 0.0.1 UI reference.

## 4. Open questions for EMBL IT

[schedulers §12](../specs/schedulers-and-monitoring.md) owns the site questions (its Q1–Q7). This list orders them for 0.0.1 and adds those §15.3 raised ("new": to add to §12 at the next apply step). Nothing is sent without Thomas (#27).

**Login node and SLURM (blocks testing 0.0.1 at EMBL):**
1. May a user keep a long-running `spectio serve` on a login node, kept up by `systemd --user` with lingering, cron, or neither? Does a session or CPU / memory cap kill it? Depends: dev-env §15.3 "Site prerequisites", schedulers §6; §12 Q2; CH-028.
2. Does the login alias round-robin? The tunnel must reach the server's node (new). Depends: dev-env §15.3 "Access", architecture §7.3.
3. Is SSH local port forwarding (`ssh -L`) to login nodes allowed, and through which jump host (new)? Depends: dev-env §15.3 "Access".
4. Does the login node have persistent node-local disk that is not purged, and how much (new)? Depends: dev-env §15.3 "Where data lives", architecture §7.2.
5. May an engine head run as a long SLURM job submitted from the login node: walltime, partition or QOS for heads, per-user job limits? Depends: schedulers §3.1, §3.2; CH-026.
6. Are `squeue` and `sacct` rate-limited? 0.0.1 polls the head job only. Depends: schedulers §3.2; §12 Q3.
7. Do compute nodes have outbound HTTPS for pipelines, containers and plugins (events do not need it)? Depends: dev-env §15.3 "Launch"; §12 Q6; CH-001.

**Storage:**
8. Which shared file system holds the runs root, and with what quota, purge policy and quota command? Depends: architecture §7.2; §12 Q4.
9. Is a line appended on a compute node promptly visible on the login node, and are file locks reliable (new)? Depends: architecture §13.1 (spool cursor).
10. Can a user create 0700 directories under that root, or do group ACLs override the mode (new)? Depends: dev-env §15.3 req. 5.

**Auth (later only; 0.0.1 needs only Unix accounts and SSH):**
11. Which identity provider would a shared Spectio use (OIDC or SAML), and may a service node submit jobs on users' behalf? Depends: authentication-and-access §0; #14, #20.
12. Is slurmrestd offered to users, and with which tokens? Is `PrivateData=jobs` set? Depends: schedulers §3.3; §12 Q1, Q7; #59.

**Kubernetes (later only):**
13. Is Kueue installed on EMBL's Kubernetes? Can a project get its own namespace with PodSecurity `restricted`? Depends: schedulers §4; §12 Q5; #53, #54.

## 5. Go / no-go

**Recommendation: GO for P1 now; GO for code after P1, under the conditions below.** The backlog is large (123 open, 200 partly applied), but 70 of the 82 open blockers and majors belong to features that left 0.0.1, and 7 of the remaining 12 are decided or applied in their 0.0.1 part. This also answers #52: what stands before code is short.

**Conditions before the first line of product code (the GO gate after P1):**
- **C1.** Thomas answers [#52](inbox.md). This synthesis supports (b): code first, full review circuit for product code and security boundaries only.
- **C2.** The driven-run part of api §14 (row 1) is P1's first task; it is decided (#36 a).
- **C3.** Decisions D1–D4 below are answered, or P1 records the recommended option as assumed.
- **C4.** P1 turns rows 1–13 of §3a into tasks with tests, one test per §15.3 security requirement.

**Conditions before the 0.0.1 tag (not before coding):**
- **C5.** EMBL IT answers Q1–Q4 and Q7–Q10, or another first site does; sind `slurm-mini` covers development ([dev-env §4](../specs/dev-environment-and-testing.md)).
- **C6.** Spike sec-single-mode confirms the three browser behaviours of §15.3 (SSE cookie, `SameSite=Strict` after a cross-site link, `Origin` on writes).
- **C7.** The Snakemake head job is checked on failure scenarios and long runs (T3 covered `happy` only); otherwise the §15.1 fallback (head on the login node) applies.
- **C8.** The GitHub App exists for release-please ([#8](inbox.md)), and the first release commit carries `Release-As: 0.0.1` ([dev-env §15.2](../specs/dev-environment-and-testing.md)).

**No-go trigger.** If login nodes forbid long-running user processes or SSH forwarding (Q1, Q3), §15.3 does not hold at that site; the cut goes back to Thomas (a service node, or a remote runner, both bringing back #12–#14).

**What Thomas decides** (the [inbox](inbox.md) entries that matter for 0.0.1):

| | Question | Entry | Recommendation |
|---|---|---|---|
| D0 | Code first, and a lighter process for tooling | #52 (open, critical) | (b) |
| D1 | Relaunch and parameter history out of 0.0.1 | #61 (assumed) | confirm (a) |
| D2 | How a workflow reaches the launch form | #34, SR-056 part (open) | the smallest contract: a pipeline location the user's account can read (a path or a Git URL and revision), with its parameter schema read from it; no catalogue and no `POST /workflows` in 0.0.1 |
| D3 | What engine events may carry | #55 (reserved) | (a): `nf-spectio` sends no `script` or `env`; `homeDir`, `commandLine`, `configText` and `env` are never stored |
| D4 | Can 0.0.1 cancel a run? | [#62](inbox.md#62-assumed-001-can-cancel-a-run) (assumed; a gap in §3a) | yes: one Cancel action, with the drain rule of schedulers §2 |
| — | Attempt state `aborted` | #56 (assumed) | confirm (a); it is visible in the 0.0.1 run detail |
| — | GitHub App for releases | #8 (open) | needed before the tag only |

Not needed for 0.0.1, so they can wait: #12, #14, #15 (remainder), #16 (later versions), #17, #32, #53, #54, #57–#60.
