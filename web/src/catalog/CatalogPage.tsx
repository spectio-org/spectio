import "../runs/runs.css";
import { Button } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type CatalogItem, type CatalogList as List, getCatalogEntry, listCatalog } from "../api";
import { usePageCrumb } from "../shell/crumb";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";
import { CatalogForm, EMPTY, fromItem } from "./CatalogForm";
import { CatalogList, DeleteAsk, WAITS_ID, entryLabel, focusHeading, waitsFor } from "./CatalogList";

// The Catalog pages (FU-P3-87d; ui-spec §4.7.1): `/catalog`, the list, reached from Home and
// headed Launch › Catalog (the sidebar marks Launch); `/catalog/new` and `/catalog/<name>`, the
// form. The focus rules are those of the Environments pages (§4.8.1).

/** What the list says and focuses when it opens next: after Save, "Saved <name>"; after Cancel,
 * the opener (its label: "Edit <name>", "Add pipeline"), else the row's heading. */
let next: { focus: string | null; say: string; opener?: string } | null = null;

export function CatalogPage() {
  const [data, setData] = useState<List | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const load = useCallback(() => listCatalog().then(setData, (e: Error) => setError(e.message)), []);
  useEffect(() => {
    load().then(() => {
      if (next) (setSaid(next.say), focusHeading(next.focus, next.opener));
      next = null;
    });
  }, [load]);
  const why = waitsFor(data);
  const add = why ? (
    <Button size="md" aria-disabled data-disabled aria-describedby={WAITS_ID}>Add pipeline</Button>
  ) : (
    <Button component={Link} to="/catalog/new" size="md">Add pipeline</Button>
  );
  const count = data && `${data.items.length} ${data.items.length === 1 ? "pipeline" : "pipelines"}`;
  return (
    <div className="sp-page">
      <Link to="/launch" className="sp-link sp-cat-back">Back to Launch</Link>
      <PageHead section="launch" title="Catalog" sub={`Pipelines saved under a name, to pick at Launch${count ? ` · ${count}` : ""}`} action={add} />
      <p role="status" className="sp-sr">{said}</p>
      {error ? (
        <>
          <p role="alert" className="sp-note sp-alert">The catalog could not be read. {error}</p>
          <Button variant="default" style={{ alignSelf: "flex-start" }} onClick={() => (setError(null), load())}>Retry</Button>
        </>
      ) : (
        <CatalogList data={data} onReload={load} onChanged={(say, focus) => load().then(() => (setSaid(say), focusHeading(focus)))} />
      )}
    </div>
  );
}

/** `/catalog/new` and `/catalog/<name>`. */
export function CatalogEntryPage({ name }: { name: string | null }) {
  const navigate = useNavigate();
  const phone = usePhone();
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [failed, setFailed] = useState<{ missing: boolean; text: string } | null>(null);
  const [round, setRound] = useState(0);
  const [asking, setAsking] = useState(false);
  usePageCrumb(name ?? "Add pipeline");
  // Add and Edit open with focus on the page's heading (§4.8.1, inbox #146 item 10)
  const ready = !name || !!item || !!failed;
  useEffect(() => {
    if (ready) document.querySelector<HTMLElement>("h1")?.focus();
  }, [ready]);
  useEffect(() => {
    if (name)
      getCatalogEntry(name).then(setItem, (e: Error) =>
        setFailed(e instanceof ApiError && e.status === 404 ? { missing: true, text: `No entry named ${name}` } : { missing: false, text: e.message }),
      );
  }, [name, round]);
  const reload = () => setRound((r) => r + 1);
  const toList = (say: string, focus: string | null, opener?: string) => ((next = { focus, say, opener }), navigate({ to: "/catalog" }));
  if (failed?.missing) {
    return (
      <div className="sp-page">
        <h1 className="sp-page-title" tabIndex={-1}>{failed.text}</h1>
        <p>It may have been deleted in another tab. <Link to="/catalog">Your catalog</Link></p>
      </div>
    );
  }
  if (failed) {
    return (
      <div className="sp-page">
        <PageHead section="launch" title={name} />
        <p role="alert" className="sp-note sp-alert">{name} could not be read. {failed.text}</p>
        <Button variant="default" style={{ alignSelf: "flex-start" }} onClick={() => (setFailed(null), reload())}>Retry</Button>
      </div>
    );
  }
  if (name && !item) return <p className="sp-muted">Loading the catalog…</p>;
  return (
    <div className="sp-page">
      <PageHead
        section="launch"
        title={item ? entryLabel(item) : "Add pipeline"}
        sub="A path or a repository under a name, with the profile and parameters Launch fills in"
      />
      <CatalogForm
        key={`${round}:${item?.etag ?? ""}`}
        initial={item ? fromItem(item) : EMPTY}
        etag={item?.etag ?? null}
        onSaved={(saved) => toList(`Saved ${saved.name}`, saved.name)}
        onCancel={() => toList("", name, name ? `Edit ${name}` : "Add pipeline")}
        onReload={reload}
      />
      {/* The phone (UX-PRE-FU87-09): the entry's actions under its form, Delete last. */}
      {phone && item && (
        <div role="group" aria-labelledby="cat-more" className="sp-env-more">
          <h2 id="cat-more">More for this entry</h2>
          <Button variant="light" color="red" fullWidth onClick={() => setAsking(true)}>Delete {item.name}</Button>
          <DeleteAsk entry={asking ? item : null} onClose={() => setAsking(false)} onDeleted={() => toList(`Deleted ${item.name}`, null)} onReload={reload} />
        </div>
      )}
    </div>
  );
}
