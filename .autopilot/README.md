# .autopilot

- **`state.json`**: one status per step of `docs/playbooks/pipeline.yaml`. The statuses are `pending`, `running`, `done`, `failed`, `blocked`, `waiting_human` and `skipped`.
- **`journal.md`**: an append-only log of every tick.

Both files are committed. Every session, local or cloud, and every routine reads them, so a run that stops is resumed by whichever session runs `/autopilot` next.

**Do not edit statuses by hand, except:**
- `blocked` → `pending`, to retry a step;
- `waiting_human` → `done`, after deciding something outside the inbox.
