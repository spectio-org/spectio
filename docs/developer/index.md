---
icon: material/code-tags
---
# Developer documentation

The specifications, where the work stands, and what was decided.

<div class="grid cards" markdown>

-   :material-progress-check:{ .lg } **[Progress](../progress/index.md)**

    ---

    Where the work stands, wave by wave.

-   :material-book-open-variant:{ .lg } **[Specifications](../map.md)**

    ---

    How Spectio is designed: every spec, its topic and a reading order.

-   :material-scale-balance:{ .lg } **[Decisions](../decisions/log.md)**

    ---

    What was decided, when, and why.

</div>

## Contributing

- English for everything in the repository; one spec owns each topic; section numbers stay stable.
- Every change leaves its docs and passes `python3 tools/docs/check.py`.
- Releases: [Claim the package names](claim-package-names.md) lists what to do on the Nextflow registry and on PyPI before the first release.
- Details: [CONTRIBUTING](https://github.com/weber8thomas/spectio/blob/main/CONTRIBUTING.md) and the [documentation system](../specs/documentation-system.md).
