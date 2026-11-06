#!/usr/bin/env python3
"""Served safely, signed in: batch P3-B01 (P1 Tasks 12 to 16), step P3, milestone M3, 2026-11-06.

Writes docs/assets/diagrams/p3-b01-signed-in_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-B01 at 7d6c80f (the five PRs 132, 134, 135, 136, 137
merged, then the batch code-simplifier):
- spectio_server/auth/secrets.py: three secrets of 32 bytes (`secrets.token_urlsafe(32)`), compared
  in constant time; ServerKey.generate writes `server.key` 0600 under the db dir (node-local) at
  each start; TicketStore: single use (`burn` pops it), TICKET_TTL_S 15 * 60, only the SHA-256 kept;
  SessionStore: in memory, digests only;
- spectio_server/serve.py: start_text prints the first link "(single use, valid 15 minutes)", and
  "New link at any time: spectio login --print-link"; on SLURM the `ssh -N -L` tunnel line;
- spectio/cli/login.py: `_checked` (node, port 1024-65535, absolute db dir), another node: "run
  `ssh <node> spectio login --print-link`"; `port_owners(port) != {uid}` refuses, "the key is not
  sent"; POST `/api/v1/auth/links` to 127.0.0.1 with `Authorization: Bearer <key>` and the loopback
  Origin, through DIRECT = ProxyHandler({}); the fragment must be 43 base64url characters;
- spectio_server/auth/routes.py: link_url `http://127.0.0.1:<port>/auth/link#<ticket>`; the exchange
  burns the ticket, answers 204 and sets cookie_name(Host) httponly, samesite strict, path "/",
  no Domain; auth/static/link.js reads the fragment and drops it with history.replaceState;
- spectio_server/app.py:131-135: installed writes, middleware, browser, host; Starlette runs the
  last first, so Host, cross-site, session, writes;
- auth/host.py: LOOPBACK 127.0.0.1, localhost, [::1]; any port up to 65535 or none; 400
  host-not-allowed; `parse` is the one reading of Host, cookie_name takes its port;
- api/browser.py: Sec-Fetch-Site cross-site or same-site, or an Origin or Referer other than
  http://<Host>, refused 403 cross-site on every method;
- auth/middleware.py: cookie `spectio_session_<port of Host>`, 80 with no port; 401 unauthenticated;
  EXEMPT: GET /auth/link, GET /auth/link.js, POST magic-links:exchange, POST auth/links;
- auth/writes.py: not GET or HEAD: no Origin 403, Transfer-Encoding 411, a non-empty body not
  application/json 415, Content-Length not digits or over MAX_BODY 1048576 413; the foreign-Origin
  branch deleted by the batch code-simplifier (d7463ac, CR-P3T16-01), api.browser refuses it first;
- spectio/fsmodes.py: open_secure_dir mkdir 0700, O_DIRECTORY|O_NOFOLLOW then fstat, refuses another
  user's or a group or other bit, "chmod 700 <path>", never tightens; write_file: a 0600
  `.<name>.<16 hex>` then os.replace, or with exclusive os.link (FileExistsError if the name exists);
  serve.py writes the first server.json with exclusive=True; config.py check_config, UnsafeConfig;
- test counts: `uv run --locked pytest -q packages/spectio-server/tests/security/<file>.py` at
  7d6c80f, 2026-11-06: test_req2_secrets 15, test_req3_cookie 14, test_req4_host 33,
  test_req5_modes 12, test_req7_writes 16 passed; the whole suite 823 passed, 17 deselected
  (the simplifier's gate); simplify -11 +9 (the simplifier's report).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1220
COL = (50, 440, 830, 1220)  # the sign-in, four columns 330 wide
CW = 330
TOP = 120  # the sign-in pictograms
CAP = 372  # their captions
GATE = 630  # the base line of the gates
GX = (190, 500, 810, 1120)  # the gate centres
GCAP = GATE + 46  # their captions
LOW = 970  # the file modes and the tests


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start") -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * 21, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 else s.t.dim)


def cookie(s: Sketch, cx: float, cy: float, r: float = 16) -> None:
    """A round biscuit with chips: the session cookie."""
    s.circle(cx, cy, r, fill="work")
    for dx, dy in ((-0.4, -0.3), (0.35, -0.4), (0.1, 0.15), (-0.3, 0.45), (0.45, 0.35)):
        s.dot(cx + dx * r, cy + dy * r, r * 0.11, colour=s.t.ink)


def refused(s: Sketch, cx: float, y: float, code: str, slug: str) -> None:
    """The answer a gate gives when it refuses."""
    s.arrow(cx, y - 30, cx, y - 6, dashed=True, colour=s.t.dim)
    s.poly([(cx - 70, y), (cx + 70, y), (cx + 70, y + 46), (cx - 70, y + 46)], fill="problem", amount=0.6)
    s.text(cx, y + 20, code, size=17, weight="bold")
    s.text(cx, y + 38, f"`{slug}`", size=12)


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=112)
    t = theme
    s.heading(50, 58, "P3-B01 · signed in on a shared login node, P1 Tasks 12 to 16",
              "milestone M3 served safely · dev-env 15.3 req. 2, 3, 4, 5, 7 and 9 · "
              "PRs 132, 134, 135, 136, 137 into `autopilot/integration`")

    # -- the sign-in, Tasks 12 and 13 ----------------------------------------------------------
    # 1 serve writes a key and prints a link
    x = COL[0]
    s.terminal(x, TOP, 300, 66, ("$ spectio serve",), size=13)
    s.folder(x + 4, TOP + 92, 140, 84, fill="input")
    s.page(x + 52, TOP + 112, 40, 52, fill="surface", lines=2)
    s.lock(x + 98, TOP + 158, size=12)
    s.text(x + 74, TOP + 196, "`server.key` 0600", size=12.5)
    s.text(x + 74, TOP + 214, "node-local db dir", size=12.5, colour=t.dim)
    s.link(x + 214, TOP + 126, size=18)
    s.text(x + 214, TOP + 162, "a first link", size=13, colour=t.dim)
    s.text(x + 214, TOP + 180, "in the start text", size=13, colour=t.dim)
    s.step(x + 150, CAP, 1, "serve makes a key")
    lines(s, x, CAP + 30, ("a new 32-byte key at each start",
                           "it buys a link, never a session",
                           "a restart ends every session"))

    # 2 login asks the server for a link
    x = COL[1]
    s.terminal(x, TOP, 320, 66, ("$ spectio login --print-link",), size=13)
    s.hpc_node(x + 6, TOP + 94, 48, 62, busy=1)
    s.tick(x + 72, TOP + 110, size=7)
    s.text(x + 88, TOP + 115, "this node, else the `ssh node` line", size=13, anchor="start")
    s.tick(x + 72, TOP + 140, size=7)
    s.text(x + 88, TOP + 145, "every listener on the port: your uid", size=13, anchor="start")
    s.tick(x + 72, TOP + 170, size=7)
    s.text(x + 88, TOP + 175, "to 127.0.0.1, never through a proxy", size=13, anchor="start")
    s.text(x + 160, TOP + 210, "`POST /api/v1/auth/links`, Bearer key", size=12.5, colour=t.dim)
    s.step(x + 160, CAP, 2, "login asks for a link")
    lines(s, x, CAP + 30, ("checks `server.json` before using it",
                           "another uid on the port: the key",
                           "is not sent"))

    # 3 the link
    x = COL[2]
    s.link(x + 70, TOP + 40, size=34)
    s.text(x + 120, TOP + 34, "one ticket in the fragment", size=14, anchor="start")
    s.text(x + 120, TOP + 56, "43 characters, checked by login", size=13, anchor="start", colour=t.dim)
    s.text(x + 165, TOP + 104, "`http://127.0.0.1:8080/auth/link#ticket`", size=12.5)
    s.hourglass(x + 34, TOP + 150, size=11)
    s.text(x + 56, TOP + 155, "15 minutes", size=13.5, anchor="start")
    s.text(x + 170, TOP + 145, "1", size=22, weight="bold")
    s.text(x + 190, TOP + 155, "use, then burnt", size=13.5, anchor="start")
    s.text(x + 165, TOP + 196, "only its SHA-256 is kept", size=13, colour=t.dim)
    s.step(x + 165, CAP, 3, "a one-time link")
    lines(s, x, CAP + 30, ("printed by serve or by login",
                           "opened on this machine, or through",
                           "the `ssh -N -L` tunnel on SLURM"))

    # 4 the browser exchanges it for a cookie
    x = COL[3]
    s.browser(x, TOP, CW, 168, url="`127.0.0.1:8080/auth/link`")
    s.text(x + 20, TOP + 56, "the page reads the fragment,", size=13, anchor="start")
    s.text(x + 20, TOP + 76, "drops it from the history", size=13, anchor="start", colour=t.dim)
    s.text(x + 20, TOP + 100, "`POST magic-links:exchange`", size=12.5, anchor="start")
    s.arrow(x + 82, TOP + 128, x + 124, TOP + 128)
    s.text(x + 50, TOP + 133, "204", size=15, weight="bold")
    cookie(s, x + 150, TOP + 128, r=17)
    s.text(x + 176, TOP + 126, "`spectio_session_8080`", size=11.5, anchor="start")
    s.text(x + 176, TOP + 144, "named after the port", size=12, anchor="start", colour=t.dim)
    s.text(x + 165, TOP + 196, "`HttpOnly` `SameSite=Strict` `Path=/`, no Domain", size=12, colour=t.dim)
    s.step(x + 165, CAP, 4, "a cookie per port")
    lines(s, x, CAP + 30, ("two tunnels on two ports keep",
                           "two cookies; a cookie of another",
                           "port gets 401"))

    for a, b in zip(COL[:3], COL[1:]):
        s.arrow(a + CW + 6, TOP + 34, b - 12, TOP + 34)

    # -- every request, Tasks 14, 12 and 16 ----------------------------------------------------
    s.line(30, 506, W - 30, 506, dashed=True, colour=t.muted)
    s.text(50, 496, "then every request passes four checks, in this order: the sign-in requests too",
           size=14, anchor="start", colour=t.dim)

    s.envelope(40, GATE - 60, 62, 42, fill="input")
    s.text(71, GATE + 4, "a request", size=13, colour=t.dim)
    s.arrow(110, GATE - 38, GX[0] - 50, GATE - 38)
    for a, b in zip(GX[:3], GX[1:]):
        s.arrow(a + 52, GATE - 38, b - 50, GATE - 38)
        s.tick((a + b) / 2, GATE - 54, size=6)
    s.tick((GX[3] + 1420) / 2 - 10, GATE - 54, size=6)
    s.arrow(GX[3] + 52, GATE - 38, 1420, GATE - 38)
    for cx in GX:
        s.gate(cx, GATE, w=80, h=64)

    # 5 the Host allow-list
    cx = GX[0]
    s.step(cx, GCAP, 5, "Host allow-list")
    lines(s, cx, GCAP + 26, ("Task 14 · `auth.host`",
                             "`127.0.0.1` `localhost` `[::1]`, any port",
                             "the one reader of Host: the cookie",
                             "takes its port, against DNS rebinding"), size=13, anchor="middle")
    refused(s, cx, GCAP + 160, "400", "host-not-allowed")

    # 6 the cross-site check
    cx = GX[1]
    s.step(cx, GCAP, 6, "cross-site check")
    lines(s, cx, GCAP + 26, ("`api.browser`, every method, a GET too",
                             "`Sec-Fetch-Site` cross-site or same-site",
                             "an Origin or Referer that is not",
                             "`http://` plus this Host, port included"), size=13, anchor="middle")
    refused(s, cx, GCAP + 160, "403", "cross-site")

    # 7 the session
    cx = GX[2]
    s.step(cx, GCAP, 7, "session")
    cookie(s, cx + 52, GATE - 82, r=12)
    lines(s, cx, GCAP + 26, ("Task 12 · `auth.middleware`",
                             "the cookie of this Host port, its digest",
                             "compared in constant time; four exempt:",
                             "the link page, its script, the two auth POSTs"), size=13, anchor="middle")
    refused(s, cx, GCAP + 160, "401", "unauthenticated")

    # 8 the write checks
    cx = GX[3]
    s.step(cx, GCAP, 8, "write checks")
    lines(s, cx, GCAP + 26, ("Task 16 · `auth.writes`",
                             "not GET or HEAD: no Origin 403",
                             "`Transfer-Encoding` 411, a body",
                             "not `application/json` 415",
                             "`Content-Length` over 1 MiB 413"), size=13, anchor="middle")
    refused(s, cx, GCAP + 160, "403 411 415 413", "the first that fails")

    # the route
    s.poly([(1420, GATE - 96), (1550, GATE - 96), (1550, GATE + 4), (1420, GATE + 4)], fill="done", amount=0.8)
    s.cog(1452, GATE - 60, 10, fill="done")
    s.text(1500, GATE - 54, "route", size=16, weight="bold")
    s.text(1485, GATE - 24, "runs, logs, cancel", size=12, colour=t.dim)
    s.text(1485, GATE + 26, "no CORS header", size=12.5, colour=t.dim)
    s.text(1485, GATE + 44, "on any answer", size=12.5, colour=t.dim)

    # the simplifier's cut, pinned where it applies
    sx, sy = 1290, GCAP + 80
    s.shade(sx, sy, 270, 116, fill="neutral", opacity=0.5, colour=t.muted, dashed=True)
    s.text(sx + 14, sy + 24, "batch simplify, -11 +9, tests pass", size=13, anchor="start", weight="bold")
    s.text(sx + 14, sy + 46, "the foreign-Origin branch of 8 is gone:", size=12.5, anchor="start")
    s.text(sx + 14, sy + 66, "6 refuses it first on every method", size=12.5, anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 86, "CR-P3T16-01 · also CR-P3T14-02,", size=12.5, anchor="start", colour=t.dim)
    s.text(sx + 14, sy + 104, "CR-P3T12-03, same behaviour", size=12.5, anchor="start", colour=t.dim)
    s.arrow(sx - 4, sy + 20, GX[3] + 112, GCAP + 54, dashed=True, colour=t.dim)

    # -- the file modes, Task 15 ------------------------------------------------------------------
    s.line(30, LOW - 40, W - 30, LOW - 40, dashed=True, colour=t.muted)
    s.text(50, LOW - 50, "under it all, the private files: Task 15, `spectio.fsmodes`", size=14,
           anchor="start", colour=t.dim)

    x = 50
    s.folder(x, LOW, 190, 104, fill="input")
    s.lock(x + 176, LOW + 100, size=13)
    for i in range(3):
        s.page(x + 32 + i * 46, LOW + 24, 34, 44, fill="surface", lines=2)
    s.text(x + 95, LOW + 90, "data dir 0700", size=12.5)
    s.text(x + 95, LOW + 124, "files 0600", size=12.5)
    s.text(x + 95, LOW + 146, "made at their mode,", size=13)
    s.text(x + 95, LOW + 166, "never chmod-ed after", size=13, colour=t.dim)
    s.text(x + 95, LOW + 186, "so no umask loosens them", size=13, colour=t.dim)

    x = 270
    s.folder(x, LOW, 130, 92, fill="problem")
    s.text(x + 38, LOW + 60, "0755", size=15)
    s.cross(x + 94, LOW + 52, size=18)
    s.text(x + 65, LOW + 124, "a loose directory,", size=13)
    s.text(x + 65, LOW + 144, "a symlink, another's:", size=13, colour=t.dim)
    s.text(x + 65, LOW + 164, "refused, never tightened", size=13, colour=t.dim)
    s.text(x + 65, LOW + 186, "`chmod 700` in the message", size=12.5, colour=t.dim)

    x = 450
    s.page(x, LOW + 6, 52, 66, fill="neutral", lines=3)
    s.text(x + 26, LOW + 92, "`.server.json.hex`", size=11.5)
    s.text(x + 26, LOW + 108, "0600, written whole", size=12, colour=t.dim)
    s.arrow(x + 62, LOW + 38, x + 132, LOW + 38)
    s.text(x + 97, LOW + 28, "`link`", size=12)
    s.page(x + 142, LOW + 6, 52, 66, fill="done", lines=3)
    s.text(x + 168, LOW + 92, "`server.json`", size=12)
    s.text(x + 97, LOW + 146, "the first state file is linked", size=13)
    s.text(x + 97, LOW + 166, "into place: never seen partial,", size=13, colour=t.dim)
    s.text(x + 97, LOW + 186, "fails if one exists, a lock", size=13, colour=t.dim)

    x = 700
    s.page(x, LOW + 6, 56, 70, fill="surface", lines=3)
    s.text(x + 28, LOW + 92, "`spectio.toml`", size=12)
    s.warning(x + 50, LOW + 66, size=12)
    s.text(x + 90, LOW + 30, "others can write it,", size=13, anchor="start")
    s.text(x + 90, LOW + 50, "or its directory:", size=13, anchor="start", colour=t.dim)
    s.text(x + 90, LOW + 72, "`UnsafeConfig`", size=13, anchor="start")
    s.text(x + 28, LOW + 146, "it holds the commands the", size=13, anchor="start")
    s.text(x + 28, LOW + 166, "head script runs, so it is", size=13, anchor="start", colour=t.dim)
    s.text(x + 28, LOW + 186, "checked at every load", size=13, anchor="start", colour=t.dim)

    # -- the tests, to scale ----------------------------------------------------------------------
    bx, by = 1010, LOW - 6
    s.text(bx, by + 8, "tests per requirement, passed at `7d6c80f`", size=14, anchor="start", weight="bold")
    rows = (("req. 2 secrets", "Task 12", 15), ("req. 3 cookie", "Task 13", 14),
            ("req. 4 Host", "Task 14", 33), ("req. 5 modes", "Task 15", 12),
            ("req. 7 writes", "Task 16", 16))
    scale = 9.0  # px per test
    for i, (name, task, n) in enumerate(rows):
        y = by + 26 + i * 30
        s.text(bx, y + 16, name, size=13, anchor="start")
        s.text(bx + 112, y + 16, task, size=12, anchor="start", colour=t.dim)
        x0 = bx + 172
        s._parts.append(
            f'<rect x="{x0:.1f}" y="{y + 2:.1f}" width="{n * scale:.1f}" height="20" rx="3" '
            f'fill="{t.fill("bar_green")}" stroke="{t.ink}" stroke-width="1"/>'
        )
        s.text(x0 + n * scale + 8, y + 17, str(n), size=13.5, anchor="start")
    s.text(bx, by + 190, "whole suite: 823 passed, 17 deselected", size=13, anchor="start", colour=t.dim)
    s.text(bx, by + 210, "5 tasks, 0 blockers, 0 majors; open minors in FU-P3-39 to 43",
           size=13, anchor="start", colour=t.dim)

    s.prefix_key(50, H - 16, ("CR",))
    s.text(W - 50, H - 16, "source: `auth/` host, browser, middleware, writes, secrets, routes · "
           "`cli/login.py` · `fsmodes.py` · `app.py` at 7d6c80f · dev-env 15.3", size=12.5,
           anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-b01-signed-in")
