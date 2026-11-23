# Code review · P3-ui05a, notification items carry the engine and the run's end time

`code-reviewer` and `security-reviewer` on `autopilot/P3-ui05a`, 2026-11-11. Format: [README.md](../README.md).

```text
CODE  step=P3-ui05a  review=approve b/M/m=0/0/1  security=changes-fixed b/M/m=0/1/1  rounds=2  simplify=skipped -0/+0  tests=pass
```

| Id | Severity | Finding | Status |
|---|---|---|---|
| CR-P3UI05A-01 | minor | `NotificationsBell` test fixtures `FAILED` and `DONE` have no `engine` field and are not typed as `Notification` | open, minor |
| SEC-P3UI05A-01 | major | an ended run's `at` was `ended_at`, the producer's clock; a future end sat first and "mark all read" moved the mark past later items | fixed in `df817748`: `at` uses `min(ended_at, state_changed_at)`; `test_an_end_in_the_future_is_bounded_by_the_server_clock` |
| SEC-P3UI05A-02 | minor | `up_to` from the client is unbounded, so `9999-12-31` silences notifications for good; pre-existing | open, minor, same sink as -01 |

## Assumptions

- A NULL `state_changed_at` falls back to `ended_at`.
- An adopted run keeps its true `ended_at`.
- Spec change: [api §5.9](../../specs/api-and-data-model.md) states the bound.
