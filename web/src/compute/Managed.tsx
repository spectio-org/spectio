import "../runs/runs.css";
import "./compute.css";
import { Button, Drawer, Modal, SegmentedControl } from "@mantine/core";
import { Link, useNavigate, useSearch } from "@tanstack/react-router";
import { Fragment, type ReactNode, useCallback, useEffect, useState } from "react";
import { ApiError, type ServerVersion, type StoreFile } from "../api";
import { type IconName, Icon } from "../icons";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";
import { EmptyState, ErrorPanel, SkeletonRows } from "../shell/States";
import { Toolbar } from "../shell/Toolbar";
import { label } from "../environments/fields";
import { copyName } from "./fields";

// The lists and form pages of Compute and of Profiles (FU-P3-86f, #408; ui-spec §4.8.1; boards
// LiteEnvironments, LiteEnvironmentEdit, LiteEnvironmentsStates): the list with Delete, and the
// form's page. The two differ in what a card says and in their form; `Kind` holds the difference.

export interface Item {
  name: string;
  label: string | null;
  builtin: boolean;
  etag: string;
}

/** What differs between the Compute pages and the Profiles pages. */
export interface Kind<T extends Item, C> {
  path: "/compute" | "/profiles";
  /** "compute", "profile": for the sentences and the file's lines. */
  noun: string;
  nounPlural: string;
  title: string;
  newLabel: string;
  sub: string;
  /** Under the Delete dialog's first line. */
  deleteNote: string;
  emptyHint: string;
  icon: IconName;
  list: (signal?: AbortSignal) => Promise<{ items: T[]; file: StoreFile; context: C }>;
  get: (name: string) => Promise<T>;
  remove: (name: string, etag: string) => Promise<null>;
  /** The kind column's heading and the chip beside a card's title. */
  kindHeading: string;
  kindOf: (item: T, context: C) => { key: string; icon: IconName; chip: string };
  /** The card's summary line, and a second muted line when there is one. */
  summary: (item: T, context: C, server: ServerVersion | null) => string;
  extra?: (item: T, context: C) => string | null;
  /** Why the item cannot be used, or null. */
  unusable: (item: T, context: C) => string | null;
  /** The form, prefilled from `item` (an edit or a duplicate) or empty. */
  form: (p: {
    item: T | null;
    duplicate: { name: string; clearLabel: boolean } | null;
    etag: string | null;
    readOnly: boolean;
    onSaved: (saved: T) => void;
    onCancel: () => void;
    onReload: () => void;
  }) => ReactNode;
}

/** What the list says and focuses when it opens next: after Save, "Saved <name>"; after Cancel,
 * the opener (its label: "Edit <name>", "New compute"), else the card's heading. */
let next: { focus: string | null; say: string; opener?: string } | null = null;

/** `?view=table` (FU-P3-111): the list's view, cards when absent. */
export const listSearch = (search: Record<string, unknown>): { view?: "table" } => (search.view === "table" ? { view: "table" } : {});
/** The list's last view, so the form returns to it. */
let shownView: { view?: "table" } = {};

/** The new-and-duplicate route's `?from=<name>`. */
export const fromSearch = (search: Record<string, unknown>): { from?: string } =>
  typeof search.from === "string" && /^[a-z][a-z0-9-]{0,31}$/.test(search.from) ? { from: search.from } : {};

const KIND_BADGE = "sp-env-kind";
/** A built-in stays read only: its Duplicate is "Duplicate to edit". */
const duplicateWords = (item: Pick<Item, "builtin">) => (item.builtin ? "Duplicate to edit" : "Duplicate");

const FILE_LINES: Record<string, (noun: string, path: string, detail: string) => string> = {
  refused: (_n, p, d) => `Spectio does not read ${p}: ${d}. Fix it with the command shown; Spectio will not change it.`,
  invalid: (n, p, d) => `${p} has a mistake: ${d}. Only the built-in ${n} are listed until it is fixed.`,
  unreachable: (n) => `Spectio cannot read the cluster's files right now. Only the built-in ${n} are listed.`,
};
const WAITS: Record<string, string> = {
  refused: "Waits until the file can be read",
  invalid: "Waits until the mistake in the file is fixed",
  unreachable: "Waits until the cluster's files can be read",
};
/** An error as the page shows it: the known 412s in words, else the message. */
const problem = (e: Error, noun: string) => {
  if (!(e instanceof ApiError)) return e.message;
  if (e.status === 412) return `This ${noun} changed in another tab.`;
  return e.slug?.endsWith("-file-changed") ? "The file changed on disk since this page read it." : e.message;
};
const headingId = (name: string) => `env-${name}`;
const byLabel = (label: string) =>
  [...document.querySelectorAll<HTMLElement>("a, button")].find((el) => (el.getAttribute("aria-label") ?? el.textContent) === label);
const focusHeading = (name: string | null, opener?: string) =>
  requestAnimationFrame(() => ((opener && byLabel(opener)) || document.getElementById(name ? headingId(name) : "") || document.querySelector("h1"))?.focus());

/** A link to one item's page. */
function ItemLink({ path, name, className, children }: { path: Kind<Item, unknown>["path"]; name: string; className?: string; children: string }) {
  return path === "/compute" ? (
    <Link to="/compute/$name" params={{ name }} className={className}>{children}</Link>
  ) : (
    <Link to="/profiles/$name" params={{ name }} className={className}>{children}</Link>
  );
}

/** A link or, while the file is not usable, a button described by why it waits (§4.6 pattern). */
function Waiting({ why, to, children, primary, ...rest }: { why: string | null; to: string; children: string; primary?: boolean; "aria-label"?: string }) {
  const look = { variant: primary ? "filled" : "default" };
  if (!why) return <Button component={Link} to={to} {...look} {...rest}>{children}</Button>;
  return <Button {...look} aria-disabled data-disabled aria-describedby="env-waits" {...rest}>{children}</Button>;
}
const waits = (why: string | null) => (why ? { "aria-disabled": true, "data-disabled": true, "aria-describedby": "env-waits" } : {});

/** Delete asks first: a dialog, a bottom sheet on the phone; a 412 or a file change in place, with Reload. */
function DeleteAsk({ item, kind, onClose, onDeleted, onReload }: { item: Item | null; kind: Pick<Kind<Item, unknown>, "noun" | "remove" | "deleteNote">; onClose: () => void; onDeleted: () => void; onReload: () => void }) {
  const phone = usePhone();
  const [error, setError] = useState<string | null>(null);
  const close = () => (setError(null), onClose());
  const body = item && (
    <>
      <p>Runs that used it keep their settings. {kind.deleteNote}</p>
      {error && <p role="alert" className="sp-note sp-alert">{error}</p>}
      <div className="sp-actions">
        <Button variant="default" data-autofocus onClick={close}>Cancel</Button>
        {error ? (
          <Button variant="default" onClick={() => (close(), onReload())}>Reload</Button>
        ) : (
          <Button color="red" onClick={() => kind.remove(item.name, item.etag).then(onDeleted, (e: Error) => setError(problem(e, kind.noun)))}>
            Delete {item.name}
          </Button>
        )}
      </div>
    </>
  );
  const props = { opened: !!item, onClose: close, title: item && `Delete ${item.name}?`, returnFocus: true };
  return phone ? (
    <Drawer {...props} position="bottom" classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}>{body}</Drawer>
  ) : (
    <Modal {...props} centered>{body}</Modal>
  );
}

export function ManagedList<T extends Item, C>({ kind }: { kind: Kind<T, C> }) {
  const server = useServer();
  const phone = usePhone();
  const navigate = useNavigate();
  const view = listSearch(useSearch({ strict: false }));
  shownView = view;
  const [data, setData] = useState<{ items: T[]; file: StoreFile; context: C } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const [asking, setAsking] = useState<T | null>(null);
  const load = useCallback(() => kind.list().then(setData, (e: Error) => setError(e.message)), [kind]);
  useEffect(() => {
    load().then(() => {
      if (next) (setSaid(next.say), focusHeading(next.focus, next.opener));
      next = null;
    });
  }, [load]);

  if (error) {
    return (
      <div className="sp-page">
        <PageHead section="environments" title={kind.title} />
        <ErrorPanel onRetry={() => (setError(null), load())}>{kind.title} could not be read. {error}</ErrorPanel>
      </div>
    );
  }
  const items = data?.items ?? [];
  const state = data?.file.state ?? "ok";
  const why = WAITS[state] ?? null;
  const done = (say: string, focus: string | null) => load().then(() => (setSaid(say), focusHeading(focus)));
  const removed = (item: T) => {
    const i = items.findIndex((e) => e.name === item.name);
    const after = items[i + 1] ?? items[i - 1];
    setAsking(null);
    done(`Deleted ${item.name}`, after?.name ?? null);
  };
  const own = items.filter((e) => !e.builtin).length;
  const KindIcon = ({ item }: { item: T }) => {
    const k = kind.kindOf(item, data!.context);
    return (
      <span className={KIND_BADGE} data-kind={k.key}>
        <Icon name={k.icon} />
      </span>
    );
  };
  const chip = (item: T) => <span className="sp-chip">{kind.kindOf(item, data!.context).chip}</span>;
  const actions = (item: T) => (
    <div className="sp-actions">
      {!item.builtin && <Waiting why={why} to={`${kind.path}/${encodeURIComponent(item.name)}`} aria-label={`Edit ${item.name}`}>Edit</Waiting>}
      <Waiting why={why} to={`${kind.path}/new?from=${encodeURIComponent(item.name)}`} aria-label={`${duplicateWords(item)} ${item.name}`}>{duplicateWords(item)}</Waiting>
      {!item.builtin && (
        <Button variant="default" size="sm" aria-label={`Delete ${item.name}`} onClick={() => !why && setAsking(item)} {...waits(why)}>
          Delete
        </Button>
      )}
    </div>
  );
  const extra = (item: T) => kind.extra?.(item, data!.context) ?? null;
  const unusable = (item: T) => kind.unusable(item, data!.context);
  const show = (table: boolean) => navigate({ to: kind.path, search: table ? { view: "table" } : {}, replace: true });
  return (
    <div className="sp-page">
      <PageHead
        section="environments"
        title={kind.title}
        sub={data && kind.sub}
        primary={<Waiting why={why} to={`${kind.path}/new`} primary>{kind.newLabel}</Waiting>}
      />
      <Toolbar
        label={`${kind.title} view`}
        filters={
          <SegmentedControl
            size="sm"
            aria-label={`Show ${kind.nounPlural} as`}
            data={["Cards", "Table"]}
            value={view.view === "table" ? "Table" : "Cards"}
            onChange={(v) => show(v === "Table")}
          />
        }
        caption={data && `${items.length} ${items.length === 1 ? kind.noun : kind.nounPlural}`}
      />
      <p role="status" className="sp-sr">{said}</p>
      {data === null && <SkeletonRows rows={2} height={120} label={`Loading ${kind.nounPlural}…`} />}
      {data && FILE_LINES[state] && (
        <div className="sp-note" role={state === "unreachable" ? undefined : "note"}>
          {FILE_LINES[state](kind.nounPlural, data.file.path, data.file.detail ?? "")}{" "}
          {state === "unreachable" && <Button variant="default" size="xs" onClick={load}>Retry</Button>}
        </div>
      )}
      {why && <p id="env-waits" className="sp-env-hint">{kind.newLabel}, Edit, Duplicate and Delete: {why.toLowerCase()}</p>}
      {data && view.view !== "table" && <div className="sp-envs">
        {items.map((item) => (
          <article key={item.name} className="sp-card sp-env">
            <div className="sp-env-top">
              <KindIcon item={item} />
              <h2 id={headingId(item.name)} tabIndex={-1}>
                {/* The phone (UX-PRE-FU86-R1-22): the whole card is this link; its actions are on the page. */}
                {phone ? <ItemLink path={kind.path} name={item.name} className="sp-env-link">{label(item)}</ItemLink> : label(item)}
              </h2>
              {chip(item)}
              {item.builtin && <span className="sp-chip">Built-in</span>}
            </div>
            {item.label && <span className="sp-mono">{item.name}</span>}
            <p>{kind.summary(item, data.context, server)}</p>
            {extra(item) && <p className="sp-env-hint">{extra(item)}</p>}
            {unusable(item) && <p className="sp-note">Not usable: {unusable(item)}</p>}
            {!phone && actions(item)}
          </article>
        ))}
      </div>}
      {data && view.view === "table" && (
        <div className="sp-table-wrap">
          <table className="sp-table sp-env-table">
            <caption className="sp-sr">{kind.title}, built-ins first</caption>
            <thead>
              <tr>
                <th scope="col">{kind.noun[0]!.toUpperCase() + kind.noun.slice(1)}</th>
                <th scope="col">{kind.kindHeading}</th>
                <th scope="col">Settings</th>
                <th scope="col">State</th>
                {!phone && <th scope="col">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.name}>
                  <th scope="row" id={headingId(item.name)} tabIndex={-1}>
                    <span className="sp-env-name">
                      <KindIcon item={item} />
                      <span>
                        {phone ? <ItemLink path={kind.path} name={item.name}>{label(item)}</ItemLink> : label(item)}
                        {item.label && <span className="sp-mono sp-env-hint"> {item.name}</span>}
                      </span>
                    </span>
                  </th>
                  <td>{chip(item)}</td>
                  <td>
                    {kind.summary(item, data.context, server)}
                    {extra(item) && <span className="sp-env-hint sp-env-line">{extra(item)}</span>}
                  </td>
                  <td>
                    {item.builtin && <span className="sp-chip">Built-in</span>}
                    {unusable(item) && <span className="sp-env-line">Not usable: {unusable(item)}</span>}
                  </td>
                  {!phone && <td>{actions(item)}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && own === 0 && (state === "ok" || state === "missing") && <EmptyState icon={kind.icon}>{kind.emptyHint}</EmptyState>}
      {data && <p className="sp-env-hint">Saved in <span className="sp-mono">{data.file.path}</span></p>}
      <DeleteAsk item={asking} kind={kind as unknown as Kind<Item, unknown>} onClose={() => setAsking(null)} onDeleted={() => asking && removed(asking)} onReload={load} />
    </div>
  );
}

/** `<path>/new` (`?from=<name>` to duplicate) and `<path>/<name>`. */
export function ManagedItem<T extends Item, C>({ kind, name, from }: { kind: Kind<T, C>; name: string | null; from?: string }) {
  const navigate = useNavigate();
  const phone = usePhone();
  const [item, setItem] = useState<T | null>(null);
  const [taken, setTaken] = useState<string[]>([]);
  const [failed, setFailed] = useState<{ missing: boolean; text: string } | null>(null);
  const [round, setRound] = useState(0);
  const [asking, setAsking] = useState(false);
  const wanted = name ?? from ?? null;
  usePageCrumb(name ?? kind.newLabel);
  // New, Edit and Duplicate open with focus on the page's heading (§4.8.1, inbox #146 item 10)
  const ready = !wanted || !!item || !!failed;
  useEffect(() => {
    if (ready) document.querySelector<HTMLElement>("h1")?.focus();
  }, [ready]);
  useEffect(() => {
    // A duplicate reads the list too, for a name nothing has (FU-P3-111); without it, `<name>-copy`.
    if (!wanted) return;
    const names = name ? Promise.resolve([]) : kind.list().then((l) => l.items.map((i) => i.name), () => []);
    Promise.all([kind.get(wanted), names]).then(([found, all]) => (setTaken(all), setItem(found)), (e: Error) =>
      setFailed(e instanceof ApiError && e.status === 404 ? { missing: true, text: `No ${kind.noun} named ${wanted}` } : { missing: false, text: e.message }),
    );
  }, [kind, name, wanted, round]);
  const reload = () => setRound((r) => r + 1);
  const toList = (say: string, focus: string | null, opener?: string) => ((next = { focus, say, opener }), navigate({ to: kind.path, search: shownView }));
  const opener = name ? `Edit ${name}` : from ? `${duplicateWords({ builtin: !!item?.builtin })} ${from}` : kind.newLabel;
  if (failed?.missing) {
    return (
      <div className="sp-page">
        <h1 className="sp-page-title" tabIndex={-1}>{failed.text}</h1>
        <p>It may have been deleted in another tab. <Link to={kind.path}>All {kind.nounPlural}</Link></p>
      </div>
    );
  }
  if (failed) {
    return (
      <div className="sp-page">
        <PageHead section="environments" title={name ?? kind.newLabel} />
        <ErrorPanel onRetry={() => (setFailed(null), reload())}>{wanted} could not be read. {failed.text}</ErrorPanel>
      </div>
    );
  }
  if (wanted && !item) return <SkeletonRows label={`Loading ${kind.nounPlural}…`} />;
  const builtin = !!(name && item?.builtin);
  // A duplicate gets a new name, `<name>-copy` (FU-P3-111); a built-in's label ("SLURM (from spectio init)") is not copied.
  const duplicate = item && !name ? { name: copyName(item.name, taken), clearLabel: item.builtin } : null;
  const duplicateLink = name && `${kind.path}/new?from=${encodeURIComponent(name)}`;
  // Duplicate here does not wait while the file is not usable (§4.8.1, inbox #141): this page does
  // not read the file's state; the create form's Save then gets 409 `...-file-unusable`.
  const more = phone && name && item && (
    <div role="group" aria-labelledby="env-more" className="sp-env-more">
      <h2 id="env-more">More for this {kind.noun}</h2>
      <Button component={Link} to={duplicateLink as string} variant="default" fullWidth>{duplicateWords(item)} {name}</Button>
      {!item.builtin && <Button variant="default" fullWidth onClick={() => setAsking(true)}>Delete {name}</Button>}
      <DeleteAsk item={asking ? item : null} kind={kind as unknown as Kind<Item, unknown>} onClose={() => setAsking(false)} onDeleted={() => toList(`Deleted ${name}`, null)} onReload={reload} />
    </div>
  );
  return (
    <div className="sp-page">
      <PageHead
        section="environments"
        title={name ? label(item!) : kind.newLabel}
        sub={kind.sub}
        secondary={builtin && !phone ? [<Button component={Link} to={duplicateLink as string} variant="default" aria-label={`Duplicate to edit ${name}`}>Duplicate to edit</Button>] : undefined}
      />
      <Fragment key={`${round}:${item?.etag ?? ""}`}>
      {kind.form({
        item,
        duplicate,
        etag: name ? (item?.etag ?? null) : null,
        readOnly: builtin,
        onSaved: (saved) => toList(`Saved ${saved.name}`, saved.name),
        onCancel: () => toList("", wanted, opener),
        onReload: reload,
      })}
      </Fragment>
      {more}
    </div>
  );
}
