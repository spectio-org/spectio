#!/usr/bin/env python3
"""How nf-spectio attaches to a Nextflow run: inbox #69, decided 2026-10-29.

Writes docs/assets/diagrams/nextflow-attach_{light,dark}.{svg,png}.

Every fact comes from docs/reviews/verification-2026-10-29-nextflow-attach.md (Nextflow v26.10.4 and
v25.10.9, a toy pipeline pinning nf-schema@2.7.2 as nf-core/rnaseq 3.27.0 does):
- -plugins nf-spectio@<ver> replaces the pipeline's list: nf-schema falls to the newest release
  (3.0.0 on 26.10.4, the run fails; 2.7.3 on 25.10.9, silent drift) (FC-311, claim 1);
- a plugins {} block in $NXF_HOME/config is replaced by the pipeline's own: the bridge is dropped (claim 3);
- NXF_PLUGINS_DEFAULT=nf-spectio@<ver> is merged with the pipeline's list; nf-tower is added after
  the merge for -with-tower or TOWER_ACCESS_TOKEN (claims 4 and 10, FC-318);
- a pinned nf-spectio-<ver> directory in $NXF_PLUGINS_DIR starts with no registry contact (claim 11);
- where it is set: the head script, the one-shot terminal prefix, a Seqera Platform Head job variable
  (architecture §13.8).
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 860


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=69)
    t = theme
    s.heading(50, 58, "Adding `nf-spectio` next to an nf-core pipeline's own plugins",
              "the pipeline declares `nf-schema@2.7.2` · Nextflow keeps one plugin list per run")

    lanes = (
        ("nextflow run … -plugins nf-spectio@<ver>", ("`nf-spectio@<ver>`", "`nf-schema` newest"),
         False, "pin lost: fails on 26.10.4, drifts on 25.10.9"),
        ("~/.nextflow/config: plugins { id 'nf-spectio@<ver>' }", ("`nf-schema@2.7.2`",),
         False, "replaced by the pipeline's list: no bridge, no warning"),
        ("NXF_PLUGINS_DEFAULT=nf-spectio@<ver> nextflow run …",
         ("`nf-schema@2.7.2`", "`nf-spectio@<ver>`", "`nf-tower` with `-with-tower`"),
         True, "merged: pins kept, Seqera Platform still added"),
    )
    top, lw = 130, 480
    for i, (cmd, plugins, ok, note) in enumerate(lanes):
        x = 50 + i * (lw + 30)
        s.shade(x, top, lw, 430, fill="neutral" if not ok else "done", opacity=0.45, colour=t.dim, dashed=not ok)
        s.terminal(x + 16, top + 18, lw - 32, 70, (cmd,), size=12)
        s.text(x + 18, top + 130, "resolved plugins", size=14.5, anchor="start", colour=t.dim)
        for k, p in enumerate(plugins):
            s.chip(x + 18, top + 148 + k * 52, lw - 60, p, fill="input" if "spectio" not in p else "work")
        mark_y = top + 330
        if ok:
            s.tick(x + 30, mark_y, size=9)
        else:
            s.cross(x + 30, mark_y)
        s.text(x + 52, mark_y + 5, note, size=13.5, anchor="start", colour=t.good if ok else t.accent)
        s.step(x + lw / 2, top + 390, i + 1, ("replaces" if i == 0 else "is replaced" if i == 1 else "adds"))

    by = 640
    s.text(50, by, "Where `NXF_PLUGINS_DEFAULT` is set, per run", size=16, anchor="start", weight="bold")
    where = (
        "runs Spectio launches: the head script exports it",
        "terminal runs: the one-shot prefix; `export` in the profile is opt-in",
        "Seqera Platform: a Head job variable, or the pre-run script",
    )
    for k, w in enumerate(where):
        s.dot(62, by + 34 + k * 30, 4)
        s.text(76, by + 39 + k * 30, w, size=14, anchor="start")
    s.folder(1010, by - 10, 56, 42, fill="input")
    s.text(1080, by + 12, "`$NXF_HOME/plugins/nf-spectio-<ver>/`", size=14, anchor="start")
    s.text(1080, by + 38, "unpacked by the runner: starts with no registry,", size=13, anchor="start",
           colour=t.dim)
    s.text(1080, by + 58, "online or with `NXF_OFFLINE=true`", size=13, anchor="start", colour=t.dim)
    s.warning(1022, by + 112)
    s.text(1042, by + 117, "the merge is undocumented: checked weekly", size=13.5, anchor="start",
           colour=t.accent)
    s.text(1042, by + 137, "by `nextflow-edge.yml`", size=13.5, anchor="start", colour=t.accent)

    s.text(W - 50, H - 16, "source: docs/reviews/verification-2026-10-29-nextflow-attach.md · architecture §13.8",
           size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "nextflow-attach")
