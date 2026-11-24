import "./runs.css";
import { Link } from "@tanstack/react-router";
import type { Run, RunState, Task } from "../api";
import { type IconName, Icon } from "../icons";
import { PipelineMark } from "../shell/EngineMark";
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

/** The run's failure as words: "tool error · <message>", or, with no message, "tool error · 2
 * tasks failed" (UX-PAR-16); never blank. */
export function failureText(run: Run): string {
  const failure = run.failure as { class?: unknown; message?: unknown } | null;
  const message = typeof failure?.message === "string" ? failure.message.trim() : "";
  const kind = typeof failure?.class === "string" ? classWord(failure.class) : "";
  const { unit, units } = words(run.workflow.engine);
  const failed = run.summary.tasks.failed;
  const detail = message || (failed > 0 ? `${plural(failed, unit, units)} failed` : "");
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
  let what = lines.find((l) => l && l !== "Traceback (most recent call last):" && !/^File\s+"?[^"\n,]+?"?,\s+line\s+\d+/.test(l));
  if (what === undefined) what = lines.find((l) => l) ?? "";
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
    case "running":
      return `${plural(run.task_counts.running ?? 0, unit, units)} running`;
    case "cancelling":
      return "stopping the engine";
    case "succeeded":
      return "completed";
    case "failed":
      return failureText(run);
    case "cancelled":
      return "cancelled";
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

/** "24 / 32", or "242 / at least 347" while a checkpoint is open (ui-spec §5.2); "—" with none. */
export function tasksText(run: Run): string {
  const t = run.summary.tasks;
  if (!t.total) return "—";
  return t.lower_bound ? `${t.done} / at least ${t.total}` : `${t.done} / ${t.total}`;
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
