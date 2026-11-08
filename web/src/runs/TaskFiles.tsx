import { Button } from "@mantine/core";
import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import {
  ApiError,
  type TaskFile,
  type TaskFiles as Listing,
  type TaskOutput,
  type RunDetail,
  type Task,
  getTaskFile,
  listTaskFiles,
  taskFileUrl,
} from "../api";
import { ICONS, Icon } from "../icons";
import { usePhone } from "../shell/layout";
import { CopyButton } from "./CopyMenu";
import { LogLines } from "./LogViewer";
import { duration, when } from "./stateWord";

// Each job's files (P1 Task 32; ui-spec §4.4 note 2026-10-28, Job files; boards LiteTaskFiles,
// MLiteTaskFilesSheet, LiteTaskFilesStates), shown in the task view of the detail sheet (DetailSheet:
// the drawer, aria-modal, focus back to its opener). P1 Task 28's routes: the listing names every
// file the attempt has or may have, with its state; a read is the file's last 64 KiB as text. One
// tab per file (<button role="tab">, arrow keys move), a native <select> labelled File on the
// phone; a file that is not there says why, in its label and in words in the panel.

const TAIL = 65536; // what a read returns (api/taskfiles.py TAIL)
const DOWNLOAD = 1048576; // the most a read returns (MAX_READ)
// Nextflow's order, then Snakemake's: the SLURM job log, then the rule's logs.
const ORDER: TaskFile["kind"][] = ["job_log", "stderr", "stdout", "script", "wrapper", "exit", "marker", "trace", "slurm_log", "rule_log"];
const MORE = new Set<TaskFile["kind"]>(["marker", "trace"]); // under "More files"
const FAILED_FIRST: TaskFile["kind"][] = ["job_log", "slurm_log", "stderr"]; // a failed attempt opens on its job log
const STATE_WORDS: Record<Exclude<TaskFile["state"], "present">, string> = {
  not_yet: "not yet",
  absent: "missing",
  deleted_after_success: "deleted",
  cleaned: "gone",
};
const WHY: Record<Exclude<TaskFile["state"], "present">, [string, string]> = {
  not_yet: ["The job has not written this file yet", "The engine writes it while the job runs or when it ends. Reload once the job runs."],
  absent: ["The job ended without writing this file", "Not every job writes every file."],
  deleted_after_success: [
    "Deleted by the Snakemake SLURM plugin after the job succeeded",
    "The plugin removes the SLURM logs of successful jobs unless its keep_successful_logs setting is on. The rule's own log file is still there.",
  ],
  cleaned: [
    "The work directory was removed",
    "Its files are gone, for example after nextflow clean or a scratch purge. The run's results and logs are not affected.",
  ],
};
const OFFLINE = "Spectio cannot read the cluster's files right now";
const CLEANUP: [string, string] = [
  "This job's work directory was removed by cleanup = true",
  "Nextflow removes the work directories after a successful run when cleanup = true. The run's results are not affected.",
];

// Snakemake's outputs of the job (ui-spec §5.2): a tab after the files; its key, empty, is no
// file's name.
const OUTPUTS = "";
const OUTPUT_WORDS: Record<TaskOutput["state"], string> = {
  present: "present",
  not_yet: "not yet",
  absent: "absent",
  temp_removed: "deleted by Snakemake (temporary)",
  tbd: "decided after the checkpoint",
};

function OutputsPanel({ outputs }: { outputs: TaskOutput[] }) {
  if (!outputs.length) return <p className="sp-muted">This job declares no output.</p>;
  return (
    <>
      <ul className="sp-sheet-list sp-outputs" aria-label="Outputs">
        {outputs.map((o) => (
          <li key={o.path} className="sp-sheet-row">
            {[o.path, OUTPUT_WORDS[o.state], o.state === "temp_removed" && o.removed_at ? when(o.removed_at) : null, o.protected ? "write-protected" : null]
              .filter(Boolean)
              .join(" · ")}
          </li>
        ))}
      </ul>
      <p className="sp-muted">Snakemake says an output is temporary only when it deletes it; Spectio does not guess.</p>
    </>
  );
}

/** "2.4 KiB", "3.1 MiB", "120 B". */
function fileSize(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < DOWNLOAD) return `${(n / 1024).toFixed(1)} KiB`;
  return `${(n / DOWNLOAD).toFixed(1)} MiB`;
}

const label = (f: TaskFile) => {
  const name = f.kind === "slurm_log" ? "SLURM log" : f.name;
  return f.state === "present" ? name : `${name} · ${STATE_WORDS[f.state]}`;
};

/** The file to open first: a failed attempt's job log, else the first file present. */
function first(files: TaskFile[], failed: boolean): TaskFile | undefined {
  const present = files.filter((f) => f.state === "present");
  const log = failed ? FAILED_FIRST.map((k) => present.find((f) => f.kind === k)).find(Boolean) : undefined;
  return log ?? present[0] ?? files[0];
}

/** A refusal in words, with Retry when trying again may help. */
function Refused({ title, body, onRetry, download }: { title: string; body?: string | null; onRetry?: () => void; download?: string }) {
  return (
    <div className="sp-note sp-file-why">
      <strong>{title}</strong>
      {body && <span>{body}</span>}
      {onRetry && (
        <div>
          <Button variant="default" size="xs" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
      {download && (
        <div>
          <Button component="a" variant="default" size="xs" href={download} download>
            Download
          </Button>
        </div>
      )}
    </div>
  );
}

function FilePanel({ task, n, file, running, cleanup, onReload }: { task: Task; n: number; file: TaskFile; running: boolean; cleanup: boolean; onReload: () => void }) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [reads, setReads] = useState(0);
  const { state } = file;
  const present = state === "present";
  useEffect(() => {
    if (!present) return;
    const controller = new AbortController();
    setText(null);
    setError(null);
    getTaskFile(task.id, n, file.name, controller.signal)
      .then(setText)
      .catch((e: ApiError) => controller.signal.aborted || setError(e));
    return () => controller.abort();
  }, [task.id, n, file.name, present, reads]);

  if (state !== "present") {
    const [title, body] = state === "cleaned" && cleanup ? CLEANUP : WHY[state];
    return (
      <>
        <Refused title={title} body={body} />
        {file.note && <p className="sp-muted">{file.note}</p>}
        {state === "not_yet" && (
          <div>
            <Button variant="default" size="xs" onClick={onReload}>
              Reload
            </Button>
          </div>
        )}
      </>
    );
  }
  const download = taskFileUrl(task.id, n, file.name, { tail: DOWNLOAD, download: true });
  if (error?.status === 415) return <Refused title="This file is not text. Download it to open it" body="Spectio shows text files only." download={download} />;
  if (error?.status === 410) {
    const [title, body] = cleanup ? CLEANUP : WHY.cleaned;
    return <Refused title={title} body={body} />;
  }
  if (error?.status === 503) return <Refused title={OFFLINE} body="The file system does not answer. Nothing was lost; try again in a moment." onRetry={() => setReads((r) => r + 1)} />;
  if (error?.status === 404) return <Refused title="This file is not there now" body="It was listed, then not found: reload the list." onRetry={() => (onReload(), setReads((r) => r + 1))} />;
  if (error) return <Refused title="The file could not be read" body={error.message} onRetry={() => setReads((r) => r + 1)} />;
  const size = file.size ?? 0;
  const big = size > DOWNLOAD;
  const age = file.mtime ? (running ? `updated ${duration(file.mtime, null)} ago` : `written ${when(file.mtime)}`) : null;
  return (
    <>
      <div className="sp-file-line">
        <span className="sp-muted sp-grow">
          {[size > TAIL ? `last 64 KiB of ${fileSize(size)}` : `whole file · ${fileSize(size)}`, age].filter(Boolean).join(" · ")}
        </span>
        <span className="sp-actions">
          <Button variant="default" size="xs" leftSection={<Icon path={ICONS.reload} size={14} />} onClick={() => setReads((r) => r + 1)}>
            Reload
          </Button>
          <Button
            component="a"
            variant="default"
            size="xs"
            href={download}
            download
            aria-label={big ? `Download last 1 MiB of ${file.name}` : `Download ${file.name}`}
            leftSection={<Icon path={ICONS.download} size={14} />}
          >
            {big ? "Download last 1 MiB" : "Download"}
          </Button>
        </span>
      </div>
      {file.note && <p className="sp-muted">{file.note}</p>}
      <pre className="sp-log sp-nowrap sp-file-text" tabIndex={0} aria-label={`${file.name}, ${size > TAIL ? "last lines" : "whole file"}`}>
        {text === null ? "Loading…" : text === "" ? "Empty." : <LogLines text={text} />}
      </pre>
    </>
  );
}

/** The files of the task's last attempt, or of an earlier one picked in Attempt. */
export function TaskFiles({ run, task }: { run: RunDetail; task: Task }) {
  const phone = usePhone();
  const base = useId();
  const snakemake = run.workflow.engine === "snakemake";
  const last = task.attempt_n;
  const [n, setN] = useState(last ?? 1);
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [lists, setLists] = useState(0);
  const [picked, setPicked] = useState<string | null>(null);
  const [more, setMore] = useState(false);
  const tabs = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (last === null) return;
    const controller = new AbortController();
    setError(null);
    listTaskFiles(task.id, n, controller.signal)
      .then((found) => {
        setListing(found);
        setPicked((name) => ((name === OUTPUTS && found.outputs) || found.files.some((f) => f.name === name) ? name : null));
      })
      .catch((e: ApiError) => controller.signal.aborted || setError(e));
    return () => controller.abort();
  }, [task.id, n, last, lists]);

  if (last === null) return <p className="sp-muted">No attempt has started yet: no file to show.</p>;
  const reload = () => setLists((l) => l + 1);
  const failed = task.state === "failed" || n < last;
  const files = [...(listing?.attempt === n ? listing.files : [])].sort((a, b) => ORDER.indexOf(a.kind) - ORDER.indexOf(b.kind));
  const outputs = listing?.attempt === n ? (listing.outputs ?? null) : null;
  // with no file to show (a Snakemake job without a log: directive) the drawer opens on Outputs
  const onOutputs = outputs !== null && (picked === OUTPUTS || files.length === 0);
  const shown = onOutputs ? undefined : (files.find((f) => f.name === picked) ?? first(files, failed));
  const visible = files.filter((f) => more || !MORE.has(f.kind) || f === shown);
  const hasMore = files.some((f) => MORE.has(f.kind));
  const directory = listing?.work_dir ?? null;
  // the tabs: the files shown, then Outputs on a Snakemake attempt
  const outputsLabel = outputs ? `Outputs (${outputs.length})` : "";
  const tabList = [...visible.map((f) => ({ key: f.name, label: label(f), state: f.state as string })), ...(outputs ? [{ key: OUTPUTS, label: outputsLabel, state: "present" }] : [])];
  const current = onOutputs ? OUTPUTS : shown?.name;
  const index = tabList.findIndex((t) => t.key === current);
  const tabId = (i: number) => `${base}-tab-${i}`;
  const onKey = (event: KeyboardEvent) => {
    const to = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: tabList.length - 1 }[event.key];
    if (to === undefined) return;
    event.preventDefault();
    const at = (to + tabList.length) % tabList.length;
    setPicked(tabList[at].key);
    tabs.current?.querySelectorAll<HTMLButtonElement>("[role=tab]")[at]?.focus();
  };

  return (
    <div className="sp-files">
      {last > 1 && (
        <label className="sp-select">
          Attempt{" "}
          <select value={n} onChange={(e) => setN(Number(e.currentTarget.value))}>
            {Array.from({ length: last }, (_, i) => last - i).map((a) => (
              <option key={a} value={a}>
                {a === last ? `${a} (last)` : a}
              </option>
            ))}
          </select>
        </label>
      )}
      {directory && (
        <div className="sp-log-file">
          <span className="sp-muted">{snakemake ? "Launch directory" : "Work directory"}</span>
          <code>{directory}</code>
          <CopyButton text={directory} label="Copy" name={`Copy the ${snakemake ? "launch" : "work"} directory`} />
        </div>
      )}
      {error && error.status === 503 && <Refused title={OFFLINE} body="The file system does not answer. Nothing was lost; try again in a moment." onRetry={reload} />}
      {error && error.status !== 503 && <Refused title="The files could not be listed" body={error.message} onRetry={reload} />}
      {!error && listing?.attempt !== n && <p className="sp-muted">Loading the files…</p>}
      {!error && listing?.attempt === n && files.length === 0 && outputs === null && <p className="sp-muted">This attempt has no file to show.</p>}
      {!error && current !== undefined && (
        <>
          {phone ? (
            <label className="sp-select sp-file-select">
              File{" "}
              <select value={current} onChange={(e) => setPicked(e.currentTarget.value)}>
                {files.map((f) => (
                  <option key={f.name} value={f.name}>
                    {label(f)}
                  </option>
                ))}
                {outputs && <option value={OUTPUTS}>{outputsLabel}</option>}
              </select>
            </label>
          ) : (
            <div className="sp-file-tabs">
              <div ref={tabs} role="tablist" aria-label="Files" onKeyDown={onKey}>
                {tabList.map((t, i) => (
                  <button
                    key={t.key}
                    id={tabId(i)}
                    type="button"
                    role="tab"
                    aria-selected={t.key === current}
                    aria-controls={`${base}-panel`}
                    tabIndex={t.key === current ? 0 : -1}
                    data-state={t.state}
                    onClick={() => setPicked(t.key)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              {hasMore && !more && (
                <button type="button" className="sp-link-button" aria-expanded={false} onClick={() => setMore(true)}>
                  More files
                </button>
              )}
            </div>
          )}
          <div
            id={`${base}-panel`}
            role="tabpanel"
            aria-labelledby={phone ? undefined : tabId(index)}
            aria-label={phone ? (shown ? label(shown) : outputsLabel) : undefined}
            className="sp-file-panel"
          >
            {shown ? (
              <FilePanel
                key={`${n}:${shown.name}`}
                task={task}
                n={n}
                file={shown}
                running={task.state === "running" && n === last}
                cleanup={run.engine_settings?.cleanup === true}
                onReload={reload}
              />
            ) : (
              <OutputsPanel outputs={outputs ?? []} />
            )}
          </div>
        </>
      )}
      {snakemake && <p className="sp-muted">Snakemake keeps no job script; the rule's command is in the Snakefile.</p>}
    </div>
  );
}
