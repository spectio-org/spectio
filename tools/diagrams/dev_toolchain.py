#!/usr/bin/env python3
"""The dev toolchain: one pinned list, one install script, one doctor. Build step D3, wave W3.

Writes docs/assets/diagrams/dev_toolchain_{light,dark}.{svg,png}.

Facts and numbers measured 2026-10-27 (cloud session run, GitHub Actions run 40523940610):
- dev/versions.env holds exact pins, the sha256 of every download and image digests;
  dev/snakemake.lock.txt and dev/npm/package-lock.json hash-lock the dependency trees.
- dev/bootstrap.sh --ci installs in parallel into ~/.local/share/spectio; it runs in a
  cloud session, on a GitHub Actions ubuntu-24.04 runner and on a laptop.
- cold bootstrap --ci: cloud session 25 s, CI runner 56 s, against the 300 s budget of a
  cached cloud setup script.
- dev/doctor.sh smoke layers: cloud session skips sind and kind (cgroup v1), the other four
  ok; CI (strict, a skip fails) all six ok: docker 3 s, sind 14 s, kind 40 s, nextflow 23 s,
  snakemake 1 s, playwright 1 s. The first failure exits 1 and names the tool.
"""

from __future__ import annotations

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 730

# cold `dev/bootstrap.sh --ci` wall time, seconds
BOOT = (("cloud session", 25), ("CI runner", 56))
BUDGET = 300

# doctor layers: name, what it runs, cloud session result, CI time in seconds
LAYERS = (
    ("docker", "`hello-world`", "ok", 3),
    ("sind", "`sbatch --wait`", "skip", 14),
    ("kind", "a Job", "skip", 40),
    ("nextflow", "synthetic pipeline", "ok", 23),
    ("snakemake", "dry run", "ok", 1),
    ("playwright", "`about:blank`", "ok", 1),
)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=43)
    t = theme
    s.heading(60, 58, "One pinned list, one install script, one doctor",
              "the same `dev/bootstrap.sh` runs in three places; `dev/doctor.sh` proves each layer")

    cap = 132
    s.step(200, cap, 1, "pin")
    s.step(720, cap, 2, "install")
    s.step(1385, cap, 3, "prove")

    # -- 1 pin: the pinned list and the two lock files ----------------------------
    s.page(110, 160, 150, 184, fill="input", lines=6)
    s.lock(236, 318, 11, fill="docs")
    s.text(185, 372, "`dev/versions.env`", size=15)
    for i, ln in enumerate(("exact pins", "sha256 of every download", "image digests")):
        s.text(185, 396 + i * 20, ln, size=13.5, colour=t.dim)
    for i, name in enumerate(("`snakemake.lock.txt`", "`npm/package-lock.json`")):
        y = 480 + i * 74
        s.page(80, y, 44, 58, fill="input", lines=3)
        s.lock(114, y + 46, 7, fill="docs")
        s.text(138, y + 34, name, size=13, anchor="start")
    s.text(80, 640, "hash-locked dependency trees", size=13.5, anchor="start", colour=t.dim)

    # -- 2 install: one script, parallel strands into one folder ---------------------
    s.arrow(266, 230, 424, 190)
    s.terminal(430, 158, 300, 70, ("$ dev/bootstrap.sh --ci",), size=14)
    for i in range(5):
        y0 = 166 + i * 13
        s.arc(736, y0, 872, 182 + i * 7, lift=-8 if i % 2 else 8, width=1.4, colour=t.dim)
    s.text(804, 160, "in parallel", size=13, colour=t.dim)
    s.folder(878, 150, 112, 84, fill="done")
    s.text(934, 256, "`~/.local/share/spectio`", size=13)

    # the three places it runs
    py = 300
    # cloud session: a terminal under a cloud
    for cx, cy, r in ((478, py + 14, 18), (502, py + 4, 24), (530, py + 14, 18)):
        s.circle(cx, cy, r, fill="neutral", width=1.4)
    s.terminal(452, py + 22, 106, 60, ("$ _",), size=12)
    # CI runner
    s.runner(626, py + 22, 116, 60, label="CI runner")
    # laptop: a screen on a hinged base
    lx = 818
    s.poly([(lx, py + 12), (lx + 104, py + 12), (lx + 104, py + 74), (lx, py + 74)], fill="surface")
    s.poly([(lx + 6, py + 18), (lx + 98, py + 18), (lx + 98, py + 68), (lx + 6, py + 68)], fill="input",
           width=1.1, amount=0.3)
    s.poly([(lx - 12, py + 74), (lx + 116, py + 74), (lx + 124, py + 86), (lx - 20, py + 86)], fill="neutral")
    for cx in (505, 684, 870):
        s.arrow(580, 232, cx, py - 6 if cx != 505 else py - 28, dashed=True)
    for cx, name, note in ((505, "cloud session", "Claude Code"),
                           (684, "CI runner", "ubuntu-24.04"),
                           (870, "laptop", "same script")):
        s.text(cx, py + 112, name, size=15)
        s.text(cx, py + 132, note, size=12.5, colour=t.dim)

    # cold bootstrap times, to scale against the setup-script budget
    s.text(430, 486, "cold `bootstrap.sh --ci`, to scale", size=17, anchor="start")
    x0, pps = 560, 1.5
    y = 504
    for label, sec in BOOT:
        s.text(x0 - 12, y + 16, label, size=14, anchor="end")
        s.raw(f'<rect x="{x0}" y="{y}" width="{sec * pps:.1f}" height="22" rx="3" fill="{t.fill("bar_green")}" '
              f'stroke="{t.ink}" stroke-width="1"/>')
        s.text(x0 + sec * pps + 10, y + 16, f"{sec} s", size=14, anchor="start", weight="bold")
        y += 32
    s.text(x0 - 12, y + 16, "budget", size=14, anchor="end", colour=t.dim)
    s.rect(Box(x0, y, BUDGET * pps, 22, "none"), colour=t.muted, dashed=True, rx=3)
    s.text(x0 + BUDGET * pps / 2, y + 16, "5 min, cached cloud setup script", size=13, colour=t.dim)
    ay = y + 34
    s.line(x0, ay, x0 + BUDGET * pps, ay, width=1.3, amount=0.4, passes=1, colour=t.dim)
    for n in range(0, BUDGET + 1, 60):
        x = x0 + n * pps
        s.line(x, ay, x, ay + 7, width=1.2, amount=0.2, passes=1, colour=t.dim)
        s.text(x, ay + 24, f"{n} s", size=12, colour=t.dim)

    # -- 3 prove: the doctor, one row per smoke layer -------------------------------
    s.arrow(996, 190, 1084, 186)
    s.terminal(1090, 158, 230, 62, ("$ dev/doctor.sh",), size=14)
    cc, ci = 1478, 1604  # column centres: cloud session, CI runner
    s.text(cc, 262, "cloud session", size=15, weight="bold")
    s.text(ci, 262, "CI runner", size=15, weight="bold")
    s.shade(ci - 58, 274, 116, 6 * 52 + 4, fill="done", opacity=0.6)
    rh, top = 52, 278
    ix = 1112  # icon centre
    for k, (name, what, cloud, ci_s) in enumerate(LAYERS):
        y = top + k * rh
        cy = y + rh / 2
        if k:
            s.line(1088, y, 1666, y, colour=t.muted, width=1, amount=0.4, passes=1)
        if name == "docker":
            s.poly([(ix - 16, cy - 10), (ix + 16, cy - 10), (ix + 16, cy + 10), (ix - 16, cy + 10)], fill="input",
                   width=1.3, amount=0.3)
            for dx in (-8, 0, 8):
                s.line(ix + dx, cy - 7, ix + dx, cy + 7, colour=t.muted, width=1, amount=0.1, passes=1)
        elif name == "sind":
            s.hpc_node(ix - 15, cy - 19, 30, 38, busy=2, slots=3)
        elif name == "kind":
            s.k8s_pod(ix, cy, 17, fill="input")
        elif name == "nextflow":
            for dx in (-14, 8):
                s.poly([(ix + dx - 6, cy - 7), (ix + dx + 6, cy - 7), (ix + dx + 6, cy + 7), (ix + dx - 6, cy + 7)],
                       fill="work", width=1.2, amount=0.2)
            s.line(ix - 8, cy, ix + 2, cy, width=1.2, amount=0.1, passes=1)
        elif name == "snakemake":
            s.page(ix - 12, cy - 17, 24, 34, fill="surface", lines=3)
        else:  # playwright: a small browser window
            s.poly([(ix - 18, cy - 14), (ix + 18, cy - 14), (ix + 18, cy + 14), (ix - 18, cy + 14)], fill="surface",
                   width=1.3, amount=0.3)
            s.line(ix - 18, cy - 6, ix + 18, cy - 6, width=1, amount=0.1, passes=1)
            s.dot(ix - 13, cy - 10, 1.8, colour="#ff8787")
            s.dot(ix - 8, cy - 10, 1.8, colour="#69db7c")
        s.text(1144, cy - 3, name, size=16, anchor="start", weight="bold")
        s.text(1144, cy + 16, what, size=13, anchor="start", colour=t.dim)
        if cloud == "ok":
            s.tick(cc, cy, size=9)
        else:
            s.shade(cc - 56, y + 5, 112, rh - 10, fill="gate", opacity=0.9)
            s.text(cc, cy - 2, "skip", size=15, colour=t.warn, weight="bold")
            s.text(cc, cy + 15, "cgroup v1", size=12, colour=t.dim)
        s.tick(ci - 18, cy, size=9)
        s.text(ci + 4, cy + 6, f"{ci_s} s", size=14, anchor="start", weight="bold")
    s.line(1088, top + 6 * rh, 1666, top + 6 * rh, colour=t.muted, width=1, amount=0.4, passes=1)
    ny = top + 6 * rh + 28
    s.text(cc, ny, "clusters skip", size=12.5, colour=t.dim)
    s.text(ci, ny, "strict: a skip fails", size=12.5, colour=t.dim)
    s.cross(1104, ny + 40, size=8)
    s.text(1124, ny + 46, "first failure: exit 1, names the tool", size=15, anchor="start")

    s.text(60, H - 22, "measured 2026-10-27: cloud session run, GitHub Actions run 40523940610 · "
                       "tools/diagrams/dev_toolchain.py", size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "dev_toolchain")
