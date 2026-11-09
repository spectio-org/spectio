// The environment form's fields and their rules (ui-spec §4.8.1; api §5.4 owns the rules): the
// strings the inputs hold, the typed body they become, and the summary line of a card.
import type { EnvironmentBody, EnvironmentItem } from "../api";

export type Unit = "MiB" | "GiB";
export interface Draft {
  name: string;
  label: string;
  executor: "slurm" | "local";
  partition: string;
  account: string;
  hours: string;
  minutes: string;
  mem: string;
  memUnit: Unit;
  cpus: string;
  localMem: string;
  localUnit: Unit;
  nextflow: string;
  snakemake: string;
}
export const EMPTY: Draft = {
  ...{ name: "", label: "", executor: "slurm", partition: "", account: "", hours: "", minutes: "" },
  ...{ mem: "", memUnit: "GiB", cpus: "", localMem: "", localUnit: "GiB", nextflow: "", snakemake: "" },
};

/** Errors keyed by the API's field path, so a server `422` lands on the same field. */
export type Errors = Record<string, string>;

const NAME = /^[a-z][a-z0-9-]{0,31}$/;
const SLURM_NAME = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/;
const PROFILE = /^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$/;
const MAX_MIB = 4_194_304;

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

export function toBody(d: Draft): { body: EnvironmentBody | null; errors: Errors } {
  const errors: Errors = {};
  const name = d.name.trim();
  if (["local", "slurm"].includes(name)) errors.name = `${name} is a built-in name`;
  else if (name === "new") errors.name = "new is a reserved name";
  else if (!NAME.test(name)) errors.name = "Lowercase letters, digits and '-', up to 32, starting with a letter";
  if (d.label.length > 80) errors.label = "At most 80 characters";
  const named = (key: string, text: string, rule: RegExp, words: string) => {
    if (text.trim() !== "" && !rule.test(text.trim())) errors[key] = words;
    return text.trim() || null;
  };
  const slurmWords = "Letters, digits, '_', '.' and '-', up to 64, as SLURM names it";
  const profileWords = "One profile name: letters, digits, '_', '.' and '-'";
  const profiles = {
    nextflow: named("profiles.nextflow", d.nextflow, PROFILE, profileWords),
    snakemake: named("profiles.snakemake", d.snakemake, PROFILE, profileWords),
  };
  let slurm: EnvironmentBody["slurm"] = null;
  let local: EnvironmentBody["local"] = null;
  if (d.executor === "slurm") {
    const partition = named("slurm.partition", d.partition, SLURM_NAME, slurmWords);
    const account = named("slurm.account", d.account, SLURM_NAME, slurmWords);
    const h = whole(d.hours, 0, 720);
    const m = whole(d.minutes, 0, 59);
    let time_min: number | null = null;
    if (h === undefined || m === undefined) errors["slurm.time_min"] = "Hours 0 to 720, minutes 0 to 59";
    else if (h !== null || m !== null) {
      time_min = (h ?? 0) * 60 + (m ?? 0);
      if (time_min === 0) errors["slurm.time_min"] = "At least 1 minute";
      if (time_min > 43_200) errors["slurm.time_min"] = "At most 720 h";
    }
    const mem_mib = mib(d.mem, d.memUnit);
    if (mem_mib === undefined) errors["slurm.mem_mib"] = "Whole MiB, or GiB with one decimal; 1 MiB to 4,096 GiB";
    slurm = { partition, account, time_min, mem_mib: mem_mib ?? null };
  } else {
    const cpus = whole(d.cpus, 1, 256);
    if (cpus === undefined) errors["local.cpus"] = "A whole number, 1 to 256";
    const mem_mib = mib(d.localMem, d.localUnit);
    if (mem_mib === undefined) errors["local.mem_mib"] = "Whole MiB, or GiB with one decimal; 1 MiB to 4,096 GiB";
    local = { cpus: cpus ?? null, mem_mib: mem_mib ?? null };
  }
  if (Object.keys(errors).length) return { body: null, errors };
  return { body: { name, label: d.label.trim() || null, executor: d.executor, slurm, local, profiles }, errors };
}

const memText = (n: number | null): [string, Unit] =>
  n === null ? ["", "GiB"] : n % 1024 === 0 ? [String(n / 1024), "GiB"] : [String(n), "MiB"];

/** An item as the form's strings: hours and minutes, GiB when the value divides by 1024. */
export function fromItem(item: EnvironmentItem): Draft {
  const t = item.slurm?.time_min ?? null;
  const [mem, memUnit] = memText(item.slurm?.mem_mib ?? null);
  const [localMem, localUnit] = memText(item.local?.mem_mib ?? null);
  return {
    ...{ name: item.name, label: item.label ?? "", executor: item.executor, mem, memUnit, localMem, localUnit },
    ...{ partition: item.slurm?.partition ?? "", account: item.slurm?.account ?? "" },
    ...{ hours: t === null ? "" : String(Math.floor(t / 60)), minutes: t === null ? "" : String(t % 60) },
    ...{ cpus: item.local?.cpus == null ? "" : String(item.local.cpus) },
    ...{ nextflow: item.profiles.nextflow ?? "", snakemake: item.profiles.snakemake ?? "" },
  };
}

const memWords = (n: number) => (n % 1024 === 0 ? `${n / 1024} GiB` : `${n} MiB`);
const timeWords = (t: number) => [t >= 60 ? `${Math.floor(t / 60)} h` : "", t % 60 ? `${t % 60} min` : ""].filter(Boolean).join(" ");

/** The card's summary line, in words; an unset value is left out. Also a run's snapshot's. */
export function summary(item: Pick<EnvironmentItem, "executor" | "slurm" | "local">, node: string, serverExecutor: string): string {
  if (item.executor === "slurm") {
    const s = item.slurm;
    const parts = [
      s?.partition && `partition ${s.partition}`,
      s?.account && `SLURM account ${s.account}`,
      s?.time_min && `${timeWords(s.time_min)} per job`,
      s?.mem_mib && `${memWords(s.mem_mib)} per job`,
    ].filter(Boolean);
    return parts.length ? parts.join(" · ") : "SLURM's defaults for your account";
  }
  const where = serverExecutor === "slurm" ? `on ${node} (the login node)` : "this machine";
  const caps = [item.local?.cpus && `${item.local.cpus} CPUs`, item.local?.mem_mib && memWords(item.local.mem_mib)].filter(Boolean);
  return `${where} · ${caps.length ? `at most ${caps.join(" and ")}` : "no limit"}`;
}

export const label = (item: EnvironmentItem) => item.label ?? item.name;

/** A run's environment as its facts name it: the name, or a built-in's label (LiteStatesRun). */
export const runEnvName = (env: { name: string | null; label: string | null }) =>
  (env.name === "local" || env.name === "slurm" ? env.label : null) ?? env.name ?? "";
