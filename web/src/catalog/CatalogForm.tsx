import { Button, Radio, TextInput } from "@mantine/core";
import { useState } from "react";
import { ApiError, type CatalogBody, type CatalogItem, createCatalogEntry, replaceCatalogEntry } from "../api";
import { EngineMark } from "../shell/EngineMark";

// The one catalog entry form (ui-spec §4.7.1; board LiteCatalogEntry): the pages' new and edit,
// and later Save to catalog and the Manage dialog on Launch (FU-P3-87e). It checks how the
// fields are written (api §5.6 owns the rules; the server checks them again), never that the
// pipeline exists. A field's rule shows once it is typed in, a server `422` lands on its field,
// and Save stays focusable with why it waits — as in the Environments form (§4.8.1).

export interface Draft {
  name: string;
  label: string;
  engine: "nextflow" | "snakemake";
  location: string;
  revision: string;
  profile: string;
  params_file: string;
}
export const EMPTY: Draft = { name: "", label: "", engine: "nextflow", location: "", revision: "", profile: "", params_file: "" };
export const fromItem = (e: CatalogItem): Draft => ({
  ...{ name: e.name, label: e.label ?? "", engine: e.engine, location: e.location },
  ...{ revision: e.revision ?? "", profile: e.profile ?? "", params_file: e.params_file ?? "" },
});

type Field = keyof Draft;
type Errors = Partial<Record<string, string>>;
const NAMES: Record<Field, string> = {
  ...{ name: "Name", label: "Label", engine: "Engine", location: "Pipeline", revision: "Revision" },
  ...{ profile: "Default profile", params_file: "Params file" },
};
const NAME = /^[a-z][a-z0-9-]{0,31}$/;
const PROFILE = /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$/;
const PART = /^[A-Za-z0-9_][A-Za-z0-9._-]{0,99}$/; // never "", "." or ".." (spectio.locations)
const isRepo = (location: string) => location.trim() !== "" && !location.trim().startsWith("/");

export function toBody(d: Draft): { body: CatalogBody | null; errors: Errors } {
  const errors: Errors = {};
  const name = d.name.trim();
  if (name === "new") errors.name = "new is a reserved name";
  else if (!NAME.test(name)) errors.name = "Lowercase letters, digits and '-', up to 32, starting with a letter";
  if (d.label.length > 80) errors.label = "At most 80 characters";
  const location = d.location.trim();
  if (location === "") errors.location = "Give an absolute path or a repository.";
  const revision = isRepo(location) ? d.revision.trim() : "";
  if (isRepo(location) && revision === "") errors.revision = "Required for a repository";
  const profile = d.profile.trim();
  if (profile && !PROFILE.test(profile)) errors.profile = "One profile name: letters, digits, '_', '.' and '-'";
  const params = d.params_file.trim();
  const parts = params.split("/");
  if (params && (parts.length > 8 || !parts.every((p) => PART.test(p)))) errors.params_file = "A path inside the pipeline: no '..' and no leading '/'";
  else if (params && !/\.(json|ya?ml)$/.test(params)) errors.params_file = "A .json, .yaml or .yml file";
  if (Object.keys(errors).length) return { body: null, errors };
  return {
    body: { name, label: d.label.trim() || null, engine: d.engine, location, revision: revision || null, profile: profile || null, params_file: params || null },
    errors,
  };
}

const BANNERS: Record<string, string> = {
  "412": "This entry changed in another tab.",
  "catalog-file-changed": "The file changed on disk since this page read it.",
};

interface Props {
  initial: Draft;
  /** The entry's ETag when editing; null for a new entry. */
  etag: string | null;
  onSaved: (item: CatalogItem) => void;
  onCancel: () => void;
  /** Reload after a 412 or a file change: the page reads the entry again. */
  onReload: () => void;
}

export function CatalogForm({ initial, etag, onSaved, onCancel, onReload }: Props) {
  const [draft, setDraft] = useState<Draft>(initial);
  const [touched, setTouched] = useState<Set<string>>(new Set(etag ? Object.keys(NAMES) : []));
  const [server422, setServer422] = useState<Errors>({});
  const [banner, setBanner] = useState<{ text: string; reload: boolean } | null>(null);
  const [sending, setSending] = useState(false);
  const { body, errors } = toBody(draft);
  const shown: Errors = { ...Object.fromEntries(Object.entries(errors).filter(([k]) => touched.has(k))), ...server422 };
  const first = Object.keys(errors)[0] as Field | undefined;
  const why = first ? `Fix ${NAMES[first]} first` : null;

  const set = (key: Field) => (value: string) => {
    setDraft({ ...draft, [key]: value });
    setTouched(new Set(touched).add(key));
    setServer422(({ [key]: _, ...rest }) => rest);
  };
  const save = () => {
    if (!body) return setTouched(new Set(Object.keys(NAMES)));
    setSending(true);
    setBanner(null);
    (etag ? replaceCatalogEntry(body, etag) : createCatalogEntry(body))
      .then(onSaved)
      .catch((e: Error) => {
        if (e instanceof ApiError && e.slug === "catalog-entry-exists") return setServer422({ name: `An entry named ${body.name} exists` });
        if (e instanceof ApiError && e.errors.length) {
          // A field the form shows gets its message; the rest go in the banner.
          setServer422(Object.fromEntries(e.errors.filter((f) => f.field in NAMES).map((f) => [f.field, f.message])));
          const rest = e.errors.filter((f) => !(f.field in NAMES));
          return rest.length ? setBanner({ text: rest.map((f) => f.message).join(" ") || e.message, reload: false }) : undefined;
        }
        const known = e instanceof ApiError ? (BANNERS[String(e.status)] ?? BANNERS[e.slug ?? ""]) : undefined;
        setBanner({ text: known ?? e.message, reload: !!known });
      })
      .finally(() => setSending(false));
  };
  const text = (key: Field, label: string, hint: string | undefined, more: object = {}) => (
    <TextInput
      label={label}
      description={hint}
      inputWrapperOrder={["label", "input", "description", "error"]}
      value={draft[key]}
      onChange={(e) => set(key)(e.currentTarget.value)}
      error={shown[key]}
      {...more}
    />
  );
  const engine = (value: Draft["engine"], name: string) => (
    <Radio
      name="engine"
      value={value}
      checked={draft.engine === value}
      onChange={() => set("engine")(value)}
      label={<><EngineMark engine={value} size={16} named /> {name}</>}
      mt={6}
    />
  );
  return (
    <form className="sp-env-form" onSubmit={(e) => (e.preventDefault(), save())} noValidate>
      {text(
        "name",
        "Name",
        etag ? "The name cannot change: delete the entry and add it again under a new name." : "Lowercase letters, digits and '-', up to 32, starting with a letter. Used in links.",
        { readOnly: !!etag, "data-autofocus": true }, // a dialog opens with focus here (§4.7.1, Save to catalog)
      )}
      {text("label", "Label (optional)", undefined)}
      <fieldset>
        <legend>Engine</legend>
        {engine("nextflow", "Nextflow")}
        {engine("snakemake", "Snakemake")}
      </fieldset>
      {text("location", "Pipeline", "An absolute path your account can read, a GitHub or nf-core name such as nf-core/rnaseq, or an https:// or ssh URL.")}
      {isRepo(draft.location) &&
        text("revision", "Revision", "Required for a repository. A tag or a commit: a branch is fetched once and not updated.", { withAsterisk: true })}
      {text("profile", "Default profile (optional)", "Selected at Launch when the pipeline has it; you can change it there.")}
      {text(
        "params_file",
        "Params file (optional)",
        "A JSON or YAML file inside the pipeline, such as conf/test.yaml. Its values fill the Launch form, and Launch lists any it cannot place.",
      )}
      <p className="sp-env-hint">Saving checks how the fields are written, not that the pipeline exists: Launch reads it.</p>
      {banner && (
        <div role="alert" className="sp-note sp-alert">
          {banner.text}{" "}
          {banner.reload && (
            <>
              <Button variant="default" size="xs" onClick={onReload} aria-describedby="cat-reload-hint">Reload</Button>
              <span id="cat-reload-hint" className="sp-env-hint">Reload discards your changes</span>
            </>
          )}
        </div>
      )}
      <div className="sp-actions">
        <Button
          type="submit"
          loading={sending}
          aria-disabled={why ? true : undefined}
          data-disabled={why ? true : undefined}
          aria-describedby={why ? "cat-save-why" : undefined}
        >
          Save
        </Button>
        <Button variant="default" onClick={onCancel}>Cancel</Button>
        {why && <span id="cat-save-why" className="sp-alert">{why}</span>}
      </div>
      {etag && <p className="sp-env-hint">Saving rewrites ~/.spectio/catalog.toml; comments in it are not kept.</p>}
    </form>
  );
}
