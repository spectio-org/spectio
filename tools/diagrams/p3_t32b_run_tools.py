#!/usr/bin/env python3
"""Resume, Copy to a new launch, results and reports, in the web UI: step P3, P1 Task 32 part two,
2026-11-04.

Writes docs/assets/diagrams/p3-t32b-run-tools_{light,dark}.{svg,png}.

Every fact comes from branch autopilot/P3-t32b at 551df81 (BASE 85330d6):
- web/src/runs/RunHeader.tsx: RESUMABLE failed and cancelled add Resume, every ended state Copy
  to a new launch, neither for a `cli-observed` run; Copy's "Command" item; the facts
  "Resume of" (the parent, by short ID) and "Resumed as" (each child and its state);
- web/src/runs/ResumeDialog.tsx: the question "Resume this run?" (a Modal on the desktop, a
  bottom Drawer on the phone, Cancel `data-autofocus`, `returnFocus`), Ask's words ("Spectio
  starts a new run in the same launch directory. ... runs again with -resume and reuses the N
  tasks that finished. This run stays ..."), the launch directory only for a run that is not a
  resume, "The head of this run has ended on NODE (checked): Spectio unlocks the directory
  first."; `resumeRun` posts `:relaunch` with `mode: resume` and opens the child; refused,
  Resume stays, `aria-disabled`, `aria-describedby` its reason; refusedWords has words for
  running, head_unverified, resume_in_progress, cli_observed, not_failed_or_cancelled,
  launch_dir_refused, session_id_refused, profiles_unknown, used for `actions.resume` and a 409;
- web/src/launch/LaunchPage.tsx and schemaFields.ts `valuesFrom`: `/launch?from=RUN` reads
  `getLaunchTemplate` and `getRun`, loads the pipeline again, then the run's engine, first
  profile and values in the form's shape; PrefillBanner "Prefilled from NAME (SHORT): N values
  differ from the pipeline's defaults: ...", "Not in this pipeline's form, and not sent: ...",
  each `code_loading` item "LABEL: loads code or configuration" plus " · writable by others",
  "Clear and start empty"; the outdir note "Warning: same as NAME. Change it to keep the two
  runs' results apart."; `setPrefill(null)` is called nowhere (open, CR-P3T32B-02 and
  SEC-P3T32B-01 round 1); the engine hint still "Guessed from main.nf" (CR-P3T32B-04 round 1);
- web/src/runs/ResultsSection.tsx: "Results directory, from --outdir." "Read-only.", Copy, the
  Reports (MultiQC first, a folder of two or more reports as one "Browse FOLDER/" row), the
  Folders, "Browse all results", the note "Reports open in Spectio's sandboxed report viewer,
  where they cannot reach Spectio." and the MultiQC sentences only when a MultiQC report is listed;
- web/src/runs/ResultsBrowser.tsx: `/runs/ID/results?path=`, one folder, the path bar and Copy
  path from the server's answer `results.path` (SEC-P3T32B-02 round 2), a folder opens here, an
  HTML file in the report viewer, any other file downloads, a link outside is "not followed",
  "Showing the first 1,000 entries", "Read-only. A folder's size is not counted.";
  one `error` state for getRun and listResults (open, CR-P3T32B-03 round 1);
- web/src/runs/ReportViewer.tsx: FORMAT_CHARS, the UNSAFE class (C0, DEL, C1 and FORMAT_CHARS),
  `isResultPath` (no empty, `.` or `..` part); ResultsBrowser imports it;
  packages/spectio-server/src/spectio_server/files/redact.py:53 FORMAT_CHARS and confine.py:77
  `_UNSERVED`; packages/spectio-server/tests/test_taskfiles.py
  `test_req13_web_refuses_the_same_format_chars`;
- the bars: code points in the client's format-character class, counted from the regex at each
  commit (`git show REV:web/src/runs/ReportViewer.tsx`): c60d21f none; a580fb4 U+200E-200F,
  U+202A-202E, U+2066-2069 = 2 + 5 + 4 = 11; f1907f8 U+061C, U+200B-200F, U+2028-202E,
  U+2060-206F, U+FEFF, U+FFF9-FFFB = 1 + 5 + 7 + 16 + 1 + 3 = 33, equal to the server's;
  every version also refuses the 32 C0 and the 33 DEL and C1 controls;
- the example run, values and file names are the live shots of commit 8d7d21b and af7ce77
  (docs/assets/shots/app-run-resume, app-launch-copy, app-results-browser, app-report-viewer):
  the demo server as alice on login1, run synthetic-oom MEMPEK, 61 of 62 tasks; the report
  viewer's frame shows MultiQC 1.35 with "Loading report.." (inbox #102);
- the findings are rounds 1 to 5 of docs/reviews/code/P3-t32b.md. Majors: CR-P3T32B-01 round 1
  (fixed af7ce77), CR-P3T32B-02 round 2 (fixed 2999e77), CR-P3T32B-03 round 3 (fixed a580fb4);
  no blocker. Finding IDs restart per round, so each pin names its round. "Open" items were
  checked against the code and shots at 551df81; CR-P3T32B-03 round 2 is fixed by the retake of
  app-results-browser on the 2 MB fixture; CR-P3T32B-06 round 4 is fixed in part (U+00AD still
  passes, SEC-P3T32B-06 round 5);
- tests: the four `test.fixme` Playwright tests made real plus a results browser test
  (tests/e2e/skeleton.spec.ts); pytest, ruff, mypy, tsc and vitest pass (simplifier's report,
  no count kept so that the figure does not go stale).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 1740
TOP = 128  # band 1: the run page, Resume
CAP1 = TOP + 400
DIV1 = CAP1 + 132
TOP2 = DIV1 + 34  # band 2: Copy to a new launch, results, reports
CAP2 = TOP2 + 388
DIV2 = CAP2 + 196
TOP3 = DIV2 + 34  # band 3: one set of refused characters

SERVER_FORMAT = 33  # code points in redact.FORMAT_CHARS
CLIENT_FORMAT = (("c60d21f", "first build", 0), ("a580fb4", "round 3 fix, SEC-P3T32B-02", 11),
                 ("f1907f8", "round 4 fix, SEC-P3T32B-05", 33))


def lines(s: Sketch, x: float, y: float, rows: tuple[str, ...], *, size: float = 13.5,
          anchor: str = "start", step: float = 20) -> None:
    for i, row in enumerate(rows):
        s.text(x, y + i * step, row, size=size, anchor=anchor, colour=s.t.ink if i == 0 else s.t.dim)


def pin(s: Sketch, x: float, y: float, fid: str, rows: tuple[str, ...], *, done: bool = True) -> None:
    """A finding pinned where it hits: a tick when this branch fixed it, a warning while open."""
    if done:
        s.tick(x + 8, y - 5, size=7)
    else:
        s.warning(x + 8, y - 5, size=8)
    s.text(x + 24, y, fid, size=13, anchor="start", weight="bold", colour=s.t.accent)
    for i, row in enumerate(rows):
        s.text(x + 24, y + 18 + i * 17, row, size=12.5, anchor="start", colour=s.t.dim)


def badge(s: Sketch, cx: float, cy: float, n: int) -> None:
    """The step number on the control that starts it."""
    s.circle(cx, cy, 11, fill="docs")
    s.text(cx, cy + 5, str(n), size=14, weight="bold")


def bar(s: Sketch, x: float, y: float, w: float, h: float, fill: str) -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], fill=fill, amount=0.4)


def field(s: Sketch, x: float, y: float, w: float, value: str, *, fill: str = "surface") -> None:
    s.poly([(x, y), (x + w, y), (x + w, y + 26), (x, y + 26)], fill=fill, amount=0.3)
    s.text(x + 8, y + 18, value, size=12, anchor="start")


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=32)
    t = theme
    s.heading(50, 58, "P3 Task 32, part two · Resume, Copy to a new launch, results and reports",
              "`web/src/runs` ResumeDialog, ResultsSection, ResultsBrowser, ReportViewer · "
              "`web/src/launch` LaunchPage · on the API of P1 Tasks 30 and 31 · ui-spec 4.4 note")

    # the run page: where all three start ------------------------------------------------------
    x, y = 50, TOP
    s.browser(x, y, 540, 372, url="`/runs/run_id`, a run launched from Spectio, failed")
    s.text(x + 16, y + 58, "synthetic-oom", size=19, anchor="start", weight="bold")
    s.text(x + 160, y + 58, "`MEMPEK`", size=11.5, anchor="start", colour=t.dim)
    s.cross(x + 22, y + 79, size=5)
    s.text(x + 34, y + 84, "Failed · 1 task failed · 61 / 62 tasks", size=13, anchor="start",
           colour=t.accent)
    s.button(x + 16, y + 98, 96, "Resume", fill="input", h=30)
    s.button(x + 124, y + 98, 184, "Copy to a new launch", fill="neutral", h=30)
    s.button(x + 320, y + 98, 70, "Copy", fill="neutral", h=30)
    badge(s, x + 112, y + 98, 1)
    badge(s, x + 308, y + 98, 2)
    s.text(x + 402, y + 112, "now has a", size=12, anchor="start", colour=t.dim)
    s.text(x + 402, y + 128, "Command item", size=12, anchor="start", colour=t.dim)
    s.text(x + 16, y + 160, "Facts:  Resume of  ·  Resumed as", size=13, anchor="start")
    s.text(x + 16, y + 178, "parent and child link to each other", size=12, anchor="start",
           colour=t.dim)
    # Results and reports
    s.shade(x + 12, y + 192, 516, 168, fill="neutral", opacity=0.7)
    s.folder(x + 22, y + 200, 26, 20, fill="input")
    s.text(x + 58, y + 216, "Results and reports", size=14.5, anchor="start", weight="bold")
    s.text(x + 22, y + 240, "Results directory, from --outdir. Read-only.", size=12.5,
           anchor="start", colour=t.dim)
    s.text(x + 22, y + 260, "`.../runs/run_id/launch/results`", size=12, anchor="start")
    s.button(x + 300, y + 246, 54, "Copy", fill="neutral", h=22)
    s.text(x + 22, y + 286, "MultiQC report  `multiqc/multiqc_report.html`", size=12.5,
           anchor="start")
    s.text(x + 450, y + 286, "Open", size=13, anchor="start", colour=t.accent)
    s.text(x + 22, y + 308, "pipeline_info reports · 3 HTML files", size=12.5, anchor="start")
    s.text(x + 362, y + 308, "Browse pipeline_info/", size=12.5, anchor="start", colour=t.accent)
    s.text(x + 22, y + 334, "Browse all results", size=13, anchor="start", colour=t.accent)
    s.text(x + 156, y + 334, "· reports open in the sandboxed viewer", size=12, anchor="start",
           colour=t.dim)
    badge(s, x + 520, y + 281, 3)
    s.text(x + 270, CAP1, "an ended run, three ways on", size=17)
    lines(s, x + 270, CAP1 + 28, ("Resume only when failed or cancelled; none of the three",
                                  "for a run started from a terminal"), anchor="middle",
          size=13)
    pin(s, x, CAP1 + 80, "R3 CR-P3T32B-03 major", ("the run-results shots kept the old note,",
                                                   "retaken with the new one"))

    # 1 -- Resume asks ----------------------------------------------------------------------------
    s.arrow(x + 548, y + 113, 638, y + 113)
    dx, dy = 646, TOP + 20
    s.frame(dx, dy, 404, 300)
    s.text(dx + 16, dy + 30, "Resume this run?", size=16, anchor="start", weight="bold")
    s.cross(dx + 382, dy + 24, size=6)
    lines(s, dx + 16, dy + 62, ("Spectio starts a new run in the same launch directory.",
                                "Nextflow runs again with `-resume` and reuses the 61",
                                "tasks that finished. This run stays Failed."), size=13)
    s.shade(dx + 16, dy + 124, 372, 30, fill="neutral", opacity=0.9)
    s.text(dx + 26, dy + 144, "`/g/demo-lab/spectio/runs/run_id/launch`", size=12, anchor="start")
    s.text(dx + 16, dy + 180, "The head of this run has ended on login1 (checked):", size=12.5,
           anchor="start", colour=t.dim)
    s.text(dx + 16, dy + 198, "Spectio unlocks the directory first.", size=12.5, anchor="start",
           colour=t.dim)
    s.button(dx + 16, dy + 222, 90, "Cancel", fill="neutral", h=30)
    s.button(dx + 118, dy + 222, 100, "Resume", fill="input", h=30)
    s.text(dx + 16, dy + 276, "Cancel is focused first · focus goes back to Resume",
           size=12, anchor="start", colour=t.dim)
    s.text(dx + 16, dy + 293, "on the phone: a bottom sheet, Resume above Cancel", size=12,
           anchor="start", colour=t.dim)

    # the child run, linked both ways
    s.line(dx + 222, dy + 237, dx + 404 + 66, dy + 237, colour=t.dim, passes=1)
    s.line(dx + 404 + 66, dy + 237, dx + 404 + 66, TOP + 92, colour=t.dim, passes=1)
    s.arrow(dx + 404 + 66, TOP + 92, 1180, TOP + 92)
    s.text(dx + 404 + 72, TOP + 140, "`POST`", size=12, anchor="start")
    s.text(dx + 404 + 72, TOP + 158, "`:relaunch`", size=12, anchor="start")
    s.text(dx + 404 + 72, TOP + 176, "`mode:`", size=12, anchor="start")
    s.text(dx + 404 + 72, TOP + 194, "`resume`", size=12, anchor="start")
    cx = 1186
    s.browser(cx, TOP, 364, 148, url="the child run opens")
    s.text(cx + 16, TOP + 58, "synthetic-oom", size=15, anchor="start", weight="bold")
    s.hourglass(cx + 150, TOP + 52, size=7)
    s.text(cx + 164, TOP + 58, "Running", size=13, anchor="start")
    s.text(cx + 16, TOP + 88, "Resume of  run `MEMPEK`", size=13, anchor="start")
    s.link(cx + 216, TOP + 84, size=13)
    s.text(cx + 16, TOP + 112, "the parent shows Resumed as, this run", size=12, anchor="start",
           colour=t.dim)
    s.text(cx + 16, TOP + 130, "and its state", size=12, anchor="start", colour=t.dim)

    # refused: Resume stays, with its reason as text
    ry = TOP + 178
    s.text(cx, ry, "refused: Resume stays visible", size=14, anchor="start", weight="bold")
    s.poly([(cx, ry + 14), (cx + 96, ry + 14), (cx + 96, ry + 42), (cx, ry + 42)], fill="neutral",
           amount=0.4)
    s.text(cx + 48, ry + 33, "Resume", size=13, colour=t.dim)
    s.text(cx + 108, ry + 26, "`aria-disabled`, described by", size=12, anchor="start",
           colour=t.dim)
    s.text(cx + 108, ry + 42, "its reason, in words", size=12, anchor="start", colour=t.dim)
    s.text(cx, ry + 70, "`running`  The run's head is still running.", size=12, anchor="start")
    s.text(cx, ry + 88, "Resume when it has ended.", size=12, anchor="start")
    s.text(cx, ry + 112, "and `head_unverified`, `resume_in_progress`,", size=12, anchor="start",
           colour=t.dim)
    s.text(cx, ry + 130, "`cli_observed`, `not_failed_or_cancelled`,", size=12, anchor="start",
           colour=t.dim)
    s.text(cx, ry + 148, "`launch_dir_refused`, `session_id_refused`,", size=12, anchor="start",
           colour=t.dim)
    s.text(cx, ry + 166, "`profiles_unknown`: 8 reasons, also for a 409", size=12, anchor="start",
           colour=t.dim)

    s.step(dx + 260, CAP1, 1, "Resume asks, then opens the child run")
    lines(s, dx + 260, CAP1 + 28, ("same launch directory, the engine reuses what finished",),
          anchor="middle", size=13)
    pin(s, dx, CAP1 + 80, "R1 CR-P3T32B-06 simplify", ("the unreachable not-ended words",
                                                       "of `running` removed"))

    s.line(30, DIV1, W - 30, DIV1, dashed=True, colour=t.muted)

    # 2 -- Copy to a new launch ------------------------------------------------------------------
    x, y = 50, TOP2
    s.browser(x, y, 730, 360, url="`/launch?from=run_id`  reads `GET :launch-template` and the run")
    badge(s, x + 716, y + 46, 2)
    s.shade(x + 14, y + 40, 690, 134, fill="neutral", opacity=0.8)
    s.text(x + 26, y + 62, "Prefilled from synthetic-oom (MEMPEK): 2 values differ from the",
           size=13, anchor="start")
    s.text(x + 26, y + 80, "pipeline's defaults: fail_mode, fail_process.", size=13, anchor="start")
    s.dot(x + 32, y + 101, 2.5)
    s.text(x + 42, y + 106, "Pipeline: loads code or configuration "
           "`/g/demo-lab/pipelines/synthetic/nextflow`", size=12.5, anchor="start")
    s.dot(x + 32, y + 123, 2.5)
    s.text(x + 42, y + 128, "a location another user can write ends with  · writable by others",
           size=12.5, anchor="start", colour=t.dim)
    s.text(x + 26, y + 150, "a key the form does not take: Not in this pipeline's form, and not sent",
           size=12, anchor="start", colour=t.dim)
    s.button(x + 530, y + 136, 162, "Clear and start empty", fill="neutral", h=26)

    s.text(x + 16, y + 200, "Pipeline", size=13, anchor="start")
    field(s, x + 16, y + 208, 420, "`/g/demo-lab/pipelines/synthetic/nextflow`")
    s.tick(x + 456, y + 220, size=6)
    s.text(x + 470, y + 225, "loaded again, its schema shapes the values", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 16, y + 256, "Engine", size=13, anchor="start")
    s.poly([(x + 16, y + 264), (x + 112, y + 264), (x + 112, y + 290), (x + 16, y + 290)],
           fill="input", amount=0.3)
    s.text(x + 64, y + 282, "Nextflow", size=12.5)
    s.text(x + 124, y + 282, "Guessed from main.nf · change it if the guess is wrong", size=12,
           anchor="start", colour=t.dim)
    s.text(x + 470, y + 256, "Profile", size=13, anchor="start")
    field(s, x + 470, y + 264, 230, "test")
    s.text(x + 16, y + 314, "outdir", size=13, anchor="start")
    field(s, x + 70, y + 298, 200, "the copied run's value", fill="work")
    s.text(x + 282, y + 316, "Warning: same as synthetic-oom. Change it to keep the two runs'",
           size=12, anchor="start", colour=t.warn)
    s.text(x + 282, y + 334, "results apart.", size=12, anchor="start", colour=t.warn)
    s.step(x + 365, CAP2, 2, "Copy to a new launch prefills the form")
    lines(s, x + 365, CAP2 + 28, ("the run's engine, first profile and values; nothing is sent "
                                  "until Launch",), anchor="middle", size=13)
    pin(s, x, CAP2 + 76, "R1 CR-P3T32B-02, SEC-P3T32B-01", ("the banner stays after another",
                                                            "pipeline is picked or typed"),
        done=False)
    pin(s, x + 380, CAP2 + 76, "R1 SEC-P3T32B-02, R2 SEC-P3T32B-03", ("writable by others is a plain",
                                                               "suffix, weaker than outdir's"),
        done=False)
    pin(s, x, CAP2 + 136, "R1 CR-P3T32B-04", ("a copied engine still reads",
                                                   "Guessed from main.nf"), done=False)

    # 3 -- the results browser -------------------------------------------------------------------
    bx, by = 820, TOP2
    s.browser(bx, by, 346, 300, url="`/runs/run_id/results?path=multiqc`")
    badge(s, bx + 332, by + 46, 3)
    s.text(bx + 16, by + 60, "Results", size=17, anchor="start", weight="bold")
    s.shade(bx + 12, by + 72, 322, 30, fill="input", opacity=0.5)
    s.text(bx + 22, by + 92, "results / multiqc", size=13, anchor="start", colour=t.accent)
    s.text(bx + 168, by + 92, "from the server's answer", size=11.5, anchor="start",
           colour=t.dim)
    rows = (("page", "`general_stats.tsv`", "file · downloads"),
            ("page", "`multiqc_data.json`", "file · downloads"),
            ("html", "`multiqc_report.html`", "report viewer"),
            ("link", "a link outside", "not followed"))
    for i, (kind, name, what) in enumerate(rows):
        ry = by + 116 + i * 34
        if kind == "link":
            s.link(bx + 28, ry + 12, size=12)
        else:
            s.page(bx + 18, ry, 20, 26, fill="docs" if kind == "html" else "surface", lines=0)
        s.text(bx + 48, ry + 18, name, size=12, anchor="start")
        s.text(bx + 330, ry + 18, what, size=11.5, anchor="end", colour=t.dim)
    s.text(bx + 16, by + 268, "Read-only. A folder's size is not counted.", size=12,
           anchor="start", colour=t.dim)
    s.text(bx + 16, by + 286, "a folder opens here, at most 1,000 entries", size=12,
           anchor="start", colour=t.dim)
    s.step(bx + 173, by + 330, 3, "one folder at a time")
    pin(s, bx, by + 362, "R2 CR-P3T32B-03", ("its shot showed the 1.0 KB stand-in;",
                                            "retaken on the 2 MB fixture"))
    pin(s, bx, by + 418, "R1 CR-P3T32B-03", ("one error state for the run",
                                            "and the listing"), done=False)

    # 4 -- the report viewer ---------------------------------------------------------------------
    s.arrow(bx + 300, by + 186, 1200, by + 186)
    vx, vy = 1204, TOP2
    s.browser(vx, vy, 346, 330, url="`/runs/run_id/report?path=...`")
    s.text(vx + 16, vy + 58, "MultiQC report", size=16, anchor="start", weight="bold")
    s.button(vx + 236, vy + 40, 96, "Download", fill="neutral", h=26)
    s.shade(vx + 12, vy + 72, 322, 46, fill="work", opacity=0.6)
    s.text(vx + 20, vy + 90, "Untrusted report: `multiqc/multiqc_report.html`", size=11.5,
           anchor="start")
    s.text(vx + 20, vy + 108, "Spectio never asks you to paste a link.", size=11.5,
           anchor="start", colour=t.dim)
    s.shade(vx + 12, vy + 128, 322, 190, fill="surface", opacity=0.0, colour=t.muted, dashed=True)
    s.lock(vx + 318, vy + 144, size=11)
    s.text(vx + 22, vy + 148, "`sandbox allow-scripts allow-downloads`", size=11, anchor="start",
           colour=t.dim)
    s.text(vx + 22, vy + 176, "multiqc v1.35", size=16, anchor="start", weight="bold")
    s.hourglass(vx + 30, vy + 196, size=6)
    s.text(vx + 42, vy + 201, "Loading report..  stays", size=12.5, anchor="start",
           colour=t.accent)
    for i, (smp, a, r) in enumerate((("S01", 91.2, 42.1), ("S02", 89.7, 38.9))):
        yy = vy + 216 + i * 24
        s.text(vx + 22, yy + 15, smp, size=12, anchor="start")
        bar(s, vx + 60, yy + 3, 120 * a / 100, 16, "input")
        s.text(vx + 64, yy + 15, f"{a}", size=11.5, anchor="start")
        bar(s, vx + 190, yy + 3, 120 * r / 100, 16, "input")
        s.text(vx + 194, yy + 15, f"{r}", size=11.5, anchor="start")
    s.cross(vx + 30, vy + 286, size=6)
    s.text(vx + 44, vy + 290, "scripts throw on `localStorage`:", size=12, anchor="start")
    s.text(vx + 44, vy + 307, "tables show, plots and toolbox do not", size=12, anchor="start",
           colour=t.dim)
    s.step(vx + 173, vy + 360, 4, "a report, sandboxed, as it is")
    pin(s, vx, vy + 392, "R1 CR-P3T32B-01 major", ("shots on the stand-in table, now",
                                                   "on the regenerated MultiQC fixture"))
    pin(s, vx, vy + 448, "R2 CR-P3T32B-02 major", ("the stuck banner looked like a working",
                                                   "viewer; UI and captions now say so"))
    pin(s, vx, vy + 504, "R3 SEC-P3T32B-01", ("the shot text check cannot see",
                                             "inside the frame"), done=False)

    s.line(30, DIV2, W - 30, DIV2, dashed=True, colour=t.muted)

    # 5 -- one set of refused characters ---------------------------------------------------------
    x, y = 50, TOP3
    s.text(x, y + 6, "a `path=` from the URL is checked before it is asked for or shown:",
           size=14, anchor="start")
    s.text(x, y + 26, "`isResultPath`, in the report viewer and the results browser", size=13,
           anchor="start", colour=t.dim)
    samples = (("`multiqc/multiqc_report.html`", True, "asked for"),
               ("`../launch/.nextflow.log`", False, "an empty, `.` or `..` part"),
               ("a name with U+202E or U+200B", False, "a bidi or format character"),
               ("a name with a control character", False, "C0, DEL or C1"))
    for i, (name, ok, why) in enumerate(samples):
        yy = y + 62 + i * 34
        s.page(x, yy - 16, 18, 22, fill="surface" if ok else "problem", lines=0)
        s.text(x + 28, yy, name, size=12.5, anchor="start")
        s.arrow(x + 300, yy - 5, x + 336, yy - 5, colour=t.dim)
    gx = x + 384
    s.poly([(gx - 40, y + 44), (gx + 40, y + 44), (gx + 12, y + 128), (gx - 12, y + 128)],
           fill="gate", amount=0.8)
    for ddx, ddy in ((-18, 62), (0, 62), (18, 62), (-8, 86), (8, 86)):
        s.dot(gx + ddx, y + ddy, 2.4, colour=t.dim)
    for i, (name, ok, why) in enumerate(samples):
        yy = y + 62 + i * 34
        if ok:
            s.tick(gx + 74, yy - 5, size=7)
        else:
            s.cross(gx + 74, yy - 5, size=6)
        s.text(gx + 90, yy, why, size=12.5, anchor="start", colour=t.ink if ok else t.dim)
    s.text(x, y + 214, "refused: nothing is fetched, and the page says", size=13, anchor="start",
           colour=t.dim)
    s.text(x, y + 234, "Not a folder of this run's results.", size=13, anchor="start")
    s.step(x + 330, y + 282, 5, "the client refuses what the server refuses")
    pin(s, x, y + 322, "R5 SEC-P3T32B-06", ("U+00AD, U+180E and the tag block",
                                           "pass on both sides; predates this step"), done=False)
    pin(s, x + 380, y + 322, "R2 SEC-P3T32B-01, R3 SEC-P3T32B-02", ("the path bar now comes",
                                                             "from the server's answer"))

    # the bars, to scale
    rx, full = 860, 470
    s.text(rx, y + 6, "format characters the client refuses in a path, of the server's 33",
           size=14, anchor="start")
    s.text(rx, y + 26, "to scale, counted from the regex at each commit", size=12.5,
           anchor="start", colour=t.dim)
    unit = full / SERVER_FORMAT
    for i, (rev, what, n) in enumerate(CLIENT_FORMAT):
        yy = y + 44 + i * 40
        s.text(rx + 150, yy + 15, f"`{rev}`", size=12.5, anchor="end")
        s.text(rx + 150, yy + 31, what, size=11, anchor="end", colour=t.dim)
        s.line(rx + 160, yy + 10, rx + 160 + full, yy + 10, dashed=True, colour=t.muted,
               passes=1)
        if n:
            bar(s, rx + 160, yy, n * unit, 20, "done" if n == SERVER_FORMAT else "work")
        s.text(rx + 168 + n * unit, yy + 15, str(n), size=13, anchor="start", weight="bold")
    yy = y + 44 + 3 * 40
    s.text(rx + 150, yy + 15, "server", size=12.5, anchor="end")
    s.text(rx + 150, yy + 31, "`redact.FORMAT_CHARS`", size=11, anchor="end", colour=t.dim)
    bar(s, rx + 160, yy, full, 20, "input")
    s.text(rx + 168 + full, yy + 15, "33", size=13, anchor="start", weight="bold")
    s.text(rx, yy + 58, "every version also refuses the 65 C0, DEL and C1 controls", size=12.5,
           anchor="start", colour=t.dim)
    pin(s, rx, yy + 92, "R4 SEC-P3T32B-05, CR-P3T32B-06", ("the client took the whole set;",
                                                           "one constant, `FORMAT_CHARS`;",
                                                           "CR-P3T32B-06 fixed in part:",
                                                           "U+00AD still passes (R5)"))
    s.terminal(rx + 300, yy + 74, 390, 92, ("test_req13_web_refuses_the_same_format_chars",
                                            "reads it from ReportViewer.tsx,",
                                            "asserts it equals the server's"), size=11.5,
               line_h=17)

    s.prefix_key(50, H - 40, ("CR", "SEC"))
    s.text(50, H - 18, "R1 to R5: the code review rounds, IDs restart in each round · tick: fixed "
           "here, warning: still open, all minor · the run and files are the demo shots'",
           size=12.5, anchor="start", colour=t.dim)
    s.text(W - 50, H - 40, "source: web/src/runs, web/src/launch, spectio_server/files/redact.py "
           "· P1 Task 32", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "p3-t32b-run-tools")
