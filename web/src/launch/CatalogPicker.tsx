import "../catalog/catalog.css";
import { Button, Drawer, Modal, NativeSelect, Skeleton } from "@mantine/core";
import { type ReactNode, useEffect, useRef, useState } from "react";
import type { CatalogItem, CatalogList as List } from "../api";
import { CatalogForm, type Draft, EMPTY, fromItem } from "../catalog/CatalogForm";
import { CatalogList, WAITS_ID, entryLabel, focusHeading, waitsFor } from "../catalog/CatalogList";
import { usePhone } from "../shell/layout";

// The catalog at Launch (FU-P3-87e; ui-spec §4.7.1 "At Launch"; boards LiteLaunch, MLiteLaunch):
// the "From your catalog" picker and its states, Manage catalog and Save to catalog in dialogs
// (full-height sheets on the phone), both on the list and form of the Catalog page (FU-P3-87d).
// Choosing an entry only tells the form; Launch fills its fields and Load inspects.

const ENGINES = { nextflow: "Nextflow", snakemake: "Snakemake" } as const;
const FILE_LINES: Record<string, string> = {
  refused: "Spectio does not read your catalog file: see Manage catalog",
  invalid: "Your catalog file has a mistake: see Manage catalog",
  unreachable: "Your catalog cannot be read right now",
};
export const where = (e: CatalogItem) => `${e.location}${e.revision ? `@${e.revision}` : ""}`;
/** "From the catalog: rnaseq-test · profile test · parameters from conf/test.yaml" */
const entryLine = (e: CatalogItem) =>
  ["From the catalog: " + e.name, e.profile && `profile ${e.profile}`, e.params_file && `parameters from ${e.params_file}`].filter(Boolean).join(" · ");

/** A pipeline's name as an entry name (§4.7.1): lowercase, every other character a `-`, cut to
 * 32, with `-2`, `-3` added on a clash. */
export function uniqueName(name: string, taken: string[]): string {
  const base = name.toLowerCase().replace(/[^a-z0-9-]/g, "-").replace(/^[^a-z]+/, "").slice(0, 32) || "pipeline";
  for (let n = 1; ; n++) {
    const suffix = n === 1 ? "" : `-${n}`;
    const found = base.slice(0, 32 - suffix.length) + suffix;
    if (!taken.includes(found)) return found;
  }
}

/** A dialog, a full-height sheet on the phone (`aria-modal`, focus returned to its opener). */
function Sheet({ opened, onClose, title, focusTitle, children }: { opened: boolean; onClose: () => void; title: string; focusTitle?: boolean; children: ReactNode }) {
  const phone = usePhone();
  const heading = { tabIndex: -1, "data-autofocus": focusTitle || undefined };
  if (phone) {
    return (
      <Drawer.Root opened={opened} onClose={onClose} position="bottom" size="100%">
        <Drawer.Overlay />
        <Drawer.Content className="sp-bottom-sheet">
          <Drawer.Header>
            <Drawer.Title className="sp-sheet-title" {...heading}>{title}</Drawer.Title>
            <Drawer.CloseButton aria-label="Close" />
          </Drawer.Header>
          <Drawer.Body>{children}</Drawer.Body>
        </Drawer.Content>
      </Drawer.Root>
    );
  }
  return (
    <Modal.Root opened={opened} onClose={onClose} size="lg" centered>
      <Modal.Overlay />
      <Modal.Content>
        <Modal.Header>
          <Modal.Title {...heading}>{title}</Modal.Title>
          <Modal.CloseButton aria-label="Close" />
        </Modal.Header>
        <Modal.Body>{children}</Modal.Body>
      </Modal.Content>
    </Modal.Root>
  );
}

interface Props {
  /** null while it loads. */
  data: List | null;
  failed: boolean;
  onRetry: () => Promise<unknown>;
  chosen: CatalogItem | null;
  /** An entry's name, or null for None. */
  onChoose: (name: string | null) => void;
  /** Clear and start empty. */
  onClear: () => void;
  /** Under the entry line: what the params file filled and left out. */
  children?: ReactNode;
}

export function CatalogPicker({ data, failed, onRetry, chosen, onChoose, onClear, children }: Props) {
  const phone = usePhone();
  const [managing, setManaging] = useState(false);
  const manage = (
    <Button variant="default" className="launch-cat-manage" fullWidth={phone} onClick={() => setManaging(true)}>
      Manage catalog
    </Button>
  );
  let body: ReactNode;
  if (failed) {
    body = (
      <div className="launch-env-state">
        <p className="sp-alert">The catalog could not be read.</p>
        <Button variant="default" onClick={onRetry}>Retry</Button>
      </div>
    );
  } else if (!data) {
    body = (
      <div className="launch-env-state" aria-busy="true">
        <p className="sp-muted">Loading the catalog…</p>
        <Skeleton height={58} />
      </div>
    );
  } else if (FILE_LINES[data.file.state]) {
    body = (
      <div className="launch-cat-row">
        <p className="sp-note">
          {FILE_LINES[data.file.state]}{" "}
          {data.file.state === "unreachable" && <Button variant="default" onClick={onRetry}>Retry</Button>}
        </p>
        {manage}
      </div>
    );
  } else if (data.items.length === 0) {
    body = (
      <div className="launch-cat-row">
        <p role="status">Your catalog is empty. Load a pipeline, then Save to catalog.</p>
        {manage}
      </div>
    );
  } else {
    body = (
      <>
        <div className="launch-cat-row">
          <NativeSelect
            className="sp-grow"
            label="From your catalog"
            inputWrapperOrder={["label", "input", "description", "error"]}
            data={[{ value: "", label: "None" }, ...data.items.map((e) => ({ value: e.name, label: `${entryLabel(e)} · ${ENGINES[e.engine]}` }))]}
            value={chosen?.name ?? ""}
            onChange={(e) => onChoose(e.currentTarget.value || null)}
            description={chosen && <span className="sp-mono sp-cat-location">{where(chosen)}</span>}
          />
          {manage}
          {chosen && <Button variant="subtle" fullWidth={phone} onClick={onClear}>Clear and start empty</Button>}
        </div>
        {chosen && <p role="status" className="sp-muted">{entryLine(chosen)}</p>}
      </>
    );
  }
  return (
    <div className="launch-cat">
      {body}
      {children}
      <ManageCatalog opened={managing} onClose={() => setManaging(false)} data={data} onReload={onRetry} />
    </div>
  );
}

/** Manage catalog (§4.7.1): the list in a dialog; Add and Edit put the form in its place, with Back. */
function ManageCatalog({ opened, onClose, data, onReload }: { opened: boolean; onClose: () => void; data: List | null; onReload: () => Promise<unknown> }) {
  const [editing, setEditing] = useState<{ draft: Draft; etag: string | null; opener: string } | null>(null);
  const [said, setSaid] = useState("");
  const close = () => (setEditing(null), onClose());
  const back = (say: string, focus: string | null, opener?: string) => {
    setEditing(null);
    void onReload().then(() => (setSaid(say), focusHeading(focus, opener)));
  };
  const why = waitsFor(data);
  return (
    <Sheet opened={opened} onClose={close} title="Manage catalog" focusTitle={!editing}>
      <p role="status" className="sp-sr">{said}</p>
      {editing ? (
        <EditInPlace editing={editing} onBack={back} onReload={onReload} />
      ) : (
        <>
          <Button
            mb="sm"
            onClick={() => !why && setEditing({ draft: EMPTY, etag: null, opener: "Add pipeline" })}
            aria-disabled={why ? true : undefined}
            data-disabled={why ? true : undefined}
            aria-describedby={why ? WAITS_ID : undefined}
          >
            Add pipeline
          </Button>
          <CatalogList
            data={data}
            onReload={onReload}
            onChanged={(say, focus) => back(say, focus)}
            onEdit={(e) => setEditing({ draft: fromItem(e), etag: e.etag, opener: `Edit ${e.name}` })}
          />
        </>
      )}
    </Sheet>
  );
}

function EditInPlace({ editing, onBack, onReload }: { editing: { draft: Draft; etag: string | null; opener: string }; onBack: (say: string, focus: string | null, opener?: string) => void; onReload: () => Promise<unknown> }) {
  const at = useRef<HTMLDivElement>(null);
  useEffect(() => void requestAnimationFrame(() => at.current?.querySelector<HTMLElement>("[data-autofocus]")?.focus()), []);
  const name = editing.etag ? editing.draft.name : null;
  const cancel = () => onBack("", name, editing.opener);
  return (
    <div ref={at}>
      <Button variant="subtle" mb="sm" onClick={cancel}>Back</Button>
      <CatalogForm initial={editing.draft} etag={editing.etag} onSaved={(saved) => onBack(`Saved ${saved.name}`, saved.name)} onCancel={cancel} onReload={() => void onReload()} />
    </div>
  );
}

/** The Loaded card's catalog action (§4.7.1): Save to catalog, or "In your catalog as …" with Edit
 * for a pipeline loaded from an entry; the entry form in a dialog either way. */
export function SaveToCatalog({ data, failed, entry, pipeline, draft, onSaved }: {
  data: List | null;
  failed: boolean;
  /** The entry the pipeline was loaded from, if any. */
  entry: CatalogItem | null;
  /** The loaded pipeline's name, for the new entry's. */
  pipeline: string;
  draft: Omit<Draft, "name" | "label">;
  onSaved: (item: CatalogItem) => void;
}) {
  const [open, setOpen] = useState(false);
  const why = failed ? "Waits until the catalog can be read" : !data ? "Waits until the catalog is read" : waitsFor(data);
  const initial: Draft = entry
    ? fromItem(entry)
    : { ...draft, name: uniqueName(pipeline, data?.items.map((e) => e.name) ?? []), label: "" };
  const saved = (item: CatalogItem) => (setOpen(false), onSaved(item));
  return (
    <span className="launch-cat-save">
      {entry && <span className="sp-muted">In your catalog as {entry.name}</span>}
      <Button
        variant="default"
        onClick={() => !why && setOpen(true)}
        aria-disabled={why ? true : undefined}
        data-disabled={why ? true : undefined}
        aria-describedby={why ? "cat-save-waits" : undefined}
        aria-label={entry ? `Edit ${entry.name}` : undefined}
      >
        {entry ? "Edit" : "Save to catalog"}
      </Button>
      {why && <span id="cat-save-waits" className="sp-sr">{why}</span>}
      <Sheet opened={open} onClose={() => setOpen(false)} title={entry ? `Edit ${entry.name}` : "Save to catalog"}>
        {open && <CatalogForm initial={initial} etag={entry?.etag ?? null} onSaved={saved} onCancel={() => setOpen(false)} onReload={() => setOpen(false)} />}
      </Sheet>
    </span>
  );
}
