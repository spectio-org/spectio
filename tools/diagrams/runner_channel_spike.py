#!/usr/bin/env python3
"""Figure for the runner channel spike: a central UI on Kubernetes reads run outputs through a
runner on the login node, with no mount of the cluster file systems.

Writes docs/assets/diagrams/runner_channel_spike_{light,dark}.{svg,png}.

Source: docs/research/runner-channel-spike-2026-11-25.md (§1 what was built, §2 results, §3
finding 4) and the spike code on branch `spike/runner-channel`, `spikes/runner-channel/`
(`server.py`, `runner.py`, `k8s.yaml`). Facts drawn: the browser logs in once with a token and
gets an HttpOnly, Secure, SameSite=Strict cookie; it reaches the pod through the cluster's
internal ingress over HTTPS; the pod mounts no cluster file system; the runner, under the user's
own account on the login node, long-polls `GET /runner/poll` and answers
`POST /runner/reply/<id>`, so the server never connects to it; the runner opens every path
component with `O_NOFOLLOW` from the root's descriptor, refuses `..`, serves regular files only
and caps one read at 8 MiB. Numbers from §2: a held connection lasted 152 s without being cut,
about 60 ms per command, one 8 MiB range in about 0.4 s. The spike uses one shared token and
does not verify TLS; the target (per runner tokens, OIDC, an audit) is issue #355.
No real user, path or host name appears in the figure.
"""

from __future__ import annotations

import math

from sketch import Box, Sketch, Theme, main_for

W, H = 1720, 1000


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=355)
    t = theme

    def person(cx: float, cy: float, r: float = 9, fill: str = "docs") -> None:
        """A user: a head over shoulders."""
        s.circle(cx, cy, r, fill=fill)
        sh = [(cx - r * 1.7, cy + r * 3.1), (cx - r * 1.5, cy + r * 1.8), (cx - r * 0.8, cy + r * 1.3),
              (cx + r * 0.8, cy + r * 1.3), (cx + r * 1.5, cy + r * 1.8), (cx + r * 1.7, cy + r * 3.1)]
        s.poly(sh, fill=fill, amount=0.3)

    def cylinder(cx: float, top: float, w: float, h: float, fill: str) -> None:
        """A disk: an upright drum."""
        rx, ry = w / 2, 8
        s.ellipse(cx, top + h, rx, ry, fill=fill)
        s.raw(f'<rect x="{cx - rx:.1f}" y="{top:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{t.fill(fill)}"/>')
        s.line(cx - rx, top, cx - rx, top + h, amount=0.4, passes=1, width=1.5)
        s.line(cx + rx, top, cx + rx, top + h, amount=0.4, passes=1, width=1.5)
        s.ellipse(cx, top, rx, ry, fill=fill)

    def ingress(cx: float, base: float, w: float, h: float) -> None:
        """A gateway arch: the one door into the cluster."""
        r = w / 2
        spring = base - h + r  # where the arch springs from the posts
        outer = [(cx - r, base)] + [
            (cx - r * math.cos(k * math.pi / 12), spring - r * math.sin(k * math.pi / 12))
            for k in range(13)
        ] + [(cx + r, base)]
        s.poly(outer, fill="neutral", width=1.8)
        ri = r - 13
        inner = [(cx - ri, base)] + [
            (cx - ri * math.cos(k * math.pi / 12), spring + 4 - ri * math.sin(k * math.pi / 12))
            for k in range(13)
        ] + [(cx + ri, base)]
        s.poly(inner, fill="surface", width=1.4)
        s.line(cx - r - 14, base, cx + r + 14, base, width=1.8, amount=0.6, passes=1)

    def rule(x: float, y: float, ok: bool, text: str) -> None:
        if ok:
            s.tick(x, y - 5, size=8)
        else:
            s.cross(x, y - 5, size=7)
        s.text(x + 18, y, text, size=14, anchor="start")

    s.heading(50, 56, "Runner channel spike: outputs on the cluster, viewed from a central UI",
              "the pod mounts nothing; a runner on the login node, under the user's account, "
              "dials out and reads the files for it")

    # -- the laptop: a browser with the viewers --------------------------------------------------
    s.poly([(50, 184), (290, 184), (290, 344), (50, 344)], fill="neutral", width=1.8)
    b = s.browser(62, 196, 216, 136)
    s.lock(b.x + 196, b.y + 14, 8)
    for i in range(3):  # OME-Zarr tiles
        for j in range(3):
            s.raw(f'<rect x="{b.x + 14 + j * 22:.1f}" y="{b.y + 40 + i * 22:.1f}" width="20" height="20" rx="2" '
                  f'fill="{t.fill("bar_blue" if (i + j) % 2 else "bar_violet")}" stroke="{t.ink}" stroke-width="0.7"/>')
    for i in range(4):  # a CSV table
        s.raw(f'<rect x="{b.x + 94:.1f}" y="{b.y + 42 + i * 16:.1f}" width="56" height="11" rx="1" '
              f'fill="{t.fill("bar_green" if i == 0 else "surface")}" stroke="{t.ink}" stroke-width="0.7"/>')
    s.page(b.x + 162, b.y + 40, 40, 62, fill="docs", lines=3)  # a report
    s.poly([(38, 344), (302, 344), (324, 372), (16, 372)], fill="neutral", width=1.8)
    s.step(170, 414, 1, "log in, get a cookie", size=18)
    s.text(170, 440, "`/login` with the token, once", size=13.5, colour=t.dim)
    s.text(170, 460, "HttpOnly, Secure, SameSite=Strict", size=13.5, colour=t.dim)

    # browser to the ingress, and the bytes back
    s.arrow(304, 250, 562, 250, width=1.9)
    s.step(430, 232, 2, "ask for a file or a tile", size=17)
    s.text(430, 274, "HTTPS, with the cookie", size=13.5, colour=t.dim)
    s.arrow(562, 306, 304, 306, dashed=True, width=1.6)
    s.step(430, 336, 5, "the bytes come back", size=17)
    s.text(430, 360, "OME-Zarr tiles, CSV, report", size=13.5, colour=t.dim)
    s.text(430, 380, "into Spectio's own viewers", size=13.5, colour=t.dim)

    # -- the Kubernetes cluster ------------------------------------------------------------------
    s.shade(550, 120, 630, 352, fill="input", opacity=0.55, colour=t.muted, dashed=True)
    s.text(570, 150, "Kubernetes cluster", size=19, anchor="start", weight="bold")
    ingress(616, 336, 92, 112)
    s.text(616, 194, "internal ingress", size=14.5)
    s.text(616, 212, "no DNS name yet", size=12.5, colour=t.dim)

    s.frame(700, 176, 460, 280, fill="surface", colour=t.muted, dashed=True)
    s.text(716, 202, "namespace", size=14, anchor="start", colour=t.dim)
    s.arrow(666, 276, 738, 292)
    s.k8s_pod(790, 296, 46, fill="input")
    s.text(790, 372, "Spectio pod", size=15.5, weight="bold")
    s.text(790, 394, "non-root, read-only", size=13, colour=t.dim)
    s.text(790, 412, "root file system", size=13, colour=t.dim)

    # the command queue: what the runner will pick up
    for k, lab in enumerate(("`list`", "`read range`", "`stat`")):
        s.rect(Box(872 + k * 6, 232 + k * 26, 116, 24, "work"))
        s.text(882 + k * 6, 249 + k * 26, lab, size=13, anchor="start")
    s.arrow(840, 290, 866, 290, width=1.4)
    s.step(935, 334, 3, "queue a command", size=17)
    s.text(935, 356, "for the runner to pick up", size=13.5, colour=t.dim)

    # no mount of the cluster file systems
    for k in range(2):
        cylinder(1096, 232 + k * 24, 56, 18, "gate")
    s.cross(1096, 254, size=24)
    s.text(1096, 318, "no mount", size=16, weight="bold", colour=t.accent)
    s.text(1096, 338, "of the cluster", size=13.5, colour=t.dim)
    s.text(1096, 356, "file systems", size=13.5, colour=t.dim)

    # the pod never dials the login node
    s.arrow(1000, 420, 1000, 556, dashed=True, colour=t.accent, width=1.5)
    s.cross(1000, 494, size=13)
    s.text(1024, 496, "never: the pod does not", size=14, anchor="start", colour=t.accent)
    s.text(1024, 516, "connect to the login node", size=14, anchor="start", colour=t.accent)

    # -- the login node: the runner dials out ---------------------------------------------------
    s.frame(470, 564, 560, 336, fill="neutral", colour=t.muted)
    s.text(490, 596, "login node", size=19, anchor="start", weight="bold")
    s.hpc_node(960, 582, 50, 64, busy=2, slots=3)
    r = s.runner(560, 682, 170, 66, label="runner")
    person(510, 690, 10)
    s.text(490, 786, "under the user's own account", size=15, anchor="start", weight="bold")
    s.text(490, 806, "the user's own file permissions", size=13.5, anchor="start", colour=t.dim)
    s.step(640, 848, 4, "read as the user, then reply", size=18)
    s.text(640, 874, "about 60 ms per command", size=13.5, colour=t.dim)

    # outgoing only: both requests leave the login node for the ingress
    s.arrow(612, 676, 600, 344, width=2.0)
    s.arrow(664, 676, 640, 344, width=2.0)
    s.text(592, 506, "`GET /runner/poll`", size=14.5, anchor="end")
    s.text(592, 528, "long-poll, held open", size=13, anchor="end", colour=t.dim)
    s.text(592, 546, "152 s seen without a cut", size=13, anchor="end", colour=t.dim)
    s.text(680, 506, "`POST /runner/reply/<id>`", size=14.5, anchor="start")
    s.text(680, 528, "the answer, a new request", size=13, anchor="start", colour=t.dim)
    s.text(680, 546, "outgoing HTTPS only", size=13, anchor="start", colour=t.dim)

    # -- the shared file system: only the runner reads ---------------------------------------------
    s.shade(1070, 564, 600, 336, fill="gate", opacity=0.55, colour=t.muted)
    s.text(1090, 596, "shared file system", size=19, anchor="start", weight="bold")
    s.text(1090, 618, "scratch, group share", size=13.5, anchor="start", colour=t.dim)
    for k in range(3):
        cylinder(1140, 760 + k * 30, 70, 20, "gate")
    s.arrow(1226, 716, r.right + 6, 716, width=1.9)
    s.text(1300, 650, "only the runner reads", size=14.5, anchor="middle")
    s.text(1300, 670, "one 8 MiB range in about 0.4 s", size=13, colour=t.dim)

    fold = s.folder(1240, 690, 410, 192, fill="surface")
    s.text(fold.x + 18, fold.y + 38, "one root, nothing above it", size=15, anchor="start", weight="bold")
    rule(fold.x + 30, fold.y + 72, True, "regular files only")
    rule(fold.x + 30, fold.y + 100, False, "no `..` in a path")
    rule(fold.x + 30, fold.y + 128, False, "no symlink, `O_NOFOLLOW` per component")
    rule(fold.x + 30, fold.y + 156, True, "ranged reads, at most 8 MiB each")

    # -- spike versus target ---------------------------------------------------------------------
    s.shade(40, 564, 400, 336, fill="problem", opacity=0.85, colour=t.warn, dashed=True)
    s.warning(64, 592, size=11)
    s.text(84, 598, "a spike, not a security model", size=16, anchor="start", weight="bold", colour=t.warn)
    s.text(60, 636, "in the spike", size=15, anchor="start", weight="bold")
    s.text(60, 660, "one shared token for everyone", size=14, anchor="start")
    s.text(60, 682, "TLS not verified, no DNS name yet", size=14, anchor="start")
    s.text(60, 724, "the target design, issue #355", size=15, anchor="start", weight="bold")
    s.text(60, 748, "a token per runner", size=14, anchor="start")
    s.text(60, 770, "OIDC for browsers", size=14, anchor="start")
    s.text(60, 792, "routing to the owner's runner only", size=14, anchor="start")
    s.text(60, 814, "an audit log", size=14, anchor="start")

    s.text(40, H - 46, "Source: docs/research/runner-channel-spike-2026-11-25.md (built, results, finding 4) and "
                       "spikes/runner-channel on branch `spike/runner-channel` (`server.py`, `runner.py`, `k8s.yaml`)",
           size=12.5, anchor="start", colour=t.dim)
    s.text(40, H - 24, "Numbers measured in the spike, 2026-11-25: held connection 152 s, about 60 ms per command, "
                       "8 MiB range in about 0.4 s · tools/diagrams/runner_channel_spike.py",
           size=12.5, anchor="start", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "runner_channel_spike")
