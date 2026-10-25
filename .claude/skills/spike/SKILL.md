---
name: spike
description: Run a time-boxed technical spike to confirm or kill a risk from a review (e.g. "can a cloud session run sind and kind", "Tower protocol payload for nf-core/rnaseq 3.27", "Snakemake logger events for a checkpoint", "slurmrestd data_parser negotiation"). Works in a git worktree, never in main, and ends with a dated research note.
argument-hint: "<spike-name> <question>"
disable-model-invocation: true
---

# Spike: $0

Question: $ARGUMENTS

1. **Prepare.** Use the `using-git-worktrees` skill to create a worktree on branch `spike/$0`. Work only under `spikes/$0/`.
2. **Define success.** Write the question as a yes/no or a number, the time box (default: 60 minutes of work), and what result would change which spec section.
3. **Run.** Use real tools at pinned versions (see `docs/specs/dev-environment-and-testing.md`). Record every command and its output in `spikes/$0/LOG.md`. Save raw outputs, such as JSON payloads and logs, as fixtures under `spikes/$0/fixtures/` with the tool version in the file name.
4. **Write it up** as `docs/research/spike-$0-<date>.md`: question, setup, result, evidence (paths to fixtures), what it changes in the specs, and follow-ups.
5. **Hand over.** Commit the note and the fixtures on the spike branch and open a PR. Throwaway code stays on the branch and is not merged into main unless Thomas asks.
