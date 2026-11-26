import { NativeSelect } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { type ClusterFacts, type Compute, type ExecutionProfile, createExecutionProfile, getClusterFacts, listComputes, replaceExecutionProfile } from "../api";
import { type Software, label } from "../environments/fields";
import { useServer } from "../server";
import { ErrorPanel, SkeletonRows } from "../shell/States";
import { PlacementPicker } from "./PlacementPicker";
import { type ProfileDraft, toProfileBody } from "./fields";
import { FormFrame, SoftwareChecks, useFormKit } from "./formKit";

// The one Execution profile form (ui-spec §4.8.1, #408): the Profiles page's new and edit. A
// compute, its default resources (with the placement picker on a SLURM compute), the software
// it uses and the engines' default profiles. Every field is optional but the compute.

const NAMES: Record<string, string> = {
  name: "Name",
  label: "Label",
  compute: "Compute",
  "resources.partition": "Partition",
  "resources.constraint": "Constraint",
  "resources.gres": "GRES",
  "resources.time_min": "Time per job",
  "resources.mem_mib": "Memory per job",
  "resources.cpus": "CPUs per job",
  software: "Software",
  "engine_profiles.nextflow": "Nextflow profiles (-profile)",
  "engine_profiles.snakemake": "Snakemake profile",
};
const FIELD_OF: Partial<Record<keyof ProfileDraft, string>> = {
  ...{ name: "name", label: "label", compute: "compute", partition: "resources.partition", constraint: "resources.constraint", gres: "resources.gres" },
  ...{ hours: "resources.time_min", minutes: "resources.time_min", mem: "resources.mem_mib", memUnit: "resources.mem_mib", cpus: "resources.cpus" },
  ...{ software: "software", nextflow: "engine_profiles.nextflow", snakemake: "engine_profiles.snakemake" },
};

interface Props {
  initial: ProfileDraft;
  etag: string | null;
  onSaved: (item: ExecutionProfile) => void;
  onCancel: () => void;
  onReload: () => void;
  /** A built-in: its values, read only, and no Save. */
  readOnly?: boolean;
}

/** Reads the computes first: the form's fields depend on the chosen one. */
export function ProfileForm(props: Props) {
  const [computes, setComputes] = useState<Compute[] | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const load = useCallback(() => listComputes().then((l) => (setComputes(l.items), setFailed(null)), (e: Error) => setFailed(e.message)), []);
  useEffect(() => void load(), [load]);
  if (failed) return <ErrorPanel onRetry={load}>Computes could not be read. {failed}</ErrorPanel>;
  if (!computes) return <SkeletonRows rows={3} label="Loading computes…" />;
  return <ProfileFields {...props} computes={computes} />;
}

function ProfileFields({ initial, etag, onSaved, onCancel, onReload, readOnly = false, computes }: Props & { computes: Compute[] }) {
  const server = useServer();
  const usable = computes.filter((c) => c.usable || c.name === initial.compute);
  const start = initial.compute ? initial : { ...initial, compute: (usable.find((c) => c.name === server?.executor) ?? usable[0])?.name ?? "" };
  const byName = (name: string) => computes.find((c) => c.name === name);
  const kit = useFormKit({
    ...{ initial: start, etag, readOnly, names: NAMES, fieldOf: FIELD_OF, onSaved, noun: "profile" },
    toBody: (d) => toProfileBody(d, byName(d.compute)?.executor ?? null),
    send: (body, tag) => (tag ? replaceExecutionProfile(body, tag) : createExecutionProfile(body)),
  });
  const { draft, text, unit, shown, update } = kit;
  const compute = byName(draft.compute);
  const slurm = compute?.executor === "slurm";

  // What the cluster offers (#401): a failure or no SLURM leaves the plain fields, no picker.
  const [facts, setFacts] = useState<ClusterFacts | null>(null);
  useEffect(() => {
    if (!slurm || readOnly) return;
    const stop = new AbortController();
    getClusterFacts(stop.signal).then(setFacts, () => setFacts(null));
    return () => stop.abort();
  }, [slurm, readOnly]);
  const picker = facts?.scheduler === "slurm" && facts.partitions.length > 0 ? facts : null;

  // A profile uses the software its compute has: choosing another compute starts from its own
  const chooseCompute = (name: string) => update({ compute: name, software: byName(name)?.software ?? draft.software });
  const offered = compute?.software ?? ["conda", "apptainer"];
  return (
    <FormFrame kit={kit} etag={etag} readOnly={readOnly} saveLabel="Save" file="execution-profiles.toml" onCancel={onCancel} onReload={onReload}>
      {text("name", "Name", "Lowercase letters, digits and '-', up to 32, starting with a letter. Used in links.", {
        readOnly: readOnly || !!etag,
        "data-autofocus": true,
      })}
      {text("label", "Label (optional)")}
      <NativeSelect
        label="Compute"
        description="The backend the runs of this profile go to."
        inputWrapperOrder={["label", "input", "description", "error"]}
        data={usable.map((c) => ({ value: c.name, label: `${label(c)} · ${c.executor === "slurm" ? "SLURM" : "Local"}` }))}
        value={draft.compute}
        onChange={(e) => chooseCompute(e.currentTarget.value)}
        error={shown.compute}
        disabled={readOnly}
      />
      <p className="sp-env-hint">
        <Link to="/compute">See Compute</Link>
      </p>
      <fieldset>
        <legend>Resources · each is optional: leave it empty to use the engine's or SLURM's default</legend>
        {slurm && picker && (
          <PlacementPicker
            facts={picker}
            partition={draft.partition}
            onPick={(p) => update({ partition: p.partition, ...(p.constraint !== null && { constraint: p.constraint }), ...(p.gres !== null && { gres: p.gres }) })}
          />
        )}
        {slurm && text("partition", "Partition", "Leave empty to use SLURM's default")}
        {slurm && text("constraint", "Constraint", "As in sbatch --constraint, e.g. avx512&zen4. Leave empty for none")}
        {slurm && text("gres", "GRES", "As in sbatch --gres, e.g. gpu:H100:1. Leave empty for none")}
        <div className="sp-env-pair" role="group" aria-label="Time per job">
          {text("hours", "Hours", "Time per job: hours 0 to 720", { inputMode: "numeric", w: 140 })}
          {text("minutes", "Minutes", "minutes 0 to 59", { inputMode: "numeric", w: 140, error: shown["resources.time_min"] ? true : undefined })}
        </div>
        <div className="sp-env-pair">
          {text("mem", "Memory per job", "Whole MiB, or GiB with one decimal", { inputMode: "decimal", w: 200 })}
          {unit("memUnit")}
        </div>
        {text("cpus", "CPUs per job", undefined, { inputMode: "numeric", w: 200 })}
        {slurm && (
          <p className="sp-env-hint">
            With a Snakemake workflow profile: when you choose a Snakemake profile at Launch, the profile's resources and partition are
            used, not these.
          </p>
        )}
      </fieldset>
      <fieldset>
        <legend>Software</legend>
        <p className="sp-env-hint">One or both of the methods the compute has. A Snakemake launch without a workflow profile deploys with these.</p>
        <SoftwareChecks value={draft.software} offered={offered} onChange={(v) => update({ software: v as Software[] })} error={shown["software"]} readOnly={readOnly} />
      </fieldset>
      <fieldset>
        <legend>Default engine profiles (optional)</legend>
        <p className="sp-env-hint">They preselect the engine's own profile at Launch when the pipeline has it; you can change it there.</p>
        {text("nextflow", "Nextflow profiles (-profile)")}
        {text("snakemake", "Snakemake profile")}
      </fieldset>
    </FormFrame>
  );
}
