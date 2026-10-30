# Triage policy — what the autopilot may decide alone

The autopilot (`/autopilot`, defined in `.claude/skills/autopilot/SKILL.md`) triages review findings with this policy, so that Thomas only sees what needs him. Every decision it takes is written in the review file and in `.autopilot/journal.md`, and can be reverted.

## Auto-accept

A finding is accepted automatically when **all** of these hold:
1. **Confirmed.** The orchestrator re-read the quoted passages and reproduced the problem, or two different agents reported it independently.
2. **Severity is minor or major,** or it is a pure fact correction (see below).
3. **Local fix.** The proposal changes at most two sections of the owning spec, plus links elsewhere.
4. **No decision reversed.** It does not contradict a dated entry in `docs/decisions/log.md`.
5. **Out of the reserved topics** listed below.

**Fact corrections.** A `fact-checker` correction backed by a primary source (code at a version, or official docs) is accepted at any severity, unless it invalidates a decision in the log. Then it goes to the inbox with the evidence.

## Reserved for Thomas (always to the inbox)

- Product scope and the MVP cut. Dropping or adding a feature or an engine.
- Roles, permissions defaults, security posture defaults, auth modes.
- Licences, vendoring, anything with legal effect.
- Anything that commits other people: requests to the depictio or LabID teams, EMBL IT questions.
- Money and infrastructure: paid services, hosting accounts (Cloudflare, Codespaces quota), domains.
- Irreversible actions: force-push, deleting branches or data, publishing. Merging the promotion PR into `main` is allowed for now once every check passed (Thomas, inbox #3, 2026-10-26); any other merge into `main` stays reserved.
- The `GO` gate.

## Inbox and assumptions

Findings that are not auto-accepted go to `docs/reviews/inbox.md`. Each entry has:
- a question with two or three options and a recommended one;
- what is blocked until it is answered.

When the recommended option is reversible, the autopilot **assumes** it and continues (standing rule, Thomas, 2026-10-30, [autopilot §10](autopilot.md#10-unattended-mode-thomas-2026-10-30); before that, only when it affected docs alone). It marks the decision `assumed — pending Thomas` in the spec and the log, so nothing waits on Thomas unless it must. Steps that depend on an unanswered irreversible or reserved question stay `waiting_human`.

When Thomas answers in the inbox (`Answer: B`), the next autopilot tick:
- applies the answer;
- reverts any assumption that differs from it;
- closes the entry.

## Reject

A finding is rejected automatically, with the reason recorded, when:
- it cannot be reproduced from the quoted evidence;
- it duplicates an applied or rejected finding;
- it only asks for style changes.
