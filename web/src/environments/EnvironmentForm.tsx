import { Button, NativeSelect, Radio, TextInput } from "@mantine/core";
import { useState } from "react";
import { ApiError, type EnvironmentItem, createEnvironment, replaceEnvironment } from "../api";
import { useServer } from "../server";
import { type Draft, type Errors, type Unit, toBody } from "./fields";

// The one environment form (ui-spec §4.8.1): the pages' new and edit, and Launch's New environment
// dialog (FU-P3-86g). Every field is a labelled native input; a field's rule shows under it as
// soon as it is typed in, a server `422` lands on its field, and Save stays focusable with why.

const NAMES: Record<string, string> = {
  name: "Name",
  label: "Label",
  "slurm.partition": "Partition",
  "slurm.account": "SLURM account",
  "slurm.time_min": "Time per job",
  "slurm.mem_mib": "Memory per job",
  "local.cpus": "CPUs at most",
  "local.mem_mib": "Memory at most",
  "profiles.nextflow": "Default Nextflow profile",
  "profiles.snakemake": "Default Snakemake profile",
};
const FIELD_OF: Partial<Record<keyof Draft, string>> = {
  ...{ name: "name", label: "label", partition: "slurm.partition", account: "slurm.account", hours: "slurm.time_min" },
  ...{ minutes: "slurm.time_min", mem: "slurm.mem_mib", memUnit: "slurm.mem_mib", cpus: "local.cpus" },
  ...{ localMem: "local.mem_mib", localUnit: "local.mem_mib", nextflow: "profiles.nextflow", snakemake: "profiles.snakemake" },
};
const BANNERS: Record<string, string> = {
  "412": "This environment changed in another tab.",
  "environments-file-changed": "The file changed on disk since this page read it.",
};

interface Props {
  initial: Draft;
  /** The item's ETag when editing; null for a new environment. */
  etag: string | null;
  onSaved: (item: EnvironmentItem) => void;
  onCancel: () => void;
  /** Reload after a 412 or a file change: the page reads the item again, the dialog the list. */
  onReload: () => void;
  /** A built-in: its values, read only, and no Save. */
  readOnly?: boolean;
}

export function EnvironmentForm({ initial, etag, onSaved, onCancel, onReload, readOnly = false }: Props) {
  const server = useServer();
  const onSlurm = server?.executor !== "local";
  const [typed, setDraft] = useState<Draft>(initial);
  const draft: Draft = onSlurm ? typed : { ...typed, executor: "local" };
  const [touched, setTouched] = useState<Set<string>>(new Set(etag ? Object.keys(NAMES) : []));
  const [server422, setServer422] = useState<Errors>({});
  const [banner, setBanner] = useState<{ text: string; reload: boolean } | null>(null);
  const [sending, setSending] = useState(false);
  const { body, errors } = toBody(draft);
  const shown = { ...Object.fromEntries(Object.entries(errors).filter(([k]) => touched.has(k))), ...server422 };
  const first = Object.keys(errors)[0];
  const why = first ? `Fix ${NAMES[first] ?? first} first` : null;

  const set = (key: keyof Draft) => (value: string) => {
    const next = { ...draft, [key]: value };
    if (key === "executor" && value === "local" && onSlurm && !draft.cpus && !draft.localMem) {
      Object.assign(next, { cpus: "2", localMem: "8", localUnit: "GiB" });
    }
    setDraft(next);
    const field = FIELD_OF[key];
    if (field) setTouched(new Set(touched).add(field));
    setServer422(({ [field ?? ""]: _, ...rest }) => rest);
  };
  const save = () => {
    if (!body) return setTouched(new Set(Object.keys(NAMES)));
    setSending(true);
    setBanner(null);
    (etag ? replaceEnvironment(body, etag) : createEnvironment(body))
      .then(onSaved)
      .catch((e: Error) => {
        if (e instanceof ApiError && e.status === 409 && e.slug === "environment-exists") return setServer422({ name: e.message });
        if (e instanceof ApiError && e.errors.length) return setServer422(Object.fromEntries(e.errors.map((f) => [f.field, f.message])));
        const known = e instanceof ApiError ? (BANNERS[String(e.status)] ?? BANNERS[e.slug ?? ""]) : undefined;
        setBanner({ text: known ?? e.message, reload: !!known });
      })
      .finally(() => setSending(false));
  };
  const text = (key: keyof Draft, label: string, hint?: string, more: object = {}) => (
    <TextInput
      label={label}
      description={hint}
      inputWrapperOrder={["label", "input", "description", "error"]}
      value={draft[key]}
      onChange={(e) => set(key)(e.currentTarget.value)}
      error={shown[FIELD_OF[key] ?? ""]}
      readOnly={readOnly}
      {...more}
    />
  );
  const unit = (key: "memUnit" | "localUnit") => (
    <NativeSelect aria-label="Unit" data={["MiB", "GiB"]} value={draft[key]} onChange={(e) => set(key)(e.currentTarget.value as Unit)} disabled={readOnly} />
  );
  const node = server?.node ?? "this node";
  return (
    <form className="sp-env-form" onSubmit={(e) => (e.preventDefault(), save())} noValidate>
      {text("name", "Name", "Lowercase letters, digits and '-', up to 32, starting with a letter. Used in links.", {
        readOnly: readOnly || !!etag,
      })}
      {text("label", "Label (optional)")}
      {onSlurm ? (
        <Radio.Group label="Executor" value={draft.executor} onChange={set("executor")}>
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
          <legend>SLURM · each field is optional: leave it empty to use SLURM's default</legend>
          {text("partition", "Partition", "Leave empty to use SLURM's default")}
          {text("account", "SLURM account", "As in sbatch --account. Leave empty to use SLURM's default")}
          <div className="sp-env-pair" role="group" aria-label="Time per job">
            {text("hours", "Hours", "Time per job: hours 0 to 720", { inputMode: "numeric", w: 140 })}
            {text("minutes", "Minutes", "minutes 0 to 59", { inputMode: "numeric", w: 140, error: shown["slurm.time_min"] ? true : undefined })}
          </div>
          <div className="sp-env-pair">
            {text("mem", "Memory per job", "Whole MiB, or GiB with one decimal", { inputMode: "decimal", w: 200 })}
            {unit("memUnit")}
          </div>
          <p className="sp-env-hint">
            With a Snakemake workflow profile: when you choose a Snakemake profile at Launch, the profile's resources and partition are
            used, not these.
          </p>
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
        <legend>Default profiles (optional)</legend>
        <p className="sp-env-hint">They preselect the profile at Launch when the pipeline has it; you can change it there.</p>
        {text("nextflow", "Default Nextflow profile")}
        {text("snakemake", "Default Snakemake profile")}
      </fieldset>
      {banner && (
        <div role="alert" className="sp-note sp-alert">
          {banner.text}{" "}
          {banner.reload && (
            <Button variant="default" size="xs" onClick={onReload} aria-describedby="env-reload-hint">
              Reload
            </Button>
          )}
          {banner.reload && (
            <span id="env-reload-hint" className="sp-env-hint">
              Reload discards your changes
            </span>
          )}
        </div>
      )}
      {!readOnly && (
      <div className="sp-actions">
        <Button
          type="submit"
          loading={sending}
          aria-disabled={why ? true : undefined}
          data-disabled={why ? true : undefined}
          aria-describedby={why ? "env-save-why" : undefined}
        >
          Save
        </Button>
        <Button variant="default" onClick={onCancel}>
          Cancel
        </Button>
        {why && (
          <span id="env-save-why" className="sp-alert">
            {why}
          </span>
        )}
      </div>
      )}
      {etag && !readOnly && <p className="sp-env-hint">Saving rewrites ~/.spectio/environments.toml; comments in it are not kept.</p>}
    </form>
  );
}
