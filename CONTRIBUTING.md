# Contributing

Until code exists, contributions are documentation and design changes.

## Workflow

1. **Branch from `main`.** Name the branch `docs/<topic>`, `design/<topic>` or `research/<topic>`.
2. **Change the spec that owns the topic.** Each topic has exactly one owning spec, listed in [`docs/map.md`](docs/map.md). Other docs link to it instead of repeating it.
3. **Record the decision.** If the change decides something, add a dated entry to [`docs/decisions/log.md`](docs/decisions/log.md). Add a decision record too when the decision is significant ([template](docs/decisions/README.md)).
4. **Keep the research.** New facts gathered on the way go in a new dated note in `docs/research/`.
5. **Snapshot the UI canvas.** If the design changed, export the boards into `design/ui-canvas/` so the repository holds the version the specs describe.
6. **Open a pull request.** CI builds the docs site in strict mode, which also catches broken internal links.

## Writing style

- English, plain words, short sentences.
- Concrete examples beat abstractions: a real nf-core pipeline, a real command, a real field name.
- State the source of every external fact. Mark anything unverified as **[to be validated]**.
