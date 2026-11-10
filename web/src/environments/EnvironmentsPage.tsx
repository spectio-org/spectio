import "../runs/runs.css";
import "./environments.css";
import { Button, Drawer, Modal, Skeleton } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type EnvironmentItem, type EnvironmentList, deleteEnvironment, getEnvironment, listEnvironments, makeDefault } from "../api";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { usePhone } from "../shell/layout";
import { PageHead } from "../shell/PageHead";
import { EnvironmentForm } from "./EnvironmentForm";
import { EMPTY, fromItem, label, summary } from "./fields";

// The Environments pages (FU-P3-86f; ui-spec §4.8.1; boards LiteEnvironments, LiteEnvironmentEdit,
// LiteEnvironmentsStates): the list with Delete and Make default, and the form's page.

/** What the list says and focuses when it opens next: after Save, "Saved <name>"; after Cancel,
 * the opener (its label: "Edit <name>", "New environment"), else the card's heading. */
let next: { focus: string | null; say: string; opener?: string } | null = null;

const FILE_LINES: Record<string, (path: string, detail: string) => string> = {
  refused: (p, d) => `Spectio does not read ${p}: ${d}. Fix it with the command shown; Spectio will not change it.`,
  invalid: (p, d) => `${p} has a mistake: ${d}. Only the built-in environments are listed until it is fixed.`,
  unreachable: () => "Spectio cannot read the cluster's files right now. Only the built-in environments are listed.",
};
const WAITS: Record<string, string> = {
  refused: "Waits until the environments file can be read",
  invalid: "Waits until the mistake in the file is fixed",
  unreachable: "Waits until the cluster's files can be read",
};
const PROBLEMS: Record<string, string> = {
  "412": "This environment changed in another tab.",
  "environments-file-changed": "The file changed on disk since this page read it.",
};
const problem = (e: Error) => (e instanceof ApiError ? (PROBLEMS[String(e.status)] ?? PROBLEMS[e.slug ?? ""]) : undefined) ?? e.message;
const headingId = (name: string) => `env-${name}`;
const byLabel = (label: string) =>
  [...document.querySelectorAll<HTMLElement>("a, button")].find((el) => (el.getAttribute("aria-label") ?? el.textContent) === label);
const focusHeading = (name: string | null, opener?: string) =>
  requestAnimationFrame(() => ((opener && byLabel(opener)) || document.getElementById(name ? headingId(name) : "") || document.querySelector("h1"))?.focus());

/** A link or, while the file is not usable, a button described by why it waits (§4.6 pattern). */
function Waiting({ why, to, children, primary, ...rest }: { why: string | null; to: string; children: string; primary?: boolean; "aria-label"?: string }) {
  const look = { variant: primary ? "filled" : "default", size: primary ? "md" : "sm" };
  if (!why) return <Button component={Link} to={to} {...look} {...rest}>{children}</Button>;
  return <Button {...look} aria-disabled data-disabled aria-describedby="env-waits" {...rest}>{children}</Button>;
}
const waits = (why: string | null) => (why ? { "aria-disabled": true, "data-disabled": true, "aria-describedby": "env-waits" } : {});

/** Delete asks first: a dialog, a bottom sheet on the phone; a 412 or a file change in place, with Reload. */
function DeleteAsk({ env, onClose, onDeleted, onReload }: { env: EnvironmentItem | null; onClose: () => void; onDeleted: () => void; onReload: () => void }) {
  const server = useServer();
  const phone = usePhone();
  const [error, setError] = useState<string | null>(null);
  const close = () => (setError(null), onClose());
  const body = env && (
    <>
      <p>Runs that used it keep their settings.{env.default && ` It is the default: ${server?.executor ?? "slurm"} becomes the default again.`}</p>
      {error && <p role="alert" className="sp-note sp-alert">{error}</p>}
      <div className="sp-actions">
        <Button variant="default" data-autofocus onClick={close}>Cancel</Button>
        {error ? (
          <Button variant="default" onClick={() => (close(), onReload())}>Reload</Button>
        ) : (
          <Button color="red" onClick={() => deleteEnvironment(env.name, env.etag).then(onDeleted, (e: Error) => setError(problem(e)))}>
            Delete {env.name}
          </Button>
        )}
      </div>
    </>
  );
  const props = { opened: !!env, onClose: close, title: env && `Delete ${env.name}?`, returnFocus: true };
  return phone ? (
    <Drawer {...props} position="bottom" classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}>{body}</Drawer>
  ) : (
    <Modal {...props} centered>{body}</Modal>
  );
}

export function EnvironmentsPage() {
  const server = useServer();
  const phone = usePhone();
  const [data, setData] = useState<EnvironmentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const [cardError, setCardError] = useState<{ name: string; text: string } | null>(null);
  const [asking, setAsking] = useState<EnvironmentItem | null>(null);
  const load = useCallback(() => listEnvironments().then(setData, (e: Error) => setError(e.message)), []);
  useEffect(() => {
    load().then(() => {
      if (next) (setSaid(next.say), focusHeading(next.focus, next.opener));
      next = null;
    });
  }, [load]);

  if (error) {
    return (
      <div className="sp-page">
        <PageHead section="environments" title="Environments" />
        <p role="alert" className="sp-note sp-alert">Environments could not be read. {error}</p>
        <Button variant="default" onClick={() => (setError(null), load())}>Retry</Button>
      </div>
    );
  }
  const items = data?.items ?? [];
  const state = data?.file.state ?? "ok";
  const why = WAITS[state] ?? null;
  const done = (say: string, focus: string | null) => load().then(() => (setSaid(say), focusHeading(focus)));
  const removed = (env: EnvironmentItem) => {
    const i = items.findIndex((e) => e.name === env.name);
    const after = items[i + 1] ?? items[i - 1];
    setAsking(null);
    done(`Deleted ${env.name}`, after?.name ?? null);
  };
  const promote = (env: EnvironmentItem) =>
    makeDefault(env.name)
      .then(() => (setCardError(null), done(`${env.name} is now the default`, env.name)))
      .catch((e: Error) => setCardError({ name: env.name, text: problem(e) }));
  const own = items.filter((e) => !e.builtin).length;
  return (
    <div className="sp-page">
      <PageHead
        section="environments"
        title="Environments"
        sub={data && `Where the tasks of a run go: the executor and its defaults · ${items.length} environments · the default is ${data.default}`}
        action={<Waiting why={why} to="/environments/new" primary>New environment</Waiting>}
      />
      <p role="status" className="sp-sr">{said}</p>
      {data === null && <p className="sp-muted">Loading environments…</p>}
      {data && FILE_LINES[state] && (
        <div className="sp-note" role={state === "unreachable" ? undefined : "note"}>
          {FILE_LINES[state](data.file.path, data.file.detail ?? "")}{" "}
          {state === "unreachable" && <Button variant="default" size="xs" onClick={load}>Retry</Button>}
        </div>
      )}
      {why && <p id="env-waits" className="sp-env-hint">New environment, Edit, Duplicate, Make default and Delete: {why.toLowerCase()}</p>}
      <div className="sp-envs">
        {data === null &&
          [0, 1].map((i) => (
            <article key={i} className="sp-card sp-env" aria-hidden>
              <Skeleton height={18} width="45%" />
              <Skeleton height={12} mt={12} />
              <Skeleton height={12} mt={8} width="70%" />
            </article>
          ))}
        {items.map((env) => (
          <article key={env.name} className="sp-card sp-env" data-default={env.default || undefined}>
            <div className="sp-env-top">
              <h2 id={headingId(env.name)} tabIndex={-1}>
                {/* The phone (UX-PRE-FU86-R1-22): the whole card is this link; its actions are on the page. */}
                {phone ? <Link to="/environments/$name" params={{ name: env.name }} className="sp-env-link">{label(env)}</Link> : label(env)}
              </h2>
              <span className="sp-chip">{env.executor === "slurm" ? "SLURM" : "Local"}</span>
              {env.default && <span className="sp-chip" data-tone="succeeded">Default</span>}
              {env.builtin && <span className="sp-chip">Built-in</span>}
            </div>
            {env.label && <span className="sp-mono">{env.name}</span>}
            <p>{summary(env, server?.node ?? "the server", server?.executor ?? "slurm")}</p>
            {(env.profiles.nextflow || env.profiles.snakemake) && (
              <p className="sp-env-hint">
                Profiles: {[env.profiles.nextflow && `Nextflow ${env.profiles.nextflow}`, env.profiles.snakemake && `Snakemake ${env.profiles.snakemake}`].filter(Boolean).join(" · ")}
              </p>
            )}
            {!env.usable && <p className="sp-note">Not usable: {env.unusable_reason}</p>}
            {cardError?.name === env.name && (
              <div role="alert" className="sp-note sp-alert">
                {cardError.text} <Button variant="default" size="xs" onClick={() => (setCardError(null), load())}>Reload</Button>
              </div>
            )}
            {!phone && <div className="sp-actions">
              {!env.builtin && <Waiting why={why} to={`/environments/${env.name}`} aria-label={`Edit ${env.name}`}>Edit</Waiting>}
              <Waiting why={why} to={`/environments/new?from=${env.name}`} aria-label={`Duplicate ${env.name}`}>Duplicate</Waiting>
              {!env.default && env.usable && (
                <Button variant="default" size="sm" aria-label={`Make default ${env.name}`} onClick={() => !why && promote(env)} {...waits(why)}>
                  Make default
                </Button>
              )}
              {!env.builtin && (
                <Button variant="light" color="red" size="sm" aria-label={`Delete ${env.name}`} onClick={() => !why && setAsking(env)} {...waits(why)}>
                  Delete
                </Button>
              )}
            </div>}
          </article>
        ))}
      </div>
      {data && own === 0 && (state === "ok" || state === "missing") && <p className="sp-muted">Only the built-in environments so far. New environment saves your partition, account and limits under a name.</p>}
      {data && <p className="sp-env-hint">Saved in <span className="sp-mono">{data.file.path}</span></p>}
      <DeleteAsk env={asking} onClose={() => setAsking(null)} onDeleted={() => asking && removed(asking)} onReload={load} />
    </div>
  );
}

/** `/environments/new` (`?from=<name>` to duplicate) and `/environments/<name>`. */
export function EnvironmentPage({ name, from }: { name: string | null; from?: string }) {
  const navigate = useNavigate();
  const phone = usePhone();
  const [item, setItem] = useState<EnvironmentItem | null>(null);
  const [failed, setFailed] = useState<{ missing: boolean; text: string } | null>(null);
  const [round, setRound] = useState(0);
  const [asking, setAsking] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);
  const wanted = name ?? from ?? null;
  usePageCrumb(name ?? "New environment");
  // New, Edit and Duplicate open with focus on the page's heading (§4.8.1, inbox #146 item 10)
  const ready = !wanted || !!item || !!failed;
  useEffect(() => {
    if (ready) document.querySelector<HTMLElement>("h1")?.focus();
  }, [ready]);
  useEffect(() => {
    if (wanted)
      getEnvironment(wanted).then(setItem, (e: Error) =>
        setFailed(e instanceof ApiError && e.status === 404 ? { missing: true, text: `No environment named ${wanted}` } : { missing: false, text: e.message }),
      );
  }, [wanted, round]);
  const reload = () => setRound((r) => r + 1);
  const toList = (say: string, focus: string | null, opener?: string) => ((next = { focus, say, opener }), navigate({ to: "/environments" }));
  const opener = name ? `Edit ${name}` : from ? `Duplicate ${from}` : "New environment";
  if (failed?.missing) {
    return (
      <div className="sp-page">
        <h1 className="sp-page-title" tabIndex={-1}>{failed.text}</h1>
        <p>It may have been deleted in another tab. <Link to="/environments">All environments</Link></p>
      </div>
    );
  }
  if (failed) {
    return (
      <div className="sp-page">
        <PageHead section="environments" title={name ?? "New environment"} />
        <p role="alert" className="sp-note sp-alert">{wanted} could not be read. {failed.text}</p>
        <Button variant="default" onClick={() => (setFailed(null), reload())}>Retry</Button>
      </div>
    );
  }
  if (wanted && !item) return <p className="sp-muted">Loading environments…</p>;
  const builtin = !!(name && item?.builtin);
  // A duplicate gets a new name; a built-in's label ("SLURM (from spectio init)") is not copied either.
  const initial = item ? { ...fromItem(item), ...(name ? {} : { name: "", ...(item.builtin ? { label: "" } : {}) }) } : EMPTY;
  // Duplicate here does not wait while the file is not usable (§4.8.1, inbox #141): this page does
  // not read the file's state; the create form's Save then gets 409 environments-file-unusable.
  const more = phone && name && item && (
    <div role="group" aria-labelledby="env-more" className="sp-env-more">
      <h2 id="env-more">More for this environment</h2>
      {!item.default && item.usable && (
        <Button
          variant="default"
          fullWidth
          onClick={() => makeDefault(name).then(() => toList(`${name} is now the default`, name), (e: Error) => setMoreError(problem(e)))}
        >
          Make default {name}
        </Button>
      )}
      <Button component={Link} to={`/environments/new?from=${name}`} variant="default" fullWidth>Duplicate {name}</Button>
      {!item.builtin && <Button variant="light" color="red" fullWidth onClick={() => setAsking(true)}>Delete {name}</Button>}
      {moreError && <p role="alert" className="sp-note sp-alert">{moreError}</p>}
      <DeleteAsk env={asking ? item : null} onClose={() => setAsking(false)} onDeleted={() => toList(`Deleted ${name}`, null)} onReload={reload} />
    </div>
  );
  return (
    <div className="sp-page">
      <PageHead section="environments" title={name ? label(item!) : "New environment"} sub="The executor and its defaults, saved under a name you choose at Launch" />
      {builtin && !phone && <Button component={Link} to={`/environments/new?from=${name}`} variant="default" aria-label={`Duplicate ${name}`}>Duplicate</Button>}
      <EnvironmentForm
        key={`${round}:${item?.etag ?? ""}`}
        initial={initial}
        etag={name ? (item?.etag ?? null) : null}
        readOnly={builtin}
        onSaved={(saved) => toList(`Saved ${saved.name}`, saved.name)}
        onCancel={() => toList("", wanted, opener)}
        onReload={reload}
      />
      {more}
    </div>
  );
}
