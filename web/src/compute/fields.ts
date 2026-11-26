// The Compute and Profile forms' fields and their rules (ui-spec §4.8.1; api §5.13 owns the
// rules): the strings the inputs hold and the typed body they become. The summary lines of the
// cards are in ../environments/fields.
import type { Compute, ComputeBody, ExecutionProfile, ExecutionProfileBody } from "../api";
import type { Software } from "../environments/fields";

export type Unit = "MiB" | "GiB";
export type Executor = "slurm" | "local";

/** Errors keyed by the API's field path, so a server `422` lands on the same field. */
export type Errors = Record<string, string>;

const NAME = /^[a-z][a-z0-9-]{0,31}$/;
const SLURM_NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
const CONSTRAINT = /^[A-Za-z0-9_.=:,&|!*[\]()-]{1,200}$/;
const GRES = /^[A-Za-z0-9_.:,=-]{1,100}$/;
const ENGINE_PROFILE = /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$/;
const MAX_MIB = 4_194_304;
export const ALL_SOFTWARE: Software[] = ["conda", "apptainer"];

/** A whole number from `low` to `high`, null when empty, undefined when it is not one. */
function whole(text: string, low: number, high: number): number | null | undefined {
  if (text.trim() === "") return null;
  const n = Number(text);
  return /^\d+$/.test(text.trim()) && n >= low && n <= high ? n : undefined;
}

/** MiB from whole MiB or GiB with one decimal, rounded to MiB; null when empty. */
function mib(text: string, unit: Unit): number | null | undefined {
  if (text.trim() === "") return null;
  const ok = unit === "MiB" ? /^\d+$/ : /^\d+(\.\d)?$/;
  const n = Math.round(Number(text) * (unit === "GiB" ? 1024 : 1));
  return ok.test(text.trim()) && n >= 1 && n <= MAX_MIB ? n : undefined;
}

const memText = (n: number | null): [string, Unit] => (n === null ? ["", "GiB"] : n % 1024 === 0 ? [String(n / 1024), "GiB"] : [String(n), "MiB"]);

/** The name and label rules both forms share; the built-ins' names are taken. */
function checkNames(d: { name: string; label: string }, errors: Errors): string {
  const name = d.name.trim();
  if (["local", "slurm"].includes(name)) errors.name = `${name} is a built-in name`;
  else if (name === "new") errors.name = "new is a reserved name";
  else if (!NAME.test(name)) errors.name = "Lowercase letters, digits and '-', up to 32, starting with a letter";
  if (d.label.length > 80) errors.label = "At most 80 characters";
  return name;
}

/** An optional text field: null when empty, an error under `key` when it breaks `rule`. */
function optional(errors: Errors, key: string, text: string, rule: RegExp, words: string): string | null {
  const value = text.trim();
  if (value !== "" && !rule.test(value)) errors[key] = words;
  return value || null;
}

const slurmWords = "Letters, digits, '_', '.' and '-', up to 64, as SLURM names it";
const MEM_WORDS = "Whole MiB, or GiB with one decimal; 1 MiB to 4,096 GiB";

// ---- Compute ----

export interface ComputeDraft {
  name: string;
  label: string;
  executor: Executor;
  account: string;
  cpus: string;
  localMem: string;
  localUnit: Unit;
  software: Software[];
  apptainerArgs: string;
}
export const EMPTY_COMPUTE: ComputeDraft = {
  ...{ name: "", label: "", executor: "slurm", account: "", cpus: "", localMem: "", localUnit: "GiB" },
  ...{ software: ALL_SOFTWARE, apptainerArgs: "" },
};

export function toComputeBody(d: ComputeDraft): { body: ComputeBody | null; errors: Errors } {
  const errors: Errors = {};
  const name = checkNames(d, errors);
  let slurm: ComputeBody["slurm"] = null;
  let local: ComputeBody["local"] = null;
  if (d.executor === "slurm") {
    slurm = { account: optional(errors, "slurm.account", d.account, SLURM_NAME, slurmWords) };
  } else {
    const cpus = whole(d.cpus, 1, 256);
    if (cpus === undefined) errors["local.cpus"] = "A whole number, 1 to 256";
    const mem_mib = mib(d.localMem, d.localUnit);
    if (mem_mib === undefined) errors["local.mem_mib"] = MEM_WORDS;
    local = { cpus: cpus ?? null, mem_mib: mem_mib ?? null };
  }
  // The arguments go to Apptainer as one word, never as shell text, but a control character has
  // no place in an argument.
  if (d.apptainerArgs.length > 500) errors["apptainer_args"] = "At most 500 characters";
  else if (/[\x00-\x1f]/.test(d.apptainerArgs)) errors["apptainer_args"] = "No control character";
  if (Object.keys(errors).length) return { body: null, errors };
  return {
    body: { name, label: d.label.trim() || null, executor: d.executor, slurm, local, software: d.software, apptainer_args: d.apptainerArgs },
    errors,
  };
}

/** A compute as the form's strings. A compute from before the software field keeps both methods. */
export const computeFromItem = (c: Compute): ComputeDraft => {
  const [localMem, localUnit] = memText(c.local?.mem_mib ?? null);
  return {
    ...{ name: c.name, label: c.label ?? "", executor: c.executor, account: c.slurm?.account ?? "" },
    ...{ cpus: c.local?.cpus == null ? "" : String(c.local.cpus), localMem, localUnit },
    ...{ software: c.software ?? ALL_SOFTWARE, apptainerArgs: c.apptainer_args ?? "" },
  };
};

// ---- Execution profile ----

export interface ProfileDraft {
  name: string;
  label: string;
  compute: string;
  partition: string;
  constraint: string;
  gres: string;
  hours: string;
  minutes: string;
  mem: string;
  memUnit: Unit;
  cpus: string;
  software: Software[];
  nextflow: string;
  snakemake: string;
}
export const EMPTY_PROFILE: ProfileDraft = {
  ...{ name: "", label: "", compute: "", partition: "", constraint: "", gres: "", hours: "", minutes: "" },
  ...{ mem: "", memUnit: "GiB", cpus: "", software: ALL_SOFTWARE, nextflow: "", snakemake: "" },
};

/** `executor`: the chosen compute's, null while none is chosen. Partition, constraint and GRES
 * are SLURM's: a local compute sends them empty. */
export function toProfileBody(d: ProfileDraft, executor: Executor | null): { body: ExecutionProfileBody | null; errors: Errors } {
  const errors: Errors = {};
  const name = checkNames(d, errors);
  if (!d.compute) errors.compute = "Choose a compute";
  const slurm = executor === "slurm";
  const partition = slurm ? optional(errors, "resources.partition", d.partition, SLURM_NAME, slurmWords) : null;
  const constraint = slurm ? optional(errors, "resources.constraint", d.constraint, CONSTRAINT, "Letters, digits and _.=:,&|!*[]()-, no spaces, up to 200") : null;
  const gres = slurm ? optional(errors, "resources.gres", d.gres, GRES, "Letters, digits and _.:,=-, no spaces, up to 100") : null;
  const h = whole(d.hours, 0, 720);
  const m = whole(d.minutes, 0, 59);
  let time_min: number | null = null;
  if (h === undefined || m === undefined) errors["resources.time_min"] = "Hours 0 to 720, minutes 0 to 59";
  else if (h !== null || m !== null) {
    time_min = (h ?? 0) * 60 + (m ?? 0);
    if (time_min === 0) errors["resources.time_min"] = "At least 1 minute";
    if (time_min > 43_200) errors["resources.time_min"] = "At most 720 h";
  }
  const mem_mib = mib(d.mem, d.memUnit);
  if (mem_mib === undefined) errors["resources.mem_mib"] = MEM_WORDS;
  const cpus = whole(d.cpus, 1, 256);
  if (cpus === undefined) errors["resources.cpus"] = "A whole number, 1 to 256";
  const words = "One profile name: letters, digits, '_', '.' and '-'";
  const engine_profiles = {
    nextflow: optional(errors, "engine_profiles.nextflow", d.nextflow, ENGINE_PROFILE, words),
    snakemake: optional(errors, "engine_profiles.snakemake", d.snakemake, ENGINE_PROFILE, words),
  };
  if (Object.keys(errors).length) return { body: null, errors };
  return {
    body: {
      ...{ name, label: d.label.trim() || null, compute: d.compute, software: d.software, engine_profiles },
      resources: { partition, constraint, gres, time_min, mem_mib: mem_mib ?? null, cpus: cpus ?? null },
    },
    errors,
  };
}

/** A profile as the form's strings: hours and minutes, GiB when the value divides by 1024. */
export const profileFromItem = (p: ExecutionProfile): ProfileDraft => {
  const t = p.resources.time_min;
  const [mem, memUnit] = memText(p.resources.mem_mib);
  return {
    ...{ name: p.name, label: p.label ?? "", compute: p.compute, partition: p.resources.partition ?? "" },
    ...{ constraint: p.resources.constraint ?? "", gres: p.resources.gres ?? "", mem, memUnit },
    ...{ hours: t === null ? "" : String(Math.floor(t / 60)), minutes: t === null ? "" : String(t % 60) },
    ...{ cpus: p.resources.cpus == null ? "" : String(p.resources.cpus), software: p.software, nextflow: p.engine_profiles.nextflow ?? "", snakemake: p.engine_profiles.snakemake ?? "" },
  };
};

/** A duplicate's name (FU-P3-111): `<name>-copy`, then `-copy-2`, `-3`…, unique among `taken`
 * and within the 32 characters of a name (the base is cut, never the suffix). */
export function copyName(name: string, taken: string[]): string {
  for (let i = 1; ; i++) {
    const suffix = i === 1 ? "-copy" : `-copy-${i}`;
    const candidate = name.slice(0, 32 - suffix.length).replace(/-+$/, "") + suffix;
    if (!taken.includes(candidate)) return candidate;
  }
}
