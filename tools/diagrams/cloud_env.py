#!/usr/bin/env python3
"""What a Claude Code cloud session can run: spike D2, 2026-10-26.

Writes docs/assets/diagrams/cloud-env_{light,dark}.{svg,png}.

Every fact and number comes from the spike, not from memory:
- docs/research/spike-cloud-env-2026-10-26.md (Setup, Result, Network)
- spikes/cloud-env/LOG.md (commands, exit codes, wall times)
Measured there: 4 vCPU, 16 091 MiB, no swap; hybrid cgroups (cpu, memory, pids
on v1 hierarchies used by the sandbox, cgroup2 at /sys/fs/cgroup/unified with
only hugetlb); cold times docker hello-world 1.7 s, Snakemake local 2.3 s,
Playwright board 3.9 s, Nextflow local hello 4.6 s, Compose up 19.4 s,
mermaid-cli 21 s; kind create failed after 88 s and 250 s; GitHub 403 outside
the session's repository scope, pinned release assets 302; Docker Hub 429
after about 6 anonymous pulls, fixed with --registry-mirror=https://mirror.gcr.io;
43 URLs probed, none blocked by the domain allowlist.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 1080

# cold wall times in seconds (spike note, Result table; LOG.md sections 1, 2, 6-9)
TIMINGS = (
    ("docker run hello-world", 1.7),
    ("Snakemake local run", 2.3),
    ("Playwright board PNG", 3.9),
    ("Nextflow hello, 4 tasks", 4.6),
    ("Compose up, 3 services", 19.4),
    ("mermaid-cli, cold", 21.0),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=31)
    t = theme
    s.heading(60, 62, "What a cloud session can run",
              "spike D2: engines, Compose and the UI tools work here; SLURM and Kubernetes clusters do not")

    # -- the VM ----------------------------------------------------------------
    s.frame(60, 120, 1110, 610, fill="neutral", colour=t.muted, dashed=True)
    s.text(84, 156, "cloud session", size=20, anchor="start", weight="bold")
    s.text(232, 156, "Firecracker VM · Ubuntu 24.04 · root", size=14, anchor="start", colour=t.dim)
    # 4 vCPU: four small dies with pins
    for i in range(4):
        x = 760 + i * 40
        s.poly([(x, 136), (x + 24, 136), (x + 24, 160), (x, 160)], fill="input", width=1.4, amount=0.4)
        for k in range(3):
            p = 141 + k * 7
            s.line(x - 5, p, x, p, width=1.1, amount=0.2, passes=1)
            s.line(x + 24, p, x + 29, p, width=1.1, amount=0.2, passes=1)
    s.text(924, 154, "4 vCPU", size=15, anchor="start")
    # 16 GiB: a memory stick
    mx = 1000
    s.poly([(mx, 136), (mx + 80, 136), (mx + 80, 160), (mx, 160)], fill="done", width=1.4, amount=0.4)
    for k in range(4):
        s.poly([(mx + 6 + k * 18, 140), (mx + 18 + k * 18, 140), (mx + 18 + k * 18, 152), (mx + 6 + k * 18, 152)],
               fill="surface", width=1.0, amount=0.2)
    s.text(mx + 90, 154, "16 GiB", size=15, anchor="start")

    # -- band: works -----------------------------------------------------------
    s.shade(80, 178, 1070, 274, fill="done", opacity=0.7)
    s.text(96, 202, "works", size=16, anchor="start", colour=t.good, weight="bold")
    cap = 384

    # 1 Docker + Compose: containers on a hull
    s.poly([(118, 318), (312, 318), (296, 346), (134, 346)], fill="input", width=1.7)
    for i, (lab, fill) in enumerate((("nginx", "work"), ("postgres", "docs"), ("alpine", "gate"))):
        x = 126 + i * 62
        s.poly([(x, 280), (x + 58, 280), (x + 58, 316), (x, 316)], fill=fill, width=1.4, amount=0.5)
        for r in range(1, 4):
            s.line(x + r * 14.5, 284, x + r * 14.5, 312, colour=t.muted, width=1, amount=0.2, passes=1)
        s.text(x + 29, 303, lab, size=11.5)
    s.poly([(170, 242), (228, 242), (228, 278), (170, 278)], fill="surface", width=1.4, amount=0.5)
    s.text(199, 265, "hello", size=11.5)
    s.tick(292, 236, size=12, width=3)
    s.step(215, cap, 1, "Docker 29.9 + Compose")
    s.text(215, cap + 24, "Compose with health checks", size=13.5, colour=t.dim)
    s.text(215, cap + 44, "start dockerd by hand, each session", size=13.5, colour=t.dim)

    # 2 Nextflow: three tasks fan into one
    for i in range(3):
        y = 222 + i * 44
        s.chip(400, y, 74, "SAY", fill="work", h=32)
        s.arrow(478, y + 16, 522, 270 + i * 8)
    s.chip(526, 262, 96, "COLLECT", fill="work", h=32)
    s.tick(600, 236, size=12, width=3)
    s.step(500, cap, 2, "Nextflow 26.10")
    s.text(500, cap + 24, "local hello, also `-with-docker`", size=13.5, colour=t.dim)
    s.text(500, cap + 44, "pinned release asset, 3 s install", size=13.5, colour=t.dim)

    # 3 Playwright + Chromium: the board renderer in a browser
    b = s.browser(680, 214, 168, 126, url="RunDetail")
    s.raw(f'<rect x="{b.x + 8:.1f}" y="{b.y + 36:.1f}" width="30" height="82" rx="2" fill="{t.fill("neutral")}" '
          f'stroke="{t.muted}" stroke-width="1"/>')
    for i, hgt in enumerate((40, 62, 30, 52, 70)):
        bx = b.x + 50 + i * 21
        s.raw(f'<rect x="{bx:.1f}" y="{b.y + 116 - hgt:.1f}" width="14" height="{hgt}" rx="2" '
              f'fill="{t.fill("input")}" stroke="{t.ink}" stroke-width="0.8"/>')
    s.tick(872, 232, size=12, width=3)
    s.step(764, cap, 3, "Playwright + Chromium")
    s.text(764, cap + 24, "pre-installed 1.63.0", size=13.5, colour=t.dim)
    s.text(764, cap + 44, "the board renderer works", size=13.5, colour=t.dim)

    # 4 mermaid-cli: a page with a small flow drawn on it
    s.page(960, 212, 116, 134, fill="surface", lines=0)
    for k, (fx, fy) in enumerate(((990, 240), (1040, 240), (1015, 302))):
        s.rect(Box(fx - 18, fy - 12, 36, 24, "docs"), rx=4)
    s.arrow(1008, 240, 1020, 240)
    s.arrow(992, 254, 1008, 288)
    s.arrow(1040, 254, 1024, 288)
    s.tick(1090, 236, size=12, width=3)
    s.step(1022, cap, 4, "mermaid-cli 11")
    s.text(1022, cap + 24, "as root it needs `--no-sandbox`", size=13.5, colour=t.dim)
    s.text(1022, cap + 44, "reuses the Chromium in place", size=13.5, colour=t.dim)

    # -- band: partly ------------------------------------------------------------
    s.shade(80, 468, 420, 246, fill="gate", opacity=0.9)
    s.text(96, 492, "partly", size=16, anchor="start", colour=t.warn, weight="bold")
    s.terminal(100, 504, 380, 116, ("$ snakemake --cores 2", "$ snakemake -n --executor slurm",
                                    "$ snakemake --executor slurm"), size=12.5)
    s.tick(456, 543, size=7)
    s.tick(456, 564, size=7)
    s.cross(456, 586, size=6)
    s.step(290, 656, 5, "Snakemake 9.27")
    s.text(290, 680, "local run and dry run work", size=13.5, colour=t.dim)
    s.text(290, 700, "no cluster to submit to, no `sacct`", size=13.5, colour=t.dim)

    # -- band: does not ------------------------------------------------------------
    s.shade(516, 468, 634, 246, fill="problem", opacity=0.9)
    s.text(532, 492, "does not", size=16, anchor="start", colour=t.accent, weight="bold")
    s.hpc_node(552, 512, 58, 84, busy=0, slots=4)
    s.cross(581, 554, size=20)
    s.text(581, 620, "sind", size=15)
    s.k8s_pod(672, 554, 34, fill="input")
    s.cross(672, 554, size=20)
    s.text(672, 620, "kind", size=15)
    s.step(628, 656, 6, "sind and kind")
    s.text(628, 680, "kind failed at 88 s, then 250 s", size=13.5, colour=t.dim)
    s.text(628, 700, "a session cannot boot cgroup v2", size=13.5, colour=t.dim)

    # why: the controllers sit on v1 hierarchies the sandbox itself uses
    s.text(760, 528, "v1", size=16, anchor="start", weight="bold")
    s.text(760, 600, "v2", size=16, anchor="start", weight="bold")
    xs = (792, 862, 956)
    ws = (62, 86, 62)
    for x, w, lab in zip(xs, ws, ("cpu", "memory", "pids")):
        s.rect(Box(x, 508, w, 30, "work"), rx=4)
        s.text(x + w / 2, 528, lab, size=13.5)
    s.lock(1046, 523, 12, fill="work")
    s.text(1066, 520, "held by", size=12.5, anchor="start", colour=t.dim)
    s.text(1066, 536, "the sandbox", size=12.5, anchor="start", colour=t.dim)
    s.rect(Box(792, 580, 80, 30, "neutral"), rx=4)
    s.text(832, 600, "hugetlb", size=13.5)
    for x, w, lab in zip((882, 948, 1036), (56, 78, 56), ("cpu", "memory", "pids")):
        s.rect(Box(x, 580, w, 30, "none"), colour=t.muted, dashed=True, rx=4)
        s.text(x + w / 2, 600, lab, size=13, colour=t.muted)
    s.arc(905, 540, 980, 578, lift=-16, colour=t.accent, dashed=True)
    s.cross(960, 552, size=6)
    s.text(950, 646, "sind and kind need cpu, memory, pids in v2", size=13, colour=t.dim)
    s.text(950, 666, "a cgroup2 mount gets only `hugetlb`", size=13, colour=t.dim)

    # -- the egress proxy: a wall every outbound call goes through ----------------
    wx, wy0, wy1 = 1184, 180, 712
    s.poly([(wx, wy0), (wx + 32, wy0), (wx + 32, wy1), (wx, wy1)], fill="cached", width=1.6)
    for r, y in enumerate(range(wy0 + 19, wy1, 19)):
        s.line(wx, y, wx + 32, y, colour=t.muted, width=1, amount=0.3, passes=1)
        off = 16 if r % 2 else 0
        if off:
            s.line(wx + off, y - 19, wx + off, y, colour=t.muted, width=1, amount=0.2, passes=1)
    s.step(1440, 150, 7, "every call goes through the proxy", size=18)

    def route(y: float, code: str, what: str, note: str, ok: bool) -> None:
        x0, x1 = wx + 40, 1540
        s.text(x0 + 4, y - 11, code, size=17, anchor="start", weight="bold", colour=t.good if ok else t.accent)
        s.text(x0 + 50, y - 11, what, size=13.5, anchor="start")
        if ok:
            s.arrow(x0, y, x1, y)
            s.tick(x1 - 30, y - 14, size=7)
        else:
            s.line(x0, y, 1450, y)
            s.cross(1466, y, size=8)
            s.line(1482, y, x1, y, colour=t.muted, dashed=True, amount=1.0, passes=1)
        s.text(x0 + 50, y + 20, note, size=12.5, anchor="start", colour=t.dim)

    # GitHub: the proxy serves only the repositories attached to the session
    s.folder(1556, 228, 104, 76, fill="surface", label="GitHub")
    route(248, "403", "repo outside the session scope", "also `releases/latest` and archives", ok=False)
    route(314, "302", "release asset at a pinned tag", "`releases/download/v26.10.0`", ok=True)

    # Docker Hub: anonymous rate limit on the shared egress, fixed by a mirror
    s.bucket(1608, 402, 86, 50, fill="problem")
    s.text(1608, 478, "Docker Hub", size=13.5)
    route(426, "429", "anonymous pulls, after about 6", "still 429 on retry", ok=False)
    s.bucket(1608, 520, 86, 50, fill="done")
    s.text(1608, 596, "`mirror.gcr.io`", size=13.5)
    route(544, "ok", "fix: dockerd `--registry-mirror`", "every later pull worked", ok=True)

    # the package registries
    for k in range(3):
        s.page(1566 + k * 30, 630, 24, 32, fill="input", lines=2)
    s.text(1610, 696, "PyPI, npm, Go", size=13.5)
    route(656, "ok", "package and tool hosts", "43 URLs probed, none blocked", ok=True)

    # -- cold timings, to scale --------------------------------------------------
    s.text(60, 784, "cold wall times in the session, to scale", size=21, anchor="start")
    x0, pps = 330, 60.0  # pixels per second
    y = 806
    for label, sec in TIMINGS:
        s.text(x0 - 14, y + 15, label, size=14, anchor="end")
        s.raw(f'<rect x="{x0}" y="{y}" width="{sec * pps:.1f}" height="20" rx="3" fill="{t.fill("bar_green")}" '
              f'stroke="{t.ink}" stroke-width="1"/>')
        s.text(x0 + sec * pps + 10, y + 15, f"{sec:g} s", size=14, anchor="start", weight="bold")
        y += 28
    s.line(x0, y + 2, x0 + 22 * pps, y + 2, width=1.3, amount=0.4, passes=1, colour=t.dim)
    for n in range(0, 21, 5):
        x = x0 + n * pps
        s.line(x, y + 2, x, y + 9, width=1.2, amount=0.2, passes=1, colour=t.dim)
        s.text(x, y + 26, f"{n} s", size=12, colour=t.dim)

    s.text(60, H - 34, "Source: docs/research/spike-cloud-env-2026-10-26.md and spikes/cloud-env/LOG.md, "
                       "measured 2026-10-26 · tools/diagrams/cloud_env.py",
           size=12.5, anchor="start", colour=t.dim)
    s.text(60, H - 12, "Some proxy hosts were not tested against a Custom allowlist; see the spike note, "
                       "follow-up 3", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "cloud-env")
