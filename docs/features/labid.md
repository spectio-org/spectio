# LabID

!!! note "Designed; not scheduled yet"

    The LabID connection comes after the first versions, once LabID's API is confirmed with its team. What ships in which version: [development environment §15](../specs/dev-environment-and-testing.md#15-what-ships-in-which-version).

[LabID](https://www.researchobject.org/ro-crate/labid) is EMBL Heidelberg's data-management platform for samples, datasets, inventory and a lab notebook. Spectio is planned to work with it in both directions:

- **Launch from LabID.** Pick samples or datasets in a LabID project, choose a registered workflow and launch it. Spectio receives the samplesheet with the LabID identifiers, and finds the data on EMBL storage (`labid://` inputs).
- **Follow the run in LabID.** LabID can show the run's progress, and a QC gate can notify LabID users.
- **Results back in LabID.** When the run ends, Spectio writes a Workflow Run RO-Crate; LabID imports it and registers the outputs as datasets linked to their samples, with the full provenance.
- **The same command-line habits.** Spectio's CLI and its saved server profiles follow the LabID CLI.

Design details: [synthesis, LabID](../specs/synthesis.md#labid-embl), [API and data model, LIMS-driven run](../specs/api-and-data-model.md#a-lims-driven-run-labid), [CLI and shared libraries](../specs/cli-and-shared-libraries.md).
