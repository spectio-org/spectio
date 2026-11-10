# Vendored upstream: BioFlow-Insight

| Field | Value |
|---|---|
| Project | BioFlow-Insight (produces the MetroFlow metro-map JSON) |
| Origin | https://gitlab.liris.cnrs.fr/sharefair/bioflow-insight |
| Commit | `69e0706f008b65777bb467bb2c1e2646c6d14c87` (2026-10-29) |
| PyPI equivalent | `bioflow-insight==2.1.1` |
| Licence | MIT, © 2026 George Marchment, Université Paris-Saclay (`bioflow-insight/LICENSE`) |
| Paper | Marchment et al., NAR Genomics and Bioinformatics 6(3), lqae092, 2024, https://doi.org/10.1093/nargab/lqae092 |

**What is copied.** `src/`, `bioflow_insight_cli/`, `LICENSE`, `README.md` and the packaging files, unchanged.

**What is left out.** `src/language_server_source_code/language-server-all.jar` (≈15 MB), which is the Nextflow language server that BioFlow-Insight bundles. Fetch it from the same upstream commit (or install the PyPI package) to run the copy. Also left out: `tests/`, `wf_test/` and `img/`.

**MetroFlow renderer.** It is not vendored. It lives in the hosted service's repository `gitlab.pasteur.fr/sharefair/bioflow-insight-server`, which needed credentials on 2026-11-10 (a `git clone` asked for a username). See the spike note.

**Updating.** Re-copy these directories from a newer commit, update the table, and review the diff before committing.
