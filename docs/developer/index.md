---
icon: material/code-tags
---
# Developer documentation

The specifications, where the work stands, and what was decided.

<div class="grid cards" markdown>

-   :material-file-tree:{ .lg } **[Documentation map](../map.md)**

    ---

    Every specification and the topic it owns. Start here.

-   :material-progress-check:{ .lg } **[Progress](../progress/index.md)**

    ---

    Where the work stands, wave by wave.

-   :material-book-open-variant:{ .lg } **[Specifications](../specs/synthesis.md)**

    ---

    How Spectio is designed, one topic per spec.

-   :material-scale-balance:{ .lg } **[Decisions](../decisions/log.md)**

    ---

    What was decided, when, and why.

</div>

## Contributing

- English for everything in the repository; one spec owns each topic; section numbers stay stable.
- Every change leaves its docs and passes `python3 tools/docs/check.py`.
- Releases: [Claim the package names](claim-package-names.md) lists what Thomas does on the Nextflow registry and on PyPI before the first release.
- Details: [CONTRIBUTING](https://github.com/weber8thomas/spectio/blob/main/CONTRIBUTING.md) and the [documentation system](../specs/documentation-system.md).
