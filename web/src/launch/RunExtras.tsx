import { NativeSelect, TextInput } from "@mantine/core";
import { type ReactNode, useEffect, useState } from "react";
import type { Engine, EnvironmentItem, LaunchTemplate } from "../api";
import { label as envLabel } from "../environments/fields";
import { ICONS, Icon } from "../icons";

// Resources and Extra config file, two folding rows of Launch's "Where it runs" (FU-P3-110d;
// ui-spec §4.6 notes of 2026-11-10 and the drawn layout of FU-P3-110c; api §5.7 owns the fields
// and their bounds; boards LiteLaunch, LiteLaunchSnakemake, MLiteLaunch). The browser checks the
// bounds and a `local` environment's caps; only the server reads the file, so its refusals come
// back on the input after Launch.

export type Unit = "MiB" | "GiB";
/** The inputs' strings. */
export interface Draft {
  cpus: string;
  mem: string;
  unit: Unit;
  hours: string;
  minutes: string;
}
export const NO_DRAFT: Draft = { cpus: "", mem: "", unit: "GiB", hours: "", minutes: "" };
/** `default_resources` of `POST /runs`: only the keys set. */
export interface Sent {
  cpus?: number;
  mem_mib?: number;
  time_min?: number;
}
export type ResourceKey = "resources.cpus" | "resources.mem" | "resources.time";
/** A field's error, and its words after "Fix <field>: " in Before Launch. */
export interface Wrong {
  message: string;
  brief: string;
}
export interface Context {
  engine: Engine | null;
  profile: string;
  env: EnvironmentItem | null;
}

const MAX_MIB = 4_194_304;
const MAX_MIN = 43_200;
export const RESOURCE_LABELS: Record<ResourceKey, string> = {
  "resources.cpus": "CPUs per task",
  "resources.mem": "Memory per task",
  "resources.time": "Time per task",
};

export const memWords = (n: number) => (n % 1024 === 0 ? `${n / 1024} GiB` : `${n} MiB`);
export const timeWords = (t: number) => [t >= 60 ? `${Math.floor(t / 60)} h` : "", t % 60 ? `${t % 60} min` : ""].filter(Boolean).join(" ");

/** "2 CPUs · 6 GiB · 2 h": the keys set, in the order of the form. */
export function resourceWords(r: { cpus?: number | null; mem_mib?: number | null; time_min?: number | null }): string {
  return [r.cpus && (r.cpus === 1 ? "1 CPU" : `${r.cpus} CPUs`), r.mem_mib && memWords(r.mem_mib), r.time_min && timeWords(r.time_min)]
    .filter(Boolean)
    .join(" · ");
}

const whole = (text: string) => (/^\d+$/.test(text.trim()) ? Number(text.trim()) : null);
const lowerFirst = (s: string) => s.charAt(0).toLowerCase() + s.slice(1);
/** A Snakemake profile owns the resources: nothing is set or sent (api §5.7). */
const fromProfile = (c: Context) => c.engine === "snakemake" && !!c.profile;

/** The draft as `default_resources`, and the errors of the keys that cannot be sent. CPUs are
 * not read on Snakemake, and nothing with a Snakemake profile: those values stay unsent. */
export function readResources(d: Draft, c: Context): { sent: Sent; errors: Partial<Record<ResourceKey, Wrong>> } {
  const sent: Sent = {};
  const errors: Partial<Record<ResourceKey, Wrong>> = {};
  if (fromProfile(c)) return { sent, errors };
  const where = c.env ? envLabel(c.env) : "";
  const caps = c.env?.executor === "local" ? c.env.local : null;
  const fail = (key: ResourceKey, message: string, brief = lowerFirst(message)) => (errors[key] = { message, brief });
  if (c.engine !== "snakemake" && d.cpus.trim()) {
    const n = whole(d.cpus);
    if (n === null || n < 1 || n > 256) fail("resources.cpus", "A whole number from 1 to 256");
    // the server's words (api/extras.py), so the same line before and after Launch
    else if (caps?.cpus != null && n > caps.cpus) fail("resources.cpus", `At most ${caps.cpus} CPUs in ${where}`, `at most ${caps.cpus} on ${where}`);
    else sent.cpus = n;
  }
  if (d.mem.trim()) {
    const text = d.mem.trim();
    const n = Math.round(Number(text) * (d.unit === "GiB" ? 1024 : 1));
    if (!(d.unit === "MiB" ? /^\d+$/ : /^\d+(\.\d+)?$/).test(text)) fail("resources.mem", d.unit === "MiB" ? "Whole MiB, such as 512" : "A number of GiB, such as 16");
    else if (n < 1) fail("resources.mem", "At least 1 MiB");
    else if (n > MAX_MIB) fail("resources.mem", "At most 4,096 GiB (4 TiB)");
    else if (caps?.mem_mib != null && n > caps.mem_mib) fail("resources.mem", `At most ${memWords(caps.mem_mib)} in ${where}`, `at most ${memWords(caps.mem_mib)} on ${where}`);
    else sent.mem_mib = n;
  }
  if (d.hours.trim() || d.minutes.trim()) {
    const h = d.hours.trim() ? whole(d.hours) : 0;
    const m = d.minutes.trim() ? whole(d.minutes) : 0;
    if (h === null || m === null || m > 59) fail("resources.time", "Whole hours, and minutes from 0 to 59");
    else if (h * 60 + m < 1) fail("resources.time", "At least 1 minute");
    else if (h * 60 + m > MAX_MIN) fail("resources.time", "At most 720 hours (30 days)");
    else sent.time_min = h * 60 + m;
  }
  return { sent, errors };
}

/** The environment's own values, for a `slurm` one (api §5.4): "48 h · 32 GiB". */
function envWords(env: EnvironmentItem | null): string {
  const s = env?.executor === "slurm" ? env.slurm : null;
  return [s?.time_min && timeWords(s.time_min), s?.mem_mib && memWords(s.mem_mib)].filter(Boolean).join(" · ");
}

/** The Resources row's closed line (ui-spec §4.6). */
function closedLine(sent: Sent, c: Context): string {
  if (fromProfile(c)) return `From the profile ${c.profile}`;
  if (Object.keys(sent).length) return `Defaults: ${resourceWords(sent)} per task`;
  const env = envWords(c.env);
  return env ? `From the environment: ${env} per task` : "The pipeline's defaults";
}

/** The Summary's Resources line. */
export function summaryLine(sent: Sent, c: Context): string {
  if (fromProfile(c)) return `from the profile ${c.profile}`;
  if (!Object.keys(sent).length) return "from the environment";
  return `${resourceWords(sent)} per task; ${c.engine === "snakemake" ? "rules" : "processes"} that set their own keep them`;
}

/** Copy to a new launch: the template's `default_resources` as the inputs' strings. */
export function draftFrom(r: LaunchTemplate["default_resources"]): Draft {
  const mem = r?.mem_mib ?? null;
  const t = r?.time_min ?? null;
  return {
    cpus: r?.cpus == null ? "" : String(r.cpus),
    ...(mem === null ? { mem: "", unit: "GiB" } : mem % 1024 === 0 ? { mem: String(mem / 1024), unit: "GiB" } : { mem: String(mem), unit: "MiB" }),
    hours: t === null ? "" : String(Math.floor(t / 60)),
    minutes: t === null ? "" : String(t % 60),
  };
}

/** The name the run keeps the file as (api §5.7). */
export const keptAs = (engine: Engine | null, path: string) =>
  engine !== "snakemake" ? "extra.config" : path.trim().endsWith(".json") ? "extra.json" : "extra.yaml";
export const baseName = (path: string) => path.trim().split("/").filter(Boolean).at(-1) ?? path;

/** The form's own hint after a refusal of `check_config_file`, under the server's words. */
function configHint(message: string): string | null {
  if (message.includes("writable by group or others")) return "Fix its mode (chmod go-w), then Launch again.";
  if (message.includes("symbolic link")) return "Give the path of the file itself, not of a link to it.";
  if (message.includes("no such file")) return "Check the path, then Launch again.";
  if (message.includes("larger than 256 KiB")) return "Make it smaller than 256 KiB, then Launch again.";
  return null;
}

/** A bordered sub-card whose heading is a button (aria-expanded); folded by default, opened by
 * `reveal` changing to a truthy value (an error on one of its fields, a Before Launch link). */
function SubRow({ id, title, closed, reveal, children }: { id: string; title: string; closed: string; reveal: boolean | string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (reveal) setOpen(true);
  }, [reveal]);
  return (
    <div className="launch-xrow">
      <h3 className="launch-xrow-head">
        <button type="button" aria-expanded={open} aria-controls={`${id}-body`} onClick={() => setOpen(!open)}>
          <span className="launch-xrow-title">{title}</span>
          {" "}
          <span className="launch-xrow-sum">{closed}</span>
          <span className="sp-fold-chev">
            <Icon path={ICONS.chevronDown} size={16} stroke={2} />
          </span>
        </button>
      </h3>
      <div id={`${id}-body`} className="launch-xrow-body" hidden={!open}>
        {open && children}
      </div>
    </div>
  );
}

/** The Resources row: CPUs (not on Snakemake), memory with its unit, time as hours and minutes;
 * each empty by default, its placeholder the environment's value. `errors`: the server's, by form
 * key (`resources.cpus`, … and `resources` for the profile's refusal). */
export function ResourcesRow({
  draft,
  onChange,
  c,
  errors,
  reveal,
}: {
  draft: Draft;
  onChange: (d: Draft) => void;
  c: Context;
  errors: Record<string, string>;
  reveal: boolean | string;
}) {
  const { sent, errors: wrong } = readResources(draft, c);
  const error = (key: ResourceKey) => wrong[key]?.message ?? errors[key];
  const set = (part: Partial<Draft>) => onChange({ ...draft, ...part });
  const snakemake = c.engine === "snakemake";
  const where = c.env ? envLabel(c.env) : "";
  const caps = c.env?.executor === "local" ? c.env.local : null;
  const slurm = c.env?.executor === "slurm" ? c.env.slurm : null;
  const envMem = slurm?.mem_mib ?? null;
  const envTime = slurm?.time_min ?? null;
  const memHint =
    envMem !== null
      ? `Empty: ${memWords(envMem)}, from ${where}`
      : `Rounded to MiB · ${caps?.mem_mib != null ? `at most ${memWords(caps.mem_mib)} (${where})` : "1 MiB to 4,096 GiB (4 TiB)"}`;
  const timeHint = [
    envTime !== null ? `Empty: ${timeWords(envTime)}, from ${where}` : "1 min to 720 h (30 days)",
    snakemake && c.env?.executor === "local" && "not enforced on this machine",
  ]
    .filter(Boolean)
    .join(" · ");
  const memPlaceholder =
    envMem === null ? "the pipeline's default" : draft.unit === "MiB" ? String(envMem) : String(Math.round((envMem / 1024) * 10) / 10);
  const timeError = error("resources.time");
  const timeIds = [timeError && "res-time-e", "res-time-hint"].filter(Boolean).join(" ");
  const unit = (
    <NativeSelect
      id="res-mem-u"
      label="Memory per task, unit"
      classNames={{ label: "sp-sr" }}
      value={draft.unit}
      onChange={(e) => set({ unit: e.currentTarget.value as Unit })}
      data={["MiB", "GiB"]}
    />
  );
  return (
    <SubRow id="launch-resources" title="Resources" closed={closedLine(sent, c)} reveal={reveal}>
      {fromProfile(c) ? (
        <p className="launch-keep">
          {`The profile ${c.profile} sets the resources, so none are set here. Without a profile: memory and time per task. Values typed before a Snakemake profile was picked are kept in the form but not sent.`}
        </p>
      ) : (
        <>
          <p className="sp-muted launch-xrow-hint">
            {snakemake
              ? "Used by every rule that does not set its own. A rule that sets its own memory or time keeps them. Each is optional."
              : "Used by every process that does not set its own. A process that sets its own CPUs, memory or time keeps them. Replaces the pipeline's own default for all processes. Each is optional."}
          </p>
          {snakemake && <p className="launch-keep">Snakemake takes CPUs from each rule's threads.</p>}
          <div className="launch-res">
            {!snakemake && (
              <TextInput
                id="res-cpus"
                label="CPUs per task"
                inputWrapperOrder={["label", "input", "error", "description"]}
                inputMode="numeric"
                placeholder="the pipeline's default"
                value={draft.cpus}
                onChange={(e) => set({ cpus: e.currentTarget.value })}
                description={`1 to 256${caps?.cpus != null ? ` · at most ${caps.cpus} (${where})` : ""}`}
                error={error("resources.cpus")}
                autoComplete="off"
              />
            )}
            <TextInput
              id="res-mem"
              label="Memory per task"
              inputWrapperOrder={["label", "input", "error", "description"]}
              inputMode="decimal"
              placeholder={memPlaceholder}
              value={draft.mem}
              onChange={(e) => set({ mem: e.currentTarget.value })}
              inputContainer={(input) => (
                <div className="launch-unit">
                  {input}
                  {unit}
                </div>
              )}
              description={memHint}
              error={error("resources.mem")}
              autoComplete="off"
            />
            <fieldset className="launch-time">
              <legend>Time per task</legend>
              <div className="launch-unit">
                <label className="sp-sr" htmlFor="res-time-h">
                  Time per task, hours
                </label>
                <input
                  id="res-time-h"
                  className="launch-native"
                  aria-invalid={timeError ? true : undefined}
                  aria-describedby={timeIds}
                  inputMode="numeric"
                  placeholder={envTime === null ? "–" : String(Math.floor(envTime / 60))}
                  value={draft.hours}
                  onChange={(e) => set({ hours: e.currentTarget.value })}
                  autoComplete="off"
                />
                <span aria-hidden="true">h</span>
                <label className="sp-sr" htmlFor="res-time-m">
                  Time per task, minutes
                </label>
                <input
                  id="res-time-m"
                  className="launch-native"
                  aria-invalid={timeError ? true : undefined}
                  aria-describedby={timeIds}
                  inputMode="numeric"
                  placeholder={envTime === null ? "–" : String(envTime % 60)}
                  value={draft.minutes}
                  onChange={(e) => set({ minutes: e.currentTarget.value })}
                  autoComplete="off"
                />
                <span aria-hidden="true">min</span>
              </div>
              {timeError && (
                <span id="res-time-e" className="launch-field-error">
                  {timeError}
                </span>
              )}
              <span id="res-time-hint" className="sp-muted launch-field-hint">
                {timeHint}
              </span>
            </fieldset>
          </div>
        </>
      )}
      {errors.resources && (
        <p role="alert" className="launch-field-error">
          {errors.resources}
        </p>
      )}
    </SubRow>
  );
}

/** The Extra config file row: one typed path (no picker: the browser cannot list the server's
 * files), its hint by engine and what the run keeps; while Launch reads it, read-only with a
 * status line; a `422` of `POST /runs` in the server's words, then the form's own hint. */
export function ConfigFileRow({
  path,
  onChange,
  engine,
  error,
  reading,
  node,
  reveal,
}: {
  path: string;
  onChange: (path: string) => void;
  engine: Engine | null;
  error?: string;
  /** Launch is reading it. */
  reading: boolean;
  node: string;
  reveal: boolean | string;
}) {
  const snakemake = engine === "snakemake";
  const kept = keptAs(engine, path);
  const hint = error ? configHint(error) : null;
  const where = "In your home directory or in the pipeline: type its absolute path (the browser cannot list the server's files).";
  return (
    <SubRow id="launch-config" title="Extra config file" closed={path.trim() ? baseName(path) : "No extra config file"} reveal={reveal}>
      <TextInput
        id="launch-config-file"
        label="Extra config file (optional)"
        inputWrapperOrder={["label", "input", "error", "description"]}
        className="launch-config-input"
        value={path}
        onChange={(e) => onChange(e.currentTarget.value)}
        readOnly={reading}
        placeholder={snakemake ? "/home/…/extra.yaml" : "/home/…/my.config"}
        spellCheck={false}
        autoComplete="off"
        error={
          error && (
            <span role="alert" className="sp-lines">
              <span>{error}</span>
              {hint && <span className="launch-error-hint">{hint}</span>}
            </span>
          )
        }
        description={
          <span className="sp-lines">
            <span>
              {snakemake
                ? `A .yaml or .json file of workflow config, merged key by key under the form's values: a key you set here wins, the file's other keys stay. Not a profile: it sets config, not resources. ${where}`
                : `A .config file, passed with -c after the pipeline's own. It runs as you, like the pipeline's nextflow.config. Your withName and withLabel settings apply; the defaults above replace its general process settings. ${where}`}
            </span>
            <span className="launch-keep">
              <Icon path={ICONS.shield} size={13} />
              <span>
                {snakemake
                  ? "Read once at Launch and kept with the run as extra.yaml (extra.json for a .json file), readable by you only (0600), with its SHA-256 · at most 256 KiB · a top-level map, no __use_yte__."
                  : `Read once at Launch and kept with the run as ${kept}, readable by you only (0600), with its SHA-256 · at most 256 KiB · a later edit of your file changes no run.`}
              </span>
            </span>
          </span>
        }
      />
      {reading && path.trim() && (
        <p role="status" className="launch-reading">
          {`Reading ${baseName(path)} on ${node}: its owner, mode and size, then a copy for the run…`}
        </p>
      )}
    </SubRow>
  );
}
