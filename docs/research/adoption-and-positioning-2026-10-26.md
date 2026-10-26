# Adoption and positioning: getting users without a fight with Seqera (2026-10-26)

**Question (Thomas).** How do we get users, in which communities and on which shared platforms? A head-on confrontation with Seqera Platform is a real risk, and nf-core support will be hard to get. We can still test the idea, but only with a system that is robust, works from the start, and is clearly explained.

**Short answer.**
- Do not launch as "an open-source Seqera Platform". Launch as what nobody offers today:
  - QC gates and run steering for HPC core facilities;
  - Snakemake first, Nextflow too;
  - self-hosted, and part of the depictio and LabID platform.
- Start with design partners at EMBL. Go public only at the beta, with a demo instance, and stay at 0.x until the 1.0 gate (`dev-environment-and-testing.md` §14).

## 1. The landscape that matters for positioning (checked 2026-10-26)

| Fact | Source | Consequence |
|---|---|---|
| Seqera's open-source community edition of Tower (`nf-tower`, MPL-2.0) was archived on 2025-01-30; its README points to Seqera Cloud | [seqeralabs/nf-tower](https://github.com/seqeralabs/nf-tower) | There is no maintained open-source, self-hosted monitor from Seqera. Spectio fills a gap Seqera left, rather than cloning a live product. |
| Seqera Platform today is Seqera Cloud (free sign-up) and Enterprise (on-premises, by demo request). No free self-hosted edition is documented | [docs.seqera.io/platform](https://docs.seqera.io/platform) | Institutions that must self-host and cannot buy Enterprise are the natural audience. |
| nf-core's steering committee includes Evan Floden and Phil Ewels, among others; several maintainers are Seqera-affiliated; the site footer reads "Supported by: Seqera"; core-team duties include the "nf-core Seqera Platform workspace" | [nf-co.re/governance](https://nf-co.re/governance/) | Official nf-core endorsement of a Seqera alternative is unlikely. Plan without it. |
| The only open-source Tower-compatible server found is nf-shard (MIT, 79 stars) | [AugustDev/nf-shard](https://github.com/AugustDev/nf-shard) | Small; monitoring only, no steering. Not a competitor to fear, perhaps a project to cite or collaborate with. |
| Snakemake's own docs list a single monitoring option: panoptes, "under development", through `--wms-monitor` | [Snakemake monitoring docs](https://snakemake.readthedocs.io/en/master/executing/monitoring.html) | Snakemake users have no run manager, gates or steering. This audience has no incumbent, and there is no conflict with Seqera there. |

## 2. Positioning

**Say what Spectio is:**
- **A gate-and-steer layer for pipelines on your own cluster.** It stops a run at the stage you choose, shows the QC evidence to whoever must decide (a person, an AI agent, a robot), and resumes from the cache.
- **Snakemake and Nextflow alike.** The same review, whatever the engine.
- **For core facilities and institutes.** Self-hosted, with no cloud, and runners on SLURM or Kubernetes. LIMS hand-off (LabID) and dashboards (depictio) come with it.

**Do not say:**
- "Tower alternative" or "open-source Seqera";
- comparisons with Seqera's pricing.

Where a comparison is needed, use a neutral, factual table in the docs ("Spectio and other tools"), including Seqera, nf-shard, panoptes, Galaxy and Arvados.

**Stay compatible, not adversarial:**
- **The Tower protocol.** The synthesis plans to accept Nextflow's built-in Tower protocol (`synthesis.md` §2), as nf-shard does. Keep it as a convenience for monitoring only, and say plainly that it is unofficial and best effort. The primary Nextflow path should be Spectio's own plugin (`nf-spectio`), which uses only public Nextflow extension points. Question for Thomas: inbox #6.
- **Testing with nf-core.** Using nf-core pipelines unmodified, with their own test profiles, is the strongest demonstration, and it needs no permission (`tests/pipelines/real/`). Report upstream bugs found by the corpus as ordinary nf-core issues: that is the respectful kind of visibility.

## 3. Who first, and where

**Stage 1: design partners (private alpha, 0.2 – 0.4).**
- **Who:** 3 to 5 EMBL groups that run pipelines with a real QC step, and that have someone who will tell us what breaks.
- **Candidates [to be validated by Thomas]:**
  - the Genomics Core Facility;
  - imaging groups (the cellpose plate scenario);
  - the groups already using depictio;
  - EMBL Bio-IT.
- **Commitment:** a 30-minute install from the docs, a weekly feedback slot, and a named contact.
- **Measured:** time to the first gate decision, bugs per week, and the 1.0-gate users count.

**Stage 2: neighbouring institutes (late alpha, early beta).**
- **Networks:**
  - de.NBI and ELIXIR nodes [to be validated: which nodes run HPC workflow services];
  - core-facility networks (CTLS in Europe, ABRF) [to be validated].
- **Why these first:** they share the same constraint, self-hosting next to the data, and the same users, core-facility staff and the PIs who decide.

**Stage 3: public beta (0.5 – 0.9).**

| Channel | What to bring |
|---|---|
| Snakemake community: GitHub Discussions and the issue tracker; the Snakemake Workflow Catalog authors; Snakemake hackathons [to be validated: current official chat] | the Snakemake logger plugin, the catalog workflows running green in Spectio, a cast of a gate on a catalog workflow |
| Nextflow and nf-core community spaces (Slack, community forum) [to be validated: what is open to non-Seqera tools] | "works with nf-core pipelines unmodified", technical posts, no marketing |
| BioHackathon Europe (ELIXIR): 2026 edition 9–13 November in Barcelona; the 2026 call for projects ran 16 March to 15 April ([biohackathon-europe.org](https://biohackathon-europe.org/)) | a 2027 project: "QC gates for workflow engines", co-proposed with a partner site |
| BOSC at ISMB ([open-bio.org BOSC 2026](https://www.open-bio.org/events/bosc-2026)) | a talk or poster once the beta has outside users |
| Registries: bio.tools, Research Software Directory, WorkflowHub (as an integration) [to be validated] | listings at the beta |
| Social: Bluesky and Mastodon bioinformatics circles, r/bioinformatics, Biostars | short demo videos (the combined captures), release notes |
| Publication: JOSS ([submission rules](https://joss.readthedocs.io/en/latest/submitting.html)) | after 1.0 or late beta (see §4) |

## 4. Two constraints to plan for now

1. **JOSS requires public history.** The repository must have been public for more than six months, with steady development over that period. "A recent repo dump" and concentrated bursts of commits are not accepted, and there must be evidence of research use by others.
   - Going public at the start of the private alpha starts that clock early. The alpha users can still be private partners.
   - The autopilot's bursts of commits are fine as long as development continues over months.
   - JOSS also requires an AI usage disclosure (tools, scope, and human validation of outputs and core design decisions). The decision log and the Progress pages already record that, so keep doing it.
2. **A licence before going public.** An OSI-approved licence is required by JOSS and expected by institutions. depictio is MIT, and MIT keeps the ecosystem simple (`README.md`: "to be decided before the first code release").

## 5. What "robust, works from the start, clearly explained" means in practice

These conditions are already the entry conditions of the alpha and beta stages (`dev-environment-and-testing.md` §14).
- **Robust.**
  - The synthetic suite on both engines on every PR.
  - The real corpus nightly.
  - Upgrades, backups and restores tested.
  - Known engine faults handled and explained, not hidden (see the Snakemake 9.27.1 finding in `spike-synthetic-pipelines-2026-10-26.md`).
- **Works from the start.**
  - Install in under 30 minutes from the docs alone, tested by someone who did not write them.
  - A demo instance with seeded runs and gates. Visitors open it with a share link, no account needed.
- **Clearly explained.**
  - The documentation system (`documentation-system.md`): a landing page, a guide for every flow with a cast or video, and a changelog that says what users can now do.
  - A short comparison page, factual and fair.

## 6. Risks

| Risk | Mitigation |
|---|---|
| Seqera sees Spectio as a hostile clone | positioning (§2); no Tower branding; the Tower protocol is optional and unofficial; contribute engine bugs upstream; be ready to drop the Tower protocol if asked |
| No nf-core visibility | lead with Snakemake and institutional users; let nf-core pipelines appear as test cases and in partners' runs |
| A side project cannot support many sites | 0.x stays private-alpha-sized; one support channel with a stated response time; the 1.0 gate requires a support plan |
| A fragile first impression | public beta only after the alpha conditions; demo instance reset nightly; a "known issues" page |
