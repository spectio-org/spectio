#!/usr/bin/env python3
"""Isolated, parallel scenarios: step T5, 2026-10-28.

Writes docs/assets/diagrams/t5-scenarios_{light,dark}.{svg,png}.

Every fact comes from dev/scenario.py, tests/scenarios/parallel.sh and docs/progress/W3/T5.md:
- id N owns the name spx-N (Docker network, Compose project, sind realm or kind cluster), the ports
  20000+100*N .. +99 and the data directory .scenarios/N/ (dev/scenario.py names());
- slurm-mini scenarios: sind realm spx-N with cluster mini, the tools bootstrapped into .scenarios/N/;
  two of them hold the same cluster name, mini, apart only by their realm;
- k8s-mini: kind cluster spx-N on network spx-N, API on port 20000+100*N+1, kubeconfig in .scenarios/N/;
- the Compose project is reserved and reported, not started (no product yet);
- down removes the realm or cluster, the network and the data directory; parallel.sh compares
  docker ps -a, docker network ls and docker volume ls with the state before up.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 860


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=55)
    t = theme
    s.heading(50, 58, "T5 · one id, one set of names: scenarios side by side",
              "`python3 dev/scenario.py up <scenario> --id N` · proved in CI by `tests/scenarios/parallel.sh`")

    lanes = (
        (1, "`happy-slurm-mini`", "sind realm `spx-1`", "cluster `mini`"),
        (2, "`happy-slurm-mini`", "sind realm `spx-2`", "cluster `mini`, the same name"),
        (3, "`happy-k8s-mini`", "kind cluster `spx-3`", "API on 127.0.0.1:20301"),
    )
    top, lw = 140, 470
    for i, (n, scen, cluster, note) in enumerate(lanes):
        x = 50 + i * (lw + 30)
        s.shade(x, top, lw, 470, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
        s.text(x + 18, top + 30, f"id {n} · {scen}", size=16, anchor="start", weight="bold")
        # the cluster
        if n < 3:
            for k in range(3):
                s.hpc_node(x + 40 + k * 64, top + 60, w=48, h=64, busy=k, slots=3)
        else:
            s.k8s_pod(x + 90, top + 92, 28, fill="input")
            s.lock(x + 160, top + 92, 12, fill="docs")
            s.text(x + 180, top + 97, "kubeconfig in the data dir", size=13, anchor="start", colour=t.dim)
        s.text(x + 18, top + 160, cluster, size=14.5, anchor="start")
        s.text(x + 18, top + 180, note, size=13, anchor="start", colour=t.dim)
        # network, data dir, ports, Compose
        s.text(x + 18, top + 230, f"Docker network `spx-{n}`", size=14.5, anchor="start")
        s.folder(x + 18, top + 260, 44, 32, fill="input")
        s.text(x + 74, top + 282, f"`.scenarios/{n}/`", size=14.5, anchor="start")
        if n < 3:
            s.text(x + 74, top + 302, "tools, synthetic pipeline, job output", size=12.5, anchor="start",
                   colour=t.dim)
        base = 20000 + 100 * n
        s.text(x + 18, top + 350, f"ports {base}–{base + 99}", size=14.5, anchor="start")
        s.text(x + 18, top + 380, f"Compose project `spx-{n}`: reserved, not started", size=13,
               anchor="start", colour=t.accent)
        s.tick(x + 26, top + 430, size=7)
        s.text(x + 44, top + 435, "a job writes into its own data dir only" if n < 3 else
               "its nodes sit on network `spx-3` alone", size=13, anchor="start", colour=t.good)
    s.step(W / 2, top + 500, 1, "up, all at once: no shared name, port or path")

    by = 700
    s.text(50, by, "`dev/scenario.py down N`", size=16, anchor="start", weight="bold")
    s.text(50, by + 26, "realm or cluster, network, data dir: gone", size=14, anchor="start", colour=t.dim)
    s.arrow(430, by - 4, 560, by - 4, colour=t.dim)
    s.text(580, by, "`docker ps -a` · `docker network ls` · `docker volume ls`: same as before `up`",
           size=14.5, anchor="start")
    s.text(580, by + 26, "`sind get realms` and `kind get clusters`: no `spx-*`", size=14.5, anchor="start")
    s.tick(565, by + 50, size=7)
    s.text(580, by + 55, "nothing left behind", size=14, anchor="start", colour=t.good)
    s.step(W / 2, by + 100, 2, "down, all at once: nothing left")

    s.text(W - 50, H - 16, "source: dev/scenario.py · tests/scenarios/parallel.sh · docs/progress/W3/T5.md",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "t5-scenarios")
