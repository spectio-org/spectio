# Decisions

- **[`log.md`](log.md)** is the running log, one dated section per working session. It stays append-only: a decision that is reversed gets a new entry saying so, and the old entry is left as it is.
- **Decision records.** A decision that is significant on its own (expensive to reverse, or likely to be questioned later) also gets its own record, `NNNN-short-title.md`, numbered in order and written from the template below.

## Template

```markdown
# NNNN. Title in a few words

Date: YYYY-MM-DD · Status: proposed | accepted | superseded by NNNN

## Context
What forces the decision: constraints, facts with sources, who is affected.

## Options
1. Option A: what it means, pros, cons.
2. Option B: …

## Decision
The option chosen, in one or two sentences.

## Consequences
What becomes easier or harder; what must now be done; which specs change (file §n).
```
