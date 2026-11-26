import { Button, Checkbox, Select, TextInput } from "@mantine/core";
import { type ReactNode, useState } from "react";
import { ApiError } from "../api";
import type { Errors, Unit } from "./fields";

// What the Compute and Profile forms share (ui-spec §4.8.1): every field is a labelled native
// input; a field's rule shows under it as soon as it is typed in, a server `422` lands on its
// field, and Save stays focusable with why it waits.

interface Config<D, B, S> {
  initial: D;
  /** The item's ETag when editing; null for a new one. */
  etag: string | null;
  readOnly: boolean;
  /** The API's field path to the words the form calls it. */
  names: Record<string, string>;
  /** The API's field path of each draft key. */
  fieldOf: Partial<Record<keyof D & string, string>>;
  toBody: (draft: D) => { body: B | null; errors: Errors };
  send: (body: B, etag: string | null) => Promise<S>;
  onSaved: (saved: S) => void;
  /** "compute" or "profile", for the banners. */
  noun: string;
}

export function useFormKit<D extends { [K in keyof D]: D[K] }, B, S>(cfg: Config<D, B, S>) {
  const { names, fieldOf, readOnly, etag, noun } = cfg;
  const [draft, setDraft] = useState<D>(cfg.initial);
  const [touched, setTouched] = useState<Set<string>>(new Set(etag ? Object.keys(names) : []));
  const [server422, setServer422] = useState<Errors>({});
  const [banner, setBanner] = useState<{ text: string; reload: boolean } | null>(null);
  const [sending, setSending] = useState(false);
  const { body, errors } = cfg.toBody(draft);
  const shown = { ...Object.fromEntries(Object.entries(errors).filter(([k]) => touched.has(k))), ...server422 };
  const first = Object.keys(errors)[0];
  const why = first ? `Fix ${names[first] ?? first} first` : null;

  /** Changes `patch` and marks the API fields it touches as typed in. */
  const update = (patch: Partial<D>) => {
    setDraft((d) => ({ ...d, ...patch }));
    const fields = Object.keys(patch).map((k) => fieldOf[k as keyof D & string] ?? "");
    setTouched((t) => new Set([...t, ...fields]));
    setServer422((e) => Object.fromEntries(Object.entries(e).filter(([k]) => !fields.includes(k))));
  };
  const set = (key: keyof D & string) => (value: string) => update({ [key]: value } as Partial<D>);

  const known = { "412": `This ${noun} changed in another tab.`, "-file-changed": "The file changed on disk since this page read it." };
  const save = () => {
    if (!body) return setTouched(new Set(Object.keys(names)));
    setSending(true);
    setBanner(null);
    cfg
      .send(body, etag)
      .then(cfg.onSaved)
      .catch((e: Error) => {
        if (e instanceof ApiError && e.status === 409 && /-exists$/.test(e.slug ?? "")) return setServer422({ name: e.message });
        if (e instanceof ApiError && e.errors.length) {
          // A field the form shows gets its message; the rest (`executor`, `body`…) go in the banner.
          setServer422(Object.fromEntries(e.errors.filter((f) => f.field in names).map((f) => [f.field, f.message])));
          const rest = e.errors.filter((f) => !(f.field in names));
          return rest.length ? setBanner({ text: rest.map((f) => f.message).join(" ") || e.message, reload: false }) : undefined;
        }
        const text = e instanceof ApiError ? (e.status === 412 ? known["412"] : e.slug?.endsWith("-file-changed") ? known["-file-changed"] : undefined) : undefined;
        setBanner({ text: text ?? e.message, reload: !!text });
      })
      .finally(() => setSending(false));
  };

  const text = (key: keyof D & string, label: string, hint?: string, more: object = {}) => (
    <TextInput
      label={label}
      description={hint}
      inputWrapperOrder={["label", "input", "description", "error"]}
      value={draft[key] as string}
      onChange={(e) => set(key)(e.currentTarget.value)}
      error={shown[fieldOf[key] ?? ""]}
      readOnly={readOnly}
      {...more}
    />
  );
  const unit = (key: keyof D & string) => (
    <Select
      size="sm"
      label="Unit"
      allowDeselect={false}
      data={["MiB", "GiB"]}
      value={draft[key] as string}
      onChange={(v) => v && set(key)(v as Unit)}
      disabled={readOnly}
      w={100}
    />
  );
  return { draft, update, set, shown, text, unit, save, banner, sending, why, anyShown: Object.keys(shown).length > 0 };
}

type Kit = Pick<ReturnType<typeof useFormKit>, "save" | "banner" | "sending" | "why" | "anyShown">;

/** The form element with its banner, its actions and the note on what saving rewrites. */
export function FormFrame({
  kit,
  etag,
  readOnly,
  saveLabel,
  file,
  onCancel,
  onReload,
  children,
}: {
  kit: Kit;
  etag: string | null;
  readOnly: boolean;
  saveLabel: string;
  /** The file Save rewrites, for the note under an edit. */
  file: string;
  onCancel: () => void;
  onReload: () => void;
  children: ReactNode;
}) {
  const { banner, why } = kit;
  return (
    <form className="sp-env-form" onSubmit={(e) => (e.preventDefault(), kit.save())} noValidate>
      {children}
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
            loading={kit.sending}
            aria-disabled={why ? true : undefined}
            data-disabled={why ? true : undefined}
            aria-describedby={why ? "env-save-why" : undefined}
          >
            {saveLabel}
          </Button>
          <Button variant="default" onClick={onCancel}>
            Cancel
          </Button>
          {why && (
            <span id="env-save-why" className={kit.anyShown ? "sp-alert" : "sp-env-hint"}>
              {why}
            </span>
          )}
        </div>
      )}
      {etag && !readOnly && <p className="sp-env-hint">Saving rewrites ~/.spectio/{file}; comments in it are not kept.</p>}
    </form>
  );
}

/** Conda and Apptainer as checkboxes; `offered` limits them to what the compute has. */
export function SoftwareChecks({
  value,
  offered,
  onChange,
  error,
  readOnly,
}: {
  value: string[];
  offered: readonly string[];
  onChange: (value: string[]) => void;
  error?: string;
  readOnly: boolean;
}) {
  return (
    <Checkbox.Group value={value} onChange={onChange} error={error}>
      {offered.includes("conda") && <Checkbox value="conda" label="Conda" description="--software-deployment-method conda" mt={6} disabled={readOnly} />}
      {offered.includes("apptainer") && <Checkbox value="apptainer" label="Apptainer" description="--software-deployment-method apptainer" mt={6} disabled={readOnly} />}
    </Checkbox.Group>
  );
}
