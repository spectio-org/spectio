import "../environments/environments.css";
import "./catalog.css";
import { Button, Drawer, Modal, Skeleton } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { ApiError, type CatalogItem, type CatalogList as List, deleteCatalogEntry } from "../api";
import { EngineMark } from "../shell/EngineMark";
import { usePhone } from "../shell/layout";

// The one catalog list (ui-spec §4.7.1; boards LiteCatalog, LiteCatalogStates, MLiteCatalog): the
// Catalog page's, and later the Manage catalog dialog's on Launch (FU-P3-87e), which passes
// `onEdit` so Edit opens the form in the dialog instead of the entry's page.

const FILE_LINES: Record<string, (path: string, detail: string) => string> = {
  refused: (p, d) => `Spectio does not read ${p}: ${d}. Fix it with the command shown; Spectio will not change it.`,
  invalid: (p, d) => `${p} has a mistake: ${d}. No pipeline is listed until it is fixed.`,
  unreachable: () => "Spectio cannot read the cluster's files right now. Your catalog is not listed until they answer.",
};
const WAITS: Record<string, string> = {
  refused: "Waits until the catalog file can be read",
  invalid: "Waits until the mistake in the file is fixed",
  unreachable: "Waits until the cluster's files can be read",
};
/** Why Add pipeline waits for this file state (§4.6 pattern), or null; `WAITS_ID` describes it. */
export const waitsFor = (data: List | null) => (data && WAITS[data.file.state]) || null;
export const WAITS_ID = "cat-waits";

// Only these known refusals are sure to have changed nothing, so only they say so; a network
// failure or a 5xx may come after the server deleted the entry.
const UNCHANGED = " Reload reads it again; nothing was deleted.";
const PROBLEMS: Record<string, string> = {
  "412": "This entry changed in another tab." + UNCHANGED,
  "catalog-file-changed": "The file changed on disk since this page read it." + UNCHANGED,
  "catalog-file-unusable": "The catalog file cannot be changed right now." + UNCHANGED,
};
export const problem = (e: Error) => (e instanceof ApiError ? (PROBLEMS[String(e.status)] ?? PROBLEMS[e.slug ?? ""]) : undefined) ?? e.message;

const headingId = (name: string) => `cat-${name}`;
const byLabel = (label: string) =>
  [...document.querySelectorAll<HTMLElement>("a, button")].find((el) => (el.getAttribute("aria-label") ?? el.textContent) === label);
/** Focus the opener (its label), else the entry's heading, else the page's (or dialog's) h1 (§4.8.1). */
export const focusHeading = (name: string | null, opener?: string) =>
  requestAnimationFrame(() => ((opener && byLabel(opener)) || document.getElementById(name ? headingId(name) : "") || document.querySelector("h1"))?.focus());

const ENGINES = { nextflow: "Nextflow", snakemake: "Snakemake" } as const;
export const entryLabel = (e: CatalogItem) => e.label ?? e.name;

/** Delete asks first: a dialog, a bottom sheet on the phone; a 412 or a 409 in place, with Reload. */
export function DeleteAsk({ entry, onClose, onDeleted, onReload }: { entry: CatalogItem | null; onClose: () => void; onDeleted: () => void; onReload: () => void }) {
  const phone = usePhone();
  const [error, setError] = useState<string | null>(null);
  const close = () => (setError(null), onClose());
  const body = entry && (
    <>
      <p>It leaves your catalog and the picker at Launch. Runs launched from it keep their pipeline.</p>
      {error && <p role="alert" className="sp-note sp-alert">{error}</p>}
      <div className="sp-actions">
        <Button variant="default" data-autofocus onClick={close}>Cancel</Button>
        {error ? (
          <Button variant="default" onClick={() => (close(), onReload())}>Reload</Button>
        ) : (
          <Button color="red" onClick={() => deleteCatalogEntry(entry.name, entry.etag).then(onDeleted, (e: Error) => setError(problem(e)))}>
            Delete {entry.name}
          </Button>
        )}
      </div>
    </>
  );
  const props = { opened: !!entry, onClose: close, title: entry && `Delete ${entry.name}?`, returnFocus: true };
  return phone ? (
    <Drawer {...props} position="bottom" classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}>{body}</Drawer>
  ) : (
    <Modal {...props} centered>{body}</Modal>
  );
}

interface Props {
  /** null while the list loads. */
  data: List | null;
  /** After a delete: what the polite region says and which heading takes the focus. */
  onChanged: (say: string, focus: string | null) => void;
  /** Retry (`unreachable`) and the Delete dialog's Reload. */
  onReload: () => void;
  /** Edit in place (the Manage dialog); without it, Edit links to `/catalog/<name>`. */
  onEdit?: (entry: CatalogItem) => void;
}

export function CatalogList({ data, onChanged, onReload, onEdit }: Props) {
  const phone = usePhone();
  const [asking, setAsking] = useState<CatalogItem | null>(null);
  const items = data?.items ?? [];
  const state = data?.file.state ?? "ok";
  const why = waitsFor(data);
  const removed = (entry: CatalogItem) => {
    const i = items.findIndex((e) => e.name === entry.name);
    setAsking(null);
    onChanged(`Deleted ${entry.name}`, (items[i + 1] ?? items[i - 1])?.name ?? null);
  };
  const edit = (entry: CatalogItem) => {
    const look = { variant: "default", size: "sm", "aria-label": `Edit ${entry.name}` };
    if (onEdit) return <Button {...look} onClick={() => onEdit(entry)}>Edit</Button>;
    return <Button component={Link} to={`/catalog/${entry.name}`} {...look}>Edit</Button>;
  };
  return (
    <>
      {data === null && <p className="sp-muted">Loading the catalog…</p>}
      {data && FILE_LINES[state] && (
        <div className="sp-note" role={state === "unreachable" ? undefined : "note"}>
          {FILE_LINES[state](data.file.path, data.file.detail ?? "")}{" "}
          {state === "unreachable" && <Button variant="default" size="xs" onClick={onReload}>Retry</Button>}
        </div>
      )}
      {why && <p id={WAITS_ID} className="sp-env-hint">Add pipeline: {why.toLowerCase()}</p>}
      <div className="sp-envs">
        {data === null &&
          [0, 1].map((i) => (
            <article key={i} className="sp-card sp-env" aria-hidden>
              <Skeleton height={18} width="45%" />
              <Skeleton height={12} mt={12} width="70%" />
            </article>
          ))}
        {items.map((entry) => {
          const extras = [entry.profile && `profile ${entry.profile}`, entry.params_file && `parameters from ${entry.params_file}`].filter(Boolean);
          return (
            <article key={entry.name} className="sp-card sp-env">
              <div className="sp-env-top">
                <h2 id={headingId(entry.name)} tabIndex={-1}>
                  {/* The phone (UX-PRE-FU87-09): the whole card opens the entry; its actions are there. */}
                  {!phone ? entryLabel(entry) : onEdit ? (
                    <button type="button" className="sp-env-link sp-cat-open" onClick={() => onEdit(entry)}>{entryLabel(entry)}</button>
                  ) : (
                    <Link to="/catalog/$name" params={{ name: entry.name }} className="sp-env-link">{entryLabel(entry)}</Link>
                  )}
                </h2>
                <span className="sp-chip">
                  <EngineMark engine={entry.engine} size={16} named /> {ENGINES[entry.engine]}
                </span>
              </div>
              {entry.label && <span className="sp-mono">{entry.name}</span>}
              <p className="sp-mono sp-cat-location">
                {entry.location}
                {entry.revision && <span className="sp-muted"> @{entry.revision}</span>}
              </p>
              {extras.length > 0 && <p className="sp-env-hint">{extras.join(" · ")}</p>}
              {!phone && (
                <div className="sp-actions">
                  {edit(entry)}
                  <Button variant="light" color="red" size="sm" aria-label={`Delete ${entry.name}`} onClick={() => setAsking(entry)}>Delete</Button>
                </div>
              )}
            </article>
          );
        })}
      </div>
      {data && items.length === 0 && (state === "ok" || state === "missing") && (
        <p className="sp-muted">Your catalog is empty. Add pipeline saves a path or a repository under a name, to pick at Launch.</p>
      )}
      {data && <p className="sp-env-hint">Saved in <span className="sp-mono">{data.file.path}</span></p>}
      <DeleteAsk entry={asking} onClose={() => setAsking(null)} onDeleted={() => asking && removed(asking)} onReload={onReload} />
    </>
  );
}
