import { Radio, Select } from "@mantine/core";
import { useEffect, useState } from "react";
import { type ClusterFacts, type Compute, createCompute, getClusterFacts, replaceCompute } from "../api";
import type { Software } from "../environments/fields";
import { useServer } from "../server";
import { type ComputeDraft, type Executor, toComputeBody } from "./fields";
import { FormFrame, SoftwareChecks, useFormKit } from "./formKit";

// The one Compute form (ui-spec §4.8.1, #408): the Compute page's new and edit. The backend: its
// executor, SLURM account, local caps, the software it has and the Apptainer arguments.

const NAMES: Record<string, string> = {
  name: "Name",
  label: "Label",
  "slurm.account": "SLURM account",
  "local.cpus": "CPUs at most",
  "local.mem_mib": "Memory at most",
  software: "Software",
  apptainer_args: "Apptainer arguments",
};
const FIELD_OF: Partial<Record<keyof ComputeDraft, string>> = {
  ...{ name: "name", label: "label", account: "slurm.account", cpus: "local.cpus", localMem: "local.mem_mib" },
  ...{ localUnit: "local.mem_mib", software: "software", apptainerArgs: "apptainer_args" },
};

interface Props {
  initial: ComputeDraft;
  etag: string | null;
  onSaved: (item: Compute) => void;
  onCancel: () => void;
  /** Reload after a 412 or a file change. */
  onReload: () => void;
  /** A built-in: its values, read only, and no Save. */
  readOnly?: boolean;
}

export function ComputeForm({ initial, etag, onSaved, onCancel, onReload, readOnly = false }: Props) {
  const server = useServer();
  const onSlurm = server?.executor !== "local";
  const kit = useFormKit({
    ...{ initial, etag, readOnly, names: NAMES, fieldOf: FIELD_OF, onSaved, noun: "compute" },
    // a server without SLURM (known once /version answers) has the Local executor only
    toBody: (d) => toComputeBody(onSlurm ? d : { ...d, executor: "local" }),
    send: (body, tag) => (tag ? replaceCompute(body, tag) : createCompute(body)),
  });
  const { text, unit, shown, set, update } = kit;
  const draft: ComputeDraft = onSlurm ? kit.draft : { ...kit.draft, executor: "local" };

  // The accounts the cluster knows (#401): a failure or no SLURM leaves the plain field.
  const [facts, setFacts] = useState<ClusterFacts | null>(null);
  useEffect(() => {
    if (!onSlurm || readOnly) return;
    const stop = new AbortController();
    getClusterFacts(stop.signal).then(setFacts, () => setFacts(null));
    return () => stop.abort();
  }, [onSlurm, readOnly]);
  const accounts = facts?.scheduler === "slurm" ? facts.accounts : [];

  const setExecutor = (value: string) => {
    const executor = value as Executor;
    // A first look at Local: its caps start at a small, safe value
    update(executor === "local" && onSlurm && !draft.cpus && !draft.localMem ? { executor, cpus: "2", localMem: "8", localUnit: "GiB" } : { executor });
  };
  const node = server?.node ?? "this node";
  return (
    <FormFrame kit={kit} etag={etag} readOnly={readOnly} saveLabel="Save" file="computes.toml" onCancel={onCancel} onReload={onReload}>
      {text("name", "Name", "Lowercase letters, digits and '-', up to 32, starting with a letter. Used in links.", {
        readOnly: readOnly || !!etag,
        "data-autofocus": true, // a dialog opens with focus here (ui-spec §4.8.1)
      })}
      {text("label", "Label (optional)")}
      {onSlurm ? (
        <Radio.Group label="Executor" value={draft.executor} onChange={setExecutor}>
          <Radio value="slurm" label="SLURM" description="The engine sends each task to SLURM with sbatch" mt={6} disabled={readOnly} />
          <Radio value="local" label="Local" description={`Tasks run on ${node}, the login node: keep them small`} mt={6} disabled={readOnly} />
        </Radio.Group>
      ) : (
        <p>
          <strong>Executor:</strong> Local · this machine
          <span className="sp-env-hint sp-muted">This server was set up with spectio init --local: it has no SLURM.</span>
        </p>
      )}
      {draft.executor === "slurm" ? (
        <fieldset>
          <legend>SLURM · optional: leave it empty to use SLURM's default</legend>
          {accounts.length ? (
            <Select
              label="SLURM account"
              description="As in sbatch --account. Leave empty to use SLURM's default"
              inputWrapperOrder={["label", "input", "description", "error"]}
              data={[...new Set([...accounts, ...(draft.account ? [draft.account] : [])])]}
              value={draft.account || null}
              onChange={(v) => set("account")(v ?? "")}
              error={shown["slurm.account"]}
              disabled={readOnly}
              clearable
            />
          ) : (
            text("account", "SLURM account", "As in sbatch --account. Leave empty to use SLURM's default")
          )}
          <p className="sp-env-hint">The partition, memory and time are in an execution profile on this compute (Profiles).</p>
        </fieldset>
      ) : (
        <fieldset>
          <legend>Local · the most the tasks may ask for at once</legend>
          {text("cpus", "CPUs at most", undefined, { inputMode: "numeric", w: 200 })}
          <div className="sp-env-pair">
            {text("localMem", "Memory at most", undefined, { inputMode: "decimal", w: 200 })}
            {unit("localUnit")}
          </div>
        </fieldset>
      )}
      <fieldset>
        <legend>Software available</legend>
        <p className="sp-env-hint">
          The deployment methods this backend has. A profile on it uses these or fewer: a Snakemake launch without a workflow profile
          deploys with them, under the server's data directory. A Nextflow run's profiles decide their own.
        </p>
        <SoftwareChecks value={draft.software} offered={["conda", "apptainer"]} onChange={(v) => update({ software: v as Software[] })} error={shown["software"]} readOnly={readOnly} />
        {text("apptainerArgs", "Apptainer arguments", "One --apptainer-args word, e.g. --bind /g,/scratch")}
      </fieldset>
    </FormFrame>
  );
}
