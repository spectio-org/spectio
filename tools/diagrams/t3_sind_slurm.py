#!/usr/bin/env python3
"""sind SLURM clusters in CI: step T3, 2026-10-28.

Writes docs/assets/diagrams/t3-sind-slurm_{light,dark}.{svg,png}.

Every fact comes from docs/progress/W3/T3.md, docs/research/spike-t3-ci-2026-10-28.md, dev/slurm/ and
tests/slurm/:
- the data directory (tools, pipelines, work) is mounted into every sind node at its own path
  (dev/slurm/cluster.sh); the engines run as user spx on the submitter, as on a login node;
- slurm-site: controller, db (slurmdbd), submitter, worker-[0-1] in htc, worker-2 in bigmem, account capped
  with MaxJobs=1 (dev/slurm/site.yaml); slurm-rest adds an api node, slurmrestd with JWT;
- probes (tests/slurm/scenarios.sh probes): OUT_OF_MEMORY, TIMEOUT, AssocMaxJobsLimit, a maintenance
  reservation (ReqNodeNotAvail, "Reserved for maintenance"), NODE_FAIL after a power cut of worker-2;
- Snakemake task jobs end FAILED 1:0 whatever the tool returned; the synthetic oom mode ends FAILED 137:0.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 900


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=33)
    t = theme
    s.heading(50, 58, "T3 · SLURM clusters with sind, built in CI",
              "`ubuntu-24.04` GitHub runner · `slurm-mini`, `slurm-site`, `slurm-rest` · the synthetic pipelines, "
              "probes and slurmrestd")

    # == 1 -- the runner builds the cluster; the data directory is in every node ======================
    top = 160
    r = s.runner(50, top + 30, w=170, h=62, label="GitHub runner")
    s.folder(80, top + 130, 60, 44, fill="input")
    s.text(150, top + 150, "tools,", size=14, anchor="start")
    s.text(150, top + 168, "pipelines", size=14, anchor="start")
    s.text(135, top + 205, "mounted at the same path", size=13, colour=t.dim)
    s.step(135, top + 260, 1, "the runner builds it")

    # == 2 -- slurm-site ================================================================================
    cx = 300
    s.shade(cx, top - 20, 760, 270, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(cx + 16, top + 6, "`slurm-site` · Slurm 26.05.5", size=15, anchor="start", weight="bold")
    s.arrow(r.right + 8, top + 60, cx - 6, top + 80, colour=t.dim)
    # controller and db
    s.cog(cx + 50, top + 60, 18)
    s.text(cx + 50, top + 104, "controller", size=13.5)
    s.ellipse(cx + 140, top + 44, 26, 9, fill="docs")
    s.line(cx + 114, top + 44, cx + 114, top + 80)
    s.line(cx + 166, top + 44, cx + 166, top + 80)
    s.ellipse(cx + 140, top + 80, 26, 9, fill="docs")
    s.text(cx + 140, top + 112, "slurmdbd", size=13.5)
    s.text(cx + 140, top + 128, "`capped`: MaxJobs=1", size=12, colour=t.dim)
    # submitter
    s.terminal(cx + 30, top + 146, 170, 76, ("$ nextflow", "$ snakemake"))
    s.text(cx + 115, top + 240, "submitter, user spx", size=13, colour=t.dim)
    # partitions
    px = cx + 250
    s.shade(px, top + 30, 220, 180, fill="work", opacity=0.35, colour=t.dim)
    s.text(px + 110, top + 54, "`htc`", size=15, weight="bold")
    for i in range(2):
        s.hpc_node(px + 30 + i * 100, top + 70, w=54, h=70, busy=1 + i, slots=2)
        s.text(px + 57 + i * 100, top + 160, f"worker-{i}", size=12.5, colour=t.dim)
    s.text(px + 110, top + 190, "2 CPU, 1.5 GiB each", size=12, colour=t.dim)
    bx = px + 240
    s.shade(bx, top + 30, 150, 180, fill="input", opacity=0.35, colour=t.dim)
    s.text(bx + 75, top + 54, "`bigmem`", size=15, weight="bold")
    s.hpc_node(bx + 48, top + 70, w=54, h=70, busy=1, slots=2)
    s.text(bx + 75, top + 160, "worker-2", size=12.5, colour=t.dim)
    s.text(bx + 75, top + 190, "2 CPU, 3 GiB", size=12, colour=t.dim)
    s.step(cx + 380, top + 280, 2, "two partitions, accounting, limits")

    # == 3 -- slurm-rest: api node =====================================================================
    ax = 1110
    s.shade(ax, top - 20, 440, 270, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(ax + 16, top + 6, "`slurm-rest` · `slurm-site` + api node", size=15, anchor="start", weight="bold")
    s.cog(ax + 80, top + 90, 20)
    s.lock(ax + 112, top + 112, 11, fill="docs")
    s.text(ax + 80, top + 150, "slurmrestd", size=14, weight="bold")
    s.text(ax + 80, top + 170, "JWT, key inside the node", size=12.5, colour=t.dim)
    for i, ep in enumerate(("`/jobs`", "`/nodes`", "`/partitions`", "`/slurmdb/jobs`")):
        s.page(ax + 220, top + 40 + i * 46, 30, 36, fill="surface", lines=2)
        s.text(ax + 262, top + 64 + i * 46, ep, size=13.5, anchor="start")
    s.step(ax + 220, top + 280, 3, "REST answers as fixtures")

    # == 4 -- probes: what Slurm records ===============================================================
    py = 520
    s.text(50, py, "Probes on `slurm-site`: the record each one leaves", size=16, anchor="start", weight="bold")
    probes = (
        ("OOM", "`OUT_OF_MEMORY`", "exit 0:125"),
        ("time limit", "`TIMEOUT`", "1 minute"),
        ("limit", "pending", "`AssocMaxJobsLimit`"),
        ("maintenance", "pending", "`ReqNodeNotAvail`"),
        ("power cut", "`NODE_FAIL`", "worker-2"),
    )
    for i, (what, rec, detail) in enumerate(probes):
        x = 120 + i * 200
        y = py + 70
        if what == "OOM":
            s.bucket(x, y - 30, 60, 54, fill="problem")
        elif what == "time limit":
            s.hourglass(x, y, size=16)
        elif what == "limit":
            s.lock(x, y, 18, fill="gate")
        elif what == "maintenance":
            s.gate(x, y + 26, w=60, h=50, state="closed")
        else:
            s.hpc_node(x - 27, y - 35, w=54, h=70, busy=0, slots=2)
            s.cross(x, y, size=16)
        s.text(x, y + 62, what, size=14, weight="bold")
        s.text(x, y + 82, rec, size=13.5, colour=t.accent)
        s.text(x, y + 100, detail, size=12.5, colour=t.dim)
    s.step(520, py + 210, 4, "each §3.5 record seen")

    # == 5 -- what the specs miss ======================================================================
    fx = 1110
    s.text(fx, py, "Engines on SLURM", size=16, anchor="start", weight="bold")
    s.warning(fx + 12, py + 46, size=11)
    s.text(fx + 34, py + 50, "Snakemake task job: `FAILED 1:0`,", size=13.5, anchor="start")
    s.text(fx + 34, py + 70, "whatever the tool returned", size=13.5, anchor="start", colour=t.dim)
    s.warning(fx + 12, py + 112, size=11)
    s.text(fx + 34, py + 116, "synthetic `oom`: `FAILED 137:0`,", size=13.5, anchor="start")
    s.text(fx + 34, py + 136, "not `OUT_OF_MEMORY`", size=13.5, anchor="start", colour=t.dim)
    s.tick(fx + 12, py + 176, size=8)
    s.text(fx + 34, py + 182, "Snakemake head in `sbatch`: works", size=13.5, anchor="start", colour=t.good)
    s.step(fx + 200, py + 210, 5, "differences for TRIAGE3")

    s.text(W - 50, H - 20, "source: docs/research/spike-t3-ci-2026-10-28.md · dev/slurm/ · tests/slurm/ · "
           "docs/progress/W3/T3.md", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t3-sind-slurm")
