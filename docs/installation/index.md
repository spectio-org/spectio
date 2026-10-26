---
icon: material/download
---
# Installation

!!! info "Nothing to install yet"
    Spectio is in its design phase. The first release, `0.1`, will be the walking skeleton: one run that goes through every part once. See the [roadmap](../roadmap/index.md).

There will be three ways to run Spectio, from the smallest to the largest. All of them run the same code.

<div class="grid cards" markdown>

-   :material-language-python:{ .lg } **Python package**

    ---

    `pip install spectio` on a laptop or a login node. It has the CLI and the runner; add the server with `spectio[server]`. Data stays in SQLite.

-   :material-docker:{ .lg } **Docker Compose**

    ---

    For a lab server: the server, a Postgres database and object storage, with optional profiles for depictio and a test identity provider.

-   :simple-kubernetes:{ .lg } **Kubernetes**

    ---

    For an institute: a Helm chart, with runners in the cluster or on the HPC login nodes.

</div>

**The runner on your cluster** is a small program on the login node or in the cluster. It only makes outgoing HTTPS calls to the server, so no port needs to be opened on the HPC side.

Design details: [packaging](../specs/architecture-plugins-and-packaging.md#7-packaging-and-the-three-deployments) and [schedulers](../specs/schedulers-and-monitoring.md#6-running-the-runner-on-hpc).
