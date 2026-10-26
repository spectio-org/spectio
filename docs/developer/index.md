---
icon: material/code-tags
---
# Developer documentation

Everything technical lives here: the specifications, how the work is organised, and the evidence behind each decision.

<div class="grid cards" markdown>

-   :material-file-tree:{ .lg } **[Documentation map](../map.md)**

    ---

    Every specification and the topic it owns. Start here.

-   :material-progress-check:{ .lg } **[Progress](../progress/index.md)**

    ---

    One page per pipeline step: what changed, why, the evidence.

-   :material-robot:{ .lg } **[Autopilot](../playbooks/autopilot.md)**

    ---

    How the design phase runs unattended, with a budget.

-   :material-magnify:{ .lg } **[Reviews](../reviews/README.md)**

    ---

    Review rounds and their findings, and the inbox for Thomas.

-   :material-scale-balance:{ .lg } **[Decisions](../decisions/log.md)**

    ---

    What was decided, when, and why.

-   :material-flask:{ .lg } **[Research](../research/adoption-and-positioning-2026-10-26.md)**

    ---

    Dated notes and spikes the specifications cite.

</div>

## Contributing

- English for everything in the repository; one spec owns each topic; section numbers stay stable.
- Every change leaves its docs and passes `python3 tools/docs/check.py`.
- Details: [CONTRIBUTING](https://github.com/weber8thomas/spectio/blob/main/CONTRIBUTING.md) and the [documentation system](../specs/documentation-system.md).
