#!/usr/bin/env python3
"""Claiming the package names: 2026-10-29.

Writes docs/assets/diagrams/name-claim_{light,dark}.{svg,png}.

Every fact comes from docs/reviews/verification-2026-10-29-names.md (FC-314 to FC-317) and
.github/workflows/pypi-publish.yml:
- registry.nextflow.io: sign in through Seqera, My plugins, Claim a plugin with a name and a provider;
  the claim waits as PENDING REVIEW until an admin approves it; an approved claim holds the ID with no
  release (nextflow docs/plugins/plugin-registry.mdx:14-40, docs/guides/gradle-plugin.mdx:107-111);
- pypi.org: a pending publisher does not hold the name; the project exists, owned by the account that
  registered the publisher, the first time the workflow exchanges its token, before any upload
  (warehouse creating-a-project-through-oidc.md:28-35, oidc/views.py:208-294); at most 3 pending;
- the workflow: build job without id-token, publish job in environment pypi-<project> with id-token.
"""

from __future__ import annotations

from sketch import Sketch, Theme, main_for

W, H = 1600, 900


def build(theme: Theme) -> Sketch:
    s = Sketch(W, H, theme, seed=66)
    t = theme
    s.heading(50, 58, "Claiming the four names: what holds a name, and when",
              "`nf-spectio` on the Nextflow registry · `spectio`, `spectio-open`, "
              "`snakemake-logger-plugin-spectio` on PyPI")

    # Lane 1: Nextflow plugin registry
    top = 130
    s.shade(40, top, W - 80, 300, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(60, top + 32, "Nextflow plugin registry · by hand, once", size=17, anchor="start", weight="bold")
    s.browser(70, top + 60, 330, 190, url="registry.nextflow.io")
    s.text(90, top + 140, "Log in through Seqera", size=14, anchor="start")
    s.text(90, top + 166, "My plugins, Claim a plugin", size=14, anchor="start")
    s.text(90, top + 192, "name `nf-spectio`", size=14, anchor="start")
    s.text(90, top + 218, "provider = future `provider`", size=14, anchor="start")
    s.arrow(420, top + 155, 540, top + 155, colour=t.dim)
    s.hourglass(600, top + 150, size=14)
    s.text(630, top + 150, "PENDING REVIEW", size=16, anchor="start", weight="bold")
    s.text(630, top + 176, "an admin approves the claim, once", size=13.5, anchor="start", colour=t.dim)
    s.text(630, top + 198, "how long: not documented", size=13.5, anchor="start", colour=t.dim)
    s.arrow(950, top + 155, 1070, top + 155, colour=t.dim)
    s.tick(1100, top + 150, size=10)
    s.text(1125, top + 156, "approved: the ID is held", size=16, anchor="start", colour=t.good, weight="bold")
    s.text(1125, top + 182, "no release needed, no placeholder", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, top + 204, "access token only at the first release", size=13.5, anchor="start", colour=t.dim)
    s.step(W / 2, top + 280, 1, "the claim, not a release, holds `nf-spectio`")

    # Lane 2: PyPI through the workflow
    top = 470
    s.shade(40, top, W - 80, 340, fill="neutral", opacity=0.5, colour=t.dim, dashed=True)
    s.text(60, top + 32, "PyPI · one name at a time, at most 3 pending", size=17, anchor="start", weight="bold")
    s.browser(70, top + 60, 330, 200, url="pypi.org, Publishing")
    s.text(90, top + 140, "pending publisher:", size=14, anchor="start")
    s.text(90, top + 166, "`weber8thomas` / `spectio`", size=14, anchor="start")
    s.text(90, top + 192, "`pypi-publish.yml`", size=14, anchor="start")
    s.text(90, top + 218, "environment `pypi-<project>`", size=14, anchor="start")
    s.warning(110, top + 290, size=12)
    s.text(130, top + 295, "holds nothing yet", size=14, anchor="start", colour=t.accent)
    s.arrow(420, top + 160, 520, top + 160, colour=t.dim)
    s.button(540, top + 100, 200, "Run workflow", fill="work")
    s.text(540, top + 160, "GitHub Actions, on `main`", size=13.5, anchor="start", colour=t.dim)
    s.pipeline(540, top + 190, ("build", "publish"), w=110)
    s.lock(800, top + 256, 11, fill="docs")
    s.text(818, top + 261, "`id-token` in publish only", size=13, anchor="start", colour=t.dim)
    s.arrow(820, top + 160, 1070, top + 160, colour=t.dim)
    s.tick(1100, top + 155, size=10)
    s.text(1125, top + 161, "token exchange: the project exists", size=16, anchor="start", colour=t.good,
           weight="bold")
    s.text(1125, top + 187, "owned by Thomas, then `0.0.0` uploads", size=13.5, anchor="start", colour=t.dim)
    s.text(1125, top + 209, "someone else first: publisher dropped", size=13.5, anchor="start", colour=t.dim)
    s.step(W / 2, top + 320, 2, "only the workflow run holds a PyPI name")

    s.text(W - 50, H - 16, "source: docs/reviews/verification-2026-10-29-names.md · "
           ".github/workflows/pypi-publish.yml", size=12.5, anchor="end", colour=t.dim)
    return s


if __name__ == "__main__":
    main_for(build, "name-claim")
