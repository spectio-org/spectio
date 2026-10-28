#!/usr/bin/env python3
"""kind and Kueue clusters in CI: step T4, 2026-10-28.

Writes docs/assets/diagrams/t4-kind-kueue_{light,dark}.{svg,png}.

Every fact comes from docs/progress/W3/T4.md, docs/research/spike-t4-ci-2026-10-28.md (ServiceAccounts),
dev/k8s/ and tests/k8s/:
- the repository is mounted into every kind node at its own path (dev/k8s/cluster.sh kind_config);
- k8s-mini: one node; failures.yaml gives an OOMKilled pod (exit 137), a Job and a Pod over their deadline,
  a Job whose pod exits 3; Nextflow 25.10.9 creates one bare Pod per task, 26.10.4 one Job per task;
- k8s-kueue: control plane + 2 workers; cq-tight has 1 CPU (dev/k8s/kueue-queues.yaml); kueue-wait.yaml
  submits 3 one-CPU Jobs: 1 admitted, 2 listed by the visibility API at positions 0 and 1;
- the §4 Roles refused pods/status get (both heads), pods delete and jobs/status get (26.10), and Kueue
  workloads (runner); tests/k8s/rbac.yaml grants them, and T4 runs saw 0 refusals (403).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 900


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=44)
    t = theme
    s.heading(50, 58, "T4 · kind and Kueue clusters, built in CI",
              "`ubuntu-24.04` GitHub runner · `k8s-mini` and `k8s-kueue` · the Nextflow heads and the runner "
              "each under their own ServiceAccount")

    # == 1 -- the runner builds kind clusters and mounts the repository into every node ==============
    top = 150
    r = s.runner(50, top + 40, w=170, h=62, label="GitHub runner")
    s.folder(80, top + 140, 60, 44, fill="input")
    s.text(150, top + 168, "repository", size=14, anchor="start")
    nx = 300
    for i in range(3):
        s.hpc_node(nx + i * 64, top + 30, w=48, h=64, busy=1 if i else 2, slots=3)
        s.folder(nx + i * 64 + 8, top + 104, 32, 24, fill="input")
    s.text(nx + 88, top + 152, "kind nodes, each with", size=13.5, colour=t.dim)
    s.text(nx + 88, top + 170, "the repository at its own path", size=13.5, colour=t.dim)
    s.arrow(r.right + 6, top + 162, nx - 4, top + 120, dashed=True, colour=t.dim)
    s.text(nx + 88, top + 200, "task pods mount it as a hostPath", size=13.5, colour=t.dim)
    s.step(240, top + 260, 1, "the runner builds the cluster")

    # == 2 -- k8s-mini: failure objects and 25.10's bare Pods =========================================
    mx = 560
    s.shade(mx, top, 430, 230, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(mx + 16, top + 26, "`k8s-mini` · 1 node", size=15, anchor="start", weight="bold")
    fails = (("OOMKilled", "exit 137"), ("deadline", "Job and Pod"), ("exit 3", "Job failed"))
    for i, (a, b) in enumerate(fails):
        cx = mx + 70 + i * 110
        s.k8s_pod(cx, top + 82, 26, fill="problem")
        s.text(cx, top + 130, a, size=14, weight="bold")
        s.text(cx, top + 148, b, size=12.5, colour=t.dim)
    s.text(mx + 16, top + 196, "Nextflow 25.10: one bare Pod per task", size=13.5, anchor="start")
    for i in range(3):
        s.k8s_pod(mx + 330 + i * 30, top + 190, 12, fill="input")
    s.text(mx + 16, top + 216, "26.10: one Job per task", size=12.5, anchor="start", colour=t.dim)
    s.step(mx + 215, top + 260, 2, "failure objects as fixtures")

    # == 3 -- k8s-kueue: cq-tight has 1 CPU, one Workload admitted, two waiting ======================
    kx = 1040
    s.shade(kx, top, 510, 230, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(kx + 16, top + 26, "`k8s-kueue` · 2 workers · Kueue", size=15, anchor="start", weight="bold")
    s.bucket(kx + 110, top + 52, 130, 100, fill="done")
    s.k8s_pod(kx + 110, top + 112, 22, fill="done")
    s.text(kx + 110, top + 176, "`cq-tight` · 1 CPU", size=13.5)
    s.text(kx + 110, top + 196, "1 admitted", size=13.5, colour=t.good)
    for i in range(2):
        cx = kx + 300 + i * 100
        s.k8s_pod(cx, top + 108, 22, fill="gate")
        s.hourglass(cx, top + 62, size=8)
        s.text(cx, top + 152, f"position {i}", size=13.5)
    s.arrow(kx + 270, top + 108, kx + 190, top + 108, dashed=True, colour=t.dim)
    s.text(kx + 350, top + 196, "2 waiting, from the visibility API", size=13.5, colour=t.accent)
    s.step(kx + 255, top + 260, 3, "Workloads waiting for quota")

    # == 4 -- ServiceAccounts: the §4 Roles against the measured ones =================================
    by = 500
    s.text(50, by, "ServiceAccount", size=15, anchor="start", weight="bold")
    s.text(330, by, "§4 Role, spec", size=15, anchor="start", weight="bold")
    s.text(820, by, "measured Role, `tests/k8s/rbac.yaml`: added", size=15, anchor="start", weight="bold")
    rows = (
        ("`nf-head-26`", "Nextflow 26.10 head", "refused: exit 1 in 7 s",
         ("`pods/status get`", "`pods delete`", "`jobs/status get`")),
        ("`nf-head-25`", "Nextflow 25.10 head", "refused: exit 1 in 8 s", ("`pods/status get`",)),
        ("`spectio-runner`", "the runner", "Workloads forbidden", ("`workloads get, list, watch`",)),
    )
    for i, (sa, who, spec, added) in enumerate(rows):
        ry = by + 50 + i * 78
        s.lock(70, ry, 13, fill="docs")
        s.text(96, ry + 2, sa, size=14, anchor="start")
        s.text(96, ry + 22, who, size=12.5, anchor="start", colour=t.dim)
        s.cross(340, ry + 2, size=8)
        s.text(360, ry + 7, spec, size=14, anchor="start", colour=t.accent)
        s.arrow(640, ry + 2, 800, ry + 2, colour=t.dim)
        x = 820
        for v in added:
            s.text(x, ry + 7, v, size=13, anchor="start", colour=t.accent, weight="bold")
            x += len(v) * 7.6 + 18
        s.tick(x + 6, ry + 2, size=7)
    s.text(820, by + 50 + 3 * 78 - 12, "T4 runs: 0 refusals (403); heads use every grant they get",
           size=13.5, anchor="start", colour=t.good)
    s.text(820, by + 50 + 3 * 78 + 8, "task pods run as `default`, with no token", size=13.5, anchor="start",
           colour=t.dim)
    s.step(800, by + 330, 4, "the §4 Roles were not sufficient; the replacement Roles are")

    s.text(W - 50, H - 20, "source: docs/research/spike-t4-ci-2026-10-28.md · tests/k8s/ · dev/k8s/ · "
           "docs/progress/W3/T4.md", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t4-kind-kueue")
