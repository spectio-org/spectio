# LabID

!!! note "Later: not in 0.0.1"

    The LabID connection comes after the first versions, once LabID's API is confirmed with its team. The date is not set; see the [roadmap](../roadmap/index.md).

[LabID](https://www.researchobject.org/ro-crate/labid) is EMBL Heidelberg's data-management platform for samples, datasets, inventory and a lab notebook. Spectio is planned to work with it in both directions:

- **Launch from LabID.** Pick samples or datasets in a LabID project, choose a registered workflow and launch it. Spectio receives the samplesheet with the LabID identifiers, and finds the data on EMBL storage (`labid://` inputs).
- **Follow the run in LabID.** LabID can show the run's progress, and a QC gate can notify LabID users.
- **Results back in LabID.** When the run ends, Spectio writes a Workflow Run RO-Crate; LabID imports it and registers the outputs as datasets linked to their samples, with the full provenance.
- **The same command-line habits.** Spectio's CLI and its saved server profiles follow the LabID CLI.
