# QC gates and review

!!! note "Later: not in 0.0.1"
    Gates are a planned feature. 0.0.1 has none: runs go from start to end, and the notification list never shows "waits at a gate". The date is not set; see the [roadmap](../roadmap/index.md).

Gates are **optional**. A pipeline without gates runs from start to end as usual. A gate stops a run between two stages so that someone can check the results before the next, often expensive, stage starts. Any pipeline can get one without being changed: Spectio uses the engine's own way to stop and resume.

What is planned:

- **Declared once** for a workflow: after which stage, which checks to show (MultiQC tables, plots, images), and who may decide.
- **A review screen** with the checks that pass and fail, and the evidence next to them.
- **Decisions:** approve, exclude samples, change a parameter and rerun the stage, or stop the run. Every decision is recorded.
- **From a phone:** a link that gives access to one gate only.
- **A review queue** of every gate waiting for you.

The screens for this are drawn, not built, so this page shows no screenshot.
