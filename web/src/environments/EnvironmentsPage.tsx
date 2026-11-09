import "../runs/runs.css";
import "./environments.css";
import { Button, Modal } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { ApiError, type EnvironmentItem, type EnvironmentList, deleteEnvironment, getEnvironment, listEnvironments, makeDefault } from "../api";
import { useServer } from "../server";
import { usePageCrumb } from "../shell/crumb";
import { PageHead } from "../shell/PageHead";
import { EnvironmentForm } from "./EnvironmentForm";
import { EMPTY, fromItem, label, summary } from "./fields";

// The Environments pages (FU-P3-86f; ui-spec §4.8.1; boards LiteEnvironments, LiteEnvironmentEdit,
// LiteEnvironmentsStates): the list with Delete and Make default, and the form's page.

/** What the list says and focuses when it opens next: after Save, "Saved <name>". */
let next: { focus: string; say: string } | null = null;

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
const focusHeading = (name: string | null) =>
  requestAnimationFrame(() => (document.getElementById(name ? headingId(name) : "") ?? document.querySelector("h1"))?.focus());

/** A link or, while the file is not usable, a button described by why it waits (§4.6 pattern). */
function Waiting({ why, to, children, primary, ...rest }: { why: string | null; to: string; children: string; primary?: boolean; "aria-label"?: string }) {
  const look = { variant: primary ? "filled" : "default", size: primary ? "md" : "sm" };
  if (!why) return <Button component={Link} to={to} {...look} {...rest}>{children}</Button>;
  return <Button {...look} aria-disabled data-disabled aria-describedby="env-waits" {...rest}>{children}</Button>;
}
const waits = (why: string | null) => (why ? { "aria-disabled": true, "data-disabled": true, "aria-describedby": "env-waits" } : {});

export function EnvironmentsPage() {
  const server = useServer();
  const [data, setData] = useState<EnvironmentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [said, setSaid] = useState("");
  const [cardError, setCardError] = useState<{ name: string; text: string } | null>(null);
  const [asking, setAsking] = useState<EnvironmentItem | null>(null);
  const [askError, setAskError] = useState<string | null>(null);
  const load = useCallback(() => listEnvironments().then(setData, (e: Error) => setError(e.message)), []);
  useEffect(() => {
    load().then(() => {
      if (next) (setSaid(next.say), focusHeading(next.focus));
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
  const remove = (env: EnvironmentItem) => {
    const i = items.findIndex((e) => e.name === env.name);
    const after = items[i + 1] ?? items[i - 1];
    deleteEnvironment(env.name, env.etag)
      .then(() => (setAsking(null), done(`Deleted ${env.name}`, after?.name ?? null)))
      .catch((e: Error) => setAskError(problem(e)));
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
        {items.map((env) => (
          <article key={env.name} className="sp-card sp-env" data-default={env.default || undefined}>
            <div className="sp-env-top">
              <h2 id={headingId(env.name)} tabIndex={-1}>{label(env)}</h2>
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
            <div className="sp-actions">
              {!env.builtin && <Waiting why={why} to={`/environments/${env.name}`} aria-label={`Edit ${env.name}`}>Edit</Waiting>}
              <Waiting why={why} to={`/environments/new?from=${env.name}`} aria-label={`Duplicate ${env.name}`}>Duplicate</Waiting>
              {!env.default && env.usable && (
                <Button variant="default" size="sm" aria-label={`Make default ${env.name}`} onClick={() => !why && promote(env)} {...waits(why)}>
                  Make default
                </Button>
              )}
              {!env.builtin && (
                <Button variant="light" color="red" size="sm" aria-label={`Delete ${env.name}`} onClick={() => !why && (setAskError(null), setAsking(env))} {...waits(why)}>
                  Delete
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>
      {data && own === 0 && <p className="sp-muted">Only the built-in environments so far. New environment saves your partition, account and limits under a name.</p>}
      {data && <p className="sp-env-hint">Saved in <span className="sp-mono">{data.file.path}</span></p>}
      <Modal opened={!!asking} onClose={() => setAsking(null)} title={asking && `Delete ${asking.name}?`} returnFocus centered>
        {asking && (
          <>
            <p>Runs that used it keep their settings.{asking.default && ` It is the default: ${server?.executor ?? "slurm"} becomes the default again.`}</p>
            {askError && <p role="alert" className="sp-note sp-alert">{askError}</p>}
            <div className="sp-actions">
              <Button variant="default" data-autofocus onClick={() => setAsking(null)}>Cancel</Button>
              {askError ? (
                <Button variant="default" onClick={() => (setAsking(null), load())}>Reload</Button>
              ) : (
                <Button color="red" onClick={() => remove(asking)}>Delete {asking.name}</Button>
              )}
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}

/** `/environments/new` (`?from=<name>` to duplicate) and `/environments/<name>`. */
export function EnvironmentPage({ name, from }: { name: string | null; from?: string }) {
  const navigate = useNavigate();
  const [item, setItem] = useState<EnvironmentItem | null>(null);
  const [missing, setMissing] = useState<string | null>(null);
  const [round, setRound] = useState(0);
  const wanted = name ?? from ?? null;
  usePageCrumb(name ?? "New environment");
  useEffect(() => {
    if (wanted) getEnvironment(wanted).then(setItem, (e: Error) => setMissing(e instanceof ApiError && e.status === 404 ? `No environment named ${wanted}` : e.message));
  }, [wanted, round]);
  if (missing) {
    return (
      <div className="sp-page">
        <h1 className="sp-page-title">{missing}</h1>
        <p>It may have been deleted in another tab. <Link to="/environments">All environments</Link></p>
      </div>
    );
  }
  if (wanted && !item) return <p className="sp-muted">Loading environments…</p>;
  const builtin = !!(name && item?.builtin);
  const initial = item ? { ...fromItem(item), ...(name ? {} : { name: "" }) } : EMPTY;
  return (
    <div className="sp-page">
      <PageHead section="environments" title={name ? label(item!) : "New environment"} sub="The executor and its defaults, saved under a name you choose at Launch" />
      {builtin && <Button component={Link} to={`/environments/new?from=${name}`} variant="default" aria-label={`Duplicate ${name}`}>Duplicate</Button>}
      <EnvironmentForm
        key={`${round}:${item?.etag ?? ""}`}
        initial={initial}
        etag={name ? (item?.etag ?? null) : null}
        readOnly={builtin}
        onSaved={(saved) => ((next = { focus: saved.name, say: `Saved ${saved.name}` }), navigate({ to: "/environments" }))}
        onCancel={() => navigate({ to: "/environments" })}
        onReload={() => setRound((r) => r + 1)}
      />
    </div>
  );
}
