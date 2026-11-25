import "./runs.css";
import { Tooltip } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import type { ReactElement } from "react";
import type { Run, RunState, Task } from "../api";
import { type IconName, Icon } from "../icons";
import { PipelineMark } from "../shell/EngineMark";
import { partsLine, taskName } from "./taskName";
import { type Tone, classWord, lastSegment, plural, runWord, shortId, tone, words } from "./stateWord";

// The icons of ui-spec §3.1, one per tone: clock, play, flag, pause, check, cross, slash.
export const TONE_ICONS: Record<Tone, IconName> = {
  queued: "clock",
  running: "play",
  review: "flag",
  paused: "pause",
  succeeded: "check",
  failed: "cross",
  cancelled: "slash",
  cached: "check",
};

/** Icon and word, never colour alone (ui-spec §3.1); the colour is the state's tone token. `state`
 * picks the tone and icon (a run, stage or task state, or a stage or process word). */
export function Word({ state, word }: { state: string; word: string }) {
  const t = tone(state);
  return (
    <span className="sp-state" data-state={state} data-tone={t}>
      <Icon name={TONE_ICONS[t]} />
      {word}
    </span>
  );
}

/** The "near limit" badge in words, after a measured value (a peak or a duration above 90 %). */
export function NearLimit({ on }: { on: boolean }) {
  return on ? <> <span className="sp-near">near limit</span></> : null;
}

/** A checkpoint rule's mark: a small icon and the word, lighter than a chip (FU-P3-88a). */
export function CheckpointMark() {
  return (
    <span className="sp-checkpoint">
      <Icon name="signpost" /> Checkpoint
    </span>
  );
}

/** The "low" badge in words, after an efficiency under 25 % (ui-spec §4.4 note 2026-11-07). */
export function Low({ on }: { on: boolean }) {
  return on ? <> <span className="sp-near" data-low="">low</span></> : null;
}

export function StateWord({ state }: { state: RunState }) {
  return <Word state={state} word={runWord(state)} />;
}

/** The run's failure as words: "tool error · <message>", or, with no message, "tool error · see
 * the failed jobs" (UX-PAR-16); never blank. The count of failed jobs is not repeated here: the
 * header and the Tasks tab say it (#385). */
export function failureText(run: Run): string {
  const failure = run.failure as { class?: unknown; message?: unknown } | null;
  const message = typeof failure?.message === "string" ? failure.message.trim() : "";
  const kind = typeof failure?.class === "string" ? classWord(failure.class) : "";
  const detail = message || (run.summary.tasks.failed > 0 ? `see the failed ${words(run.workflow.engine).units}` : "");
  return [kind, detail].filter(Boolean).join(" · ") || "failed";
}

/** A path of an engine message, short: under one of `roots` (the pipeline directory, the run's
 * launch directory) relative to it; under a pipelines store (`…/pipelines/<forge>/<org>/<repo>/
 * <ref>/…`) relative to the pipeline there; anything else as it is. */
function relativeTo(path: string, roots: readonly string[]): string {
  const p = path.replace(/[.,;:]+$/, "");
  for (const root of [...roots].sort((a, b) => b.length - a.length).map((r) => r.replace(/\/+$/, ""))) {
    if (root && p.startsWith(`${root}/`)) return p.slice(root.length + 1);
  }
  const at = p.indexOf("/pipelines/");
  if (at >= 0) {
    const parts = p.slice(at + "/pipelines/".length).split("/").filter(Boolean);
    if (parts.length > 4) return parts.slice(4).join("/");
  }
  return p;
}

/** A failed run's message, short and actionable (inbox #161): the first meaningful line, its
 * absolute paths under the pipeline (or the run directory) made relative, a repeated
 * "File …, line N" trace collapsed to one "file:line", the whole capped at about 160 characters.
 * Example: `KeyError in file "…/pipelines/github.com/org/repo/main/workflow/rules/common.smk",
 * line 8: 'sample_sheet' File "…/common.smk", line 8, in <module>` reads
 * `KeyError 'sample_sheet' · workflow/rules/common.smk:8`. */
export function shortFailure(message: string, pipelineRoot?: string | readonly string[] | null): string {
  const text = (message ?? "").trim();
  if (!text) return "";
  const roots = (Array.isArray(pipelineRoot) ? pipelineRoot : pipelineRoot ? [pipelineRoot] : []).filter(
    (r): r is string => typeof r === "string" && !!r,
  );
  // the absolute paths, longest first so a shorter one never eats a longer one's place
  let out = text;
  for (const p of [...new Set(text.match(/\/[^\s"'`,:()[\]]+/g) ?? [])].sort((a, b) => b.length - a.length)) {
    const r = relativeTo(p, roots);
    if (r !== p) out = out.split(p).join(r);
  }
  // the engine's own " in file …, line N:" of the head, and the traceback's frames
  const frames = [...out.matchAll(/File\s+"?([^"\n,]+?)"?,\s*line\s+(\d+)(?:,\s*in\s+\S+)?/g)];
  const head = /\s+in\s+file\s+"?([^"\n,]+?)"?,\s+line\s+(\d+)\s*:?/.exec(out);
  // the first meaningful line: not blank, not the traceback's title, not itself a frame
  const lines = out.split("\n").map((l) => l.trim());
  const isFrame = (l: string) => /^File\s+"?[^"\n,]+?"?,\s+line\s+\d+/.test(l);
  const at = lines.findIndex((l) => l && l !== "Traceback (most recent call last):" && !isFrame(l));
  let what = at >= 0 ? lines[at] : (lines.find((l) => l) ?? "");
  // Snakemake puts the exception's value on the next line ("KeyError in file …, line 8:" then
  // "'sample_sheet'"): a head line ending in ":" takes that line too
  const next = at >= 0 ? lines.slice(at + 1).find((l) => l) : undefined;
  if (next && what.endsWith(":") && !isFrame(next)) what = `${what} ${next}`;
  for (const f of frames) if (what.includes(f[0])) what = what.split(f[0]).join(" ");
  if (head && what.includes(head[0])) what = what.replace(head[0], " ");
  what = what.replace(/\s+/g, " ").trim().replace(/[.,;:]$/, "");
  const place = frames[0] ? `${frames[0][1]}:${frames[0][2]}` : head ? `${head[1]}:${head[2]}` : "";
  const said = [what, place].filter(Boolean).join(" · ");
  return said.length > 160 ? `${said.slice(0, 159).trimEnd()}…` : said;
}

/** The context line under the state word in a table (ui-spec §3.1). */
export function stateContext(run: Run): string {
  const { unit, units } = words(run.workflow.engine);
  switch (run.state) {
    case "queued":
      return run.head ? "head started" : "head not started yet";
    case "running": {
      // jobs that wait in the scheduler are still a running run (#385)
      const running = run.task_counts.running ?? 0;
      const queued = run.task_counts.submitted ?? 0;
      if (running === 0 && queued > 0) {
        return `${run.task_counts.pending || queued === 1 ? "" : "all "}${plural(queued, unit, units)} queued in the scheduler`;
      }
      return `${plural(running, unit, units)} running`;
    }
    case "cancelling":
      return "stopping the engine";
    case "failed":
      return failureText(run);
    default:
      return "";
  }
}

export const runName = (run: Run): string => run.name ?? `Run ${shortId(run.id)}`;

/** The run's name as a link whose accessible name names the row ("Open run <name>"). */
export function RunLink({ run }: { run: Run }) {
  const name = runName(run);
  return (
    <Link to="/runs/$id" params={{ id: run.id }} className="sp-run-link" aria-label={`Open run ${name}`}>
      {name}
    </Link>
  );
}

/** The one count format of every progress cell: "24 / 32", or "242 / at least 347" while a
 * checkpoint is open (ui-spec §5.2); "—" with no total (#385). */
export function progressText(done: number, total: number, lower = false): string {
  if (!total) return "—";
  return lower ? `${done} / at least ${total}` : `${done} / ${total}`;
}

/** A run's progress as text: its jobs or tasks done of all. */
export function tasksText(run: Run): string {
  const t = run.summary.tasks;
  return progressText(t.done, t.total, t.lower_bound);
}

/** "n / m" with a bar beside it: indigo when all is done, running blue otherwise (UX-PAR-24).
 * The bar is decoration; the text says the value. `lower`: the total may grow (a checkpoint is
 * open), so the part past the known jobs is hatched and the bar is never full (ui-spec §5.2). */
export function Bar({ done, all, lower = false }: { done: number; all: number; lower?: boolean }) {
  const width = all ? Math.round((done / all) * 100) : 0;
  return (
    <span className="sp-bar" data-full={all > 0 && done === all && !lower} data-lower={lower || undefined} aria-hidden="true">
      <span style={{ width: `${width}%` }} />
    </span>
  );
}

/** The one progress cell (#385): "done / total" in tabular figures on one line, with the bar when
 * asked and the engine's unit after the count where the column holds both engines. */
export function Progress({ done, total, lower = false, bar = false, unit }: { done: number; total: number; lower?: boolean; bar?: boolean; unit?: string }) {
  return (
    <span className="sp-done">
      {bar && !!total && <Bar done={done} all={total} lower={lower} />}
      {`${progressText(done, total, lower)}${unit && total ? ` ${unit}` : ""}`}
    </span>
  );
}

/** The run's pipeline: its mark (nf-core for an nf-core/ name, else the engine's; inbox #91), the
 * name and the version, muted, on one line (UX-PAR-01). */
export function Pipeline({ run, size = 20 }: { run: Run; size?: number }) {
  const w = run.workflow;
  return (
    <span className="sp-pipeline">
      <PipelineMark engine={w.engine} name={w.name} size={size} />
      <span>
        {w.name ?? w.location}
        {w.version && <span className="sp-version"> {w.version}</span>}
      </span>
    </span>
  );
}

/** A name cut to one line by the CSS: its full text in a tooltip on hover and on focus (ui-spec
 * §12.8). The child is the focusable element, whose accessible name keeps the full name. */
export function NameTip({ label, children }: { label: string; children: ReactElement }) {
  return (
    <Tooltip label={label} events={{ hover: true, focus: true, touch: false }} multiline maw={360}>
      {children}
    </Tooltip>
  );
}

/** A task's name in a table: the rule or process in bold, and on a second dimmed line, cut with an
 * ellipsis, its wildcards or tag (#385). The row's own label names it whole. */
export function TaskName({ task }: { task: Task }) {
  const { parts } = taskName(task);
  return (
    <>
      <strong>
        <ProcessName name={task.process} />
      </strong>
      {parts.length > 0 && <span className="sp-open-parts">{partsLine(parts)}</span>}
    </>
  );
}

/** The last segment of a process name; the full name stays its accessible text (ui-spec §4.4). */
export function ProcessName({ name }: { name: string }) {
  const last = lastSegment(name);
  if (last === name) return <span className="sp-mono">{name}</span>;
  return (
    <span className="sp-mono">
      <span aria-hidden="true">{last}</span>
      <span className="sp-sr">{name}</span>
    </span>
  );
}

/** A task as one line: the engine's name for it (`ALIGN (S01)`), else its process and tag. */
export const taskLabel = (t: Task): string => t.name ?? (t.tag ? `${lastSegment(t.process)} (${t.tag})` : lastSegment(t.process));
