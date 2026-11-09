import { Button, Drawer, Modal } from "@mantine/core";
import { Link, useNavigate } from "@tanstack/react-router";
import { type ReactNode, useState } from "react";
import { ApiError, type RunDetail, type ServerVersion, resumeRun } from "../api";
import { runEnvName } from "../environments/fields";
import { ICONS, Icon } from "../icons";
import { usePhone } from "../shell/layout";
import { engineName, isTerminal, runWord, words } from "./stateWord";

// Resume (P1 Task 32 part two; ui-spec §4.4 run tools note; boards LiteRunActions A and C-F,
// MLiteResumeSheet): a failed or cancelled run's primary action. It asks first, in a dialog on the
// desktop and a bottom sheet on the phone (aria-modal, Cancel focused first, focus back on Resume),
// then posts `:relaunch` with `mode: resume` and opens the new run. When `actions.resume` says no,
// Resume stays visible, aria-disabled, its reason as text it is described by.

/** The words for why Resume is refused: `actions.resume.reason`, and the `reason` of a `409` of
 * `:relaunch` (api §5.1), which may also be `profiles_unknown`. */
export function refusedWords(reason: string, run: RunDetail, server: ServerVersion | null): ReactNode {
  switch (reason) {
    case "running":
      return "The run's head is still running. Resume when it has ended.";
    case "head_unverified":
      return `The head may still be running on ${run.head?.node ?? "its node"}, and Spectio cannot check it from ${server?.node ?? "this node"}. Resume when it has ended.`;
    case "resume_in_progress": {
      const child = run.resumed_as.find((r) => !isTerminal(r.state));
      return child ? (
        <>
          A resume of this run is already running:{" "}
          <Link to="/runs/$id" params={{ id: child.id }}>
            {child.name ?? child.id}
          </Link>
          .
        </>
      ) : (
        "A run of this launch directory has not ended yet."
      );
    }
    case "cli_observed":
      return "Runs started from a terminal are resumed from the terminal.";
    case "not_failed_or_cancelled":
      return "Only a failed or cancelled run can be resumed.";
    case "launch_dir_refused":
      return "Spectio will not resume in this run's launch directory: it, or a file in it, is not yours or is writable by others.";
    case "session_id_refused":
      return "This run's Nextflow session ID is not one Spectio can pass to -resume.";
    case "profiles_unknown":
      return "Spectio cannot read this run's profiles from its run directory, so it cannot resume it as it ran.";
    default:
      return null;
  }
}

/** Where the resume runs, from the run's snapshot (ui-spec §4.8.1 Resume, api §5.4); a run with
 * no snapshot (started from a terminal) says nothing. */
function whereWords(run: RunDetail, server: ServerVersion | null): string | null {
  const env = run.environment;
  if (!env || env.state === "not_readable") return null;
  if (env.state === "not_recorded") return `This run has no recorded environment: it resumes on the server's default (${server?.executor ?? "slurm"}).`;
  if (env.executor === "local" && server?.executor === "slurm" && !env.local?.cpus && !env.local?.mem_mib) {
    return "It runs with the login node's limits (2 CPUs, 8 GiB).";
  }
  return `Runs on ${runEnvName(env)} as before.`;
}

/** The dialog's text: where the new run starts and what the engine reuses. The launch directory
 * is named only for a run that is not itself a resume: a resume runs in its first run's. */
function Ask({ run, server }: { run: RunDetail; server: ServerVersion | null }) {
  const snakemake = run.workflow.engine === "snakemake";
  const { units } = words(run.workflow.engine);
  const where = server && !run.parent_run_id ? `${server.runs_root}/${run.id}/launch` : null;
  const head = run.head;
  const runsOn = whereWords(run, server);
  return (
    <>
      <p>
        Spectio starts a new run in the same launch directory. {engineName(run.workflow.engine)} runs again with{" "}
        <code>{snakemake ? "--rerun-incomplete" : "-resume"}</code> and reuses the {run.summary.tasks.done} {units} that finished. This
        run stays {runWord(run.state)}.
      </p>
      {where && <code className="sp-resume-path">{where}</code>}
      {runsOn && <p>{runsOn}</p>}
      {head && !head.alive && (
        <p className="sp-note">The head of this run has ended on {head.node} (checked): Spectio unlocks the directory first.</p>
      )}
    </>
  );
}

export function ResumeAction({ run, server, fullWidth = false }: { run: RunDetail; server: ServerVersion | null; fullWidth?: boolean }) {
  const phone = usePhone();
  const navigate = useNavigate();
  const [asking, setAsking] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ReactNode>(null);
  const unreadable = run.environment?.state === "not_readable";
  const allowed = run.actions.resume.allowed && !unreadable;
  const why = unreadable
    ? "Its recorded environment cannot be read."
    : allowed ? null : (refusedWords(run.actions.resume.reason ?? "", run, server) ?? "Resume is not possible now.");

  const close = () => {
    setAsking(false);
    setError(null);
  };
  const confirm = () => {
    setSending(true);
    setError(null);
    resumeRun(run.id)
      .then((child) => navigate({ to: "/runs/$id", params: { id: child.id } }))
      .catch((e: Error) => {
        const words = e instanceof ApiError && e.reason ? refusedWords(e.reason, run, server) : null;
        setError(words ?? e.message);
      })
      .finally(() => setSending(false));
  };

  const cancel = (
    <Button variant="default" data-autofocus onClick={close} fullWidth={phone}>
      Cancel
    </Button>
  );
  const go = (
    <Button onClick={confirm} loading={sending} leftSection={<Icon path={ICONS.reload} size={15} />} fullWidth={phone}>
      Resume
    </Button>
  );
  const body = (
    <>
      <Ask run={run} server={server} />
      {error && (
        <p role="alert" className="sp-alert">
          Not resumed: {error}
        </p>
      )}
      {/* the board's order: Resume above Cancel on the phone, Cancel then Resume on the desktop */}
      <div className="sp-actions" data-stack={phone || undefined}>
        {phone ? go : cancel}
        {phone ? cancel : go}
      </div>
    </>
  );
  return (
    <>
      <Button
        className="sp-resume"
        onClick={() => allowed && setAsking(true)}
        aria-disabled={allowed ? undefined : true}
        data-disabled={allowed ? undefined : true}
        aria-describedby={why ? "resume-why" : undefined}
        leftSection={<Icon path={ICONS.reload} size={15} />}
        fullWidth={fullWidth}
      >
        Resume
      </Button>
      {why && (
        <p id="resume-why" className="sp-resume-why">
          <Icon path={ICONS.info} size={15} /> <span>{why}</span>
        </p>
      )}
      {phone ? (
        <Drawer
          opened={asking}
          onClose={close}
          position="bottom"
          title="Resume this run?"
          returnFocus
          classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}
        >
          {body}
        </Drawer>
      ) : (
        <Modal opened={asking} onClose={close} title="Resume this run?" returnFocus centered>
          {body}
        </Modal>
      )}
    </>
  );
}
