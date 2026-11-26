// The words for an execution environment, the shape a run's snapshot keeps (api §5.4, §5.13):
// the summary line of a card, a run's environment name, and the environment a launch resolves
// from an execution profile and its compute (#408). The forms' fields live in ../compute/fields.
import type { Compute, ExecutionProfile, RunEnvironment } from "../api";
import { plural } from "../runs/stateWord";

export type Software = "conda" | "apptainer";

/** What Launch reads of the chosen profile: its values over its compute's, in the snapshot's shape. */
export interface Resolved {
  name: string;
  label: string | null;
  compute: string;
  executor: "local" | "slurm";
  slurm: (NonNullable<RunEnvironment["slurm"]> & { cpus?: number | null }) | null;
  local: NonNullable<RunEnvironment["local"]> | null;
  software: Software[];
  apptainer_args: string;
  profiles: ExecutionProfile["engine_profiles"];
}

/** The profile's resources on its compute's account and caps: what the run's snapshot will say. */
export function resolve(profile: ExecutionProfile, compute: Compute): Resolved {
  const r = profile.resources;
  return {
    ...{ name: profile.name, label: profile.label, compute: compute.name, executor: compute.executor },
    slurm:
      compute.executor === "slurm"
        ? { ...{ partition: r.partition, account: compute.slurm?.account ?? null, time_min: r.time_min, mem_mib: r.mem_mib }, constraint: r.constraint, gres: r.gres, cpus: r.cpus }
        : null,
    local: compute.executor === "local" ? { cpus: r.cpus ?? compute.local?.cpus ?? null, mem_mib: r.mem_mib ?? compute.local?.mem_mib ?? null } : null,
    software: profile.software,
    apptainer_args: compute.apptainer_args,
    profiles: profile.engine_profiles,
  };
}

export const memWords = (n: number) => (n % 1024 === 0 ? `${n / 1024} GiB` : `${n} MiB`);
export const timeWords = (t: number) => [t >= 60 ? `${Math.floor(t / 60)} h` : "", t % 60 ? `${t % 60} min` : ""].filter(Boolean).join(" ");

/** The environment's software, in words (inbox #161); absent in a run's snapshot from before
 * the field, and left out there. */
const softwareWords = (software: readonly Software[] | null | undefined): string =>
  software == null
    ? ""
    : software.length
      ? ` · deploys with ${software.join(" and ")}`
      : " · deploys no software";

/** The card's summary line, in words; an unset value is left out. Also a run's snapshot's.
 * `kindSaid`: the line already names the kind (a Launch card's second line says "Login node"),
 * so the where clause leaves "(the login node)" out. */
export function summary(
  item: Pick<Resolved, "executor"> & {
    slurm: (NonNullable<RunEnvironment["slurm"]> & { cpus?: number | null }) | null;
    local: RunEnvironment["local"];
    software?: readonly Software[] | null;
    apptainer_args?: string | null;
  },
  node: string,
  serverExecutor: string,
  kindSaid = false,
): string {
  if (item.executor === "slurm") {
    const s = item.slurm;
    const parts = [
      s?.partition && `partition ${s.partition}`,
      s?.account && `SLURM account ${s.account}`,
      s?.constraint && `constraint ${s.constraint}`,
      s?.gres && `GRES ${s.gres}`,
      s?.time_min && `${timeWords(s.time_min)} per job`,
      s?.mem_mib && `${memWords(s.mem_mib)} per job`,
      s?.cpus && `${plural(s.cpus, "CPU", "CPUs")} per job`,
    ].filter(Boolean);
    return parts.length ? parts.join(" · ") + softwareWords(item.software) : `SLURM's defaults for your account${softwareWords(item.software)}`;
  }
  const where = serverExecutor === "slurm" ? `on ${node}${kindSaid ? "" : " (the login node)"}` : "this machine";
  const caps = [item.local?.cpus && plural(item.local.cpus, "CPU", "CPUs"), item.local?.mem_mib && memWords(item.local.mem_mib)].filter(Boolean);
  return `${where} · ${caps.length ? `at most ${caps.join(" and ")}` : "no limit"}${softwareWords(item.software)}`;
}

export const label = (item: { name: string; label: string | null }) => item.label ?? item.name;

/** A run's environment as its facts name it: the name, or a built-in's label (LiteStatesRun). */
export const runEnvName = (env: { name: string | null; label: string | null }) =>
  (env.name === "local" || env.name === "slurm" ? env.label : null) ?? env.name ?? "";
