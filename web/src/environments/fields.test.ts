import { expect, test } from "vitest";
import type { Compute, ExecutionProfile } from "../api";
import { type Resolved, resolve, summary } from "./fields";

const NO_SLURM = { partition: null, account: null, time_min: null, mem_mib: null };
const item = (over: Partial<Resolved> = {}): Resolved => ({
  name: "mylab-long",
  label: null,
  compute: "mylab",
  executor: "slurm",
  slurm: { partition: "htc", account: "mylab", time_min: 150, mem_mib: 1536 },
  local: null,
  software: ["conda", "apptainer"],
  apptainer_args: "",
  profiles: { nextflow: null, snakemake: null },
  ...over,
});

test("the summary names the constraint, gres and CPUs when set (#401, #408)", () => {
  const slurm = { partition: "gpu", account: null, time_min: null, mem_mib: null, constraint: "avx512&zen4", gres: "gpu:H100:1", cpus: 8 };
  expect(summary(item({ slurm }), "login1", "slurm")).toBe(
    "partition gpu · constraint avx512&zen4 · GRES gpu:H100:1 · 8 CPUs per job · deploys with conda and apptainer",
  );
});

test("the summary line, in words; an unset value is left out", () => {
  expect(summary(item(), "login1", "slurm")).toBe(
    "partition htc · SLURM account mylab · 2 h 30 min per job · 1536 MiB per job · deploys with conda and apptainer",
  );
  expect(summary(item({ slurm: { ...NO_SLURM, time_min: 120, mem_mib: 8192 } }), "login1", "slurm")).toBe("2 h per job · 8 GiB per job · deploys with conda and apptainer");
  expect(summary(item({ slurm: NO_SLURM }), "login1", "slurm")).toBe("SLURM's defaults for your account · deploys with conda and apptainer");
  const local = item({ executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 } });
  expect(summary(local, "login1", "slurm")).toBe("on login1 (the login node) · at most 2 CPUs and 8 GiB · deploys with conda and apptainer");
  expect(summary(local, "login1", "slurm", true)).toBe("on login1 · at most 2 CPUs and 8 GiB · deploys with conda and apptainer");
  expect(summary(item({ executor: "local", slurm: null, local: { cpus: null, mem_mib: null } }), "pc", "local")).toBe(
    "this machine · no limit · deploys with conda and apptainer",
  );
  expect(summary(item({ executor: "local", slurm: null, local: { cpus: 1, mem_mib: null } }), "login1", "slurm")).toMatch(/at most 1 CPU · /);
});

test("the summary line names the software the item has, and nothing when absent (inbox #161)", () => {
  expect(summary(item({ software: ["conda"] }), "login1", "slurm")).toMatch(/ · deploys with conda$/);
  expect(summary(item({ software: [] }), "login1", "slurm")).toMatch(/ · deploys no software$/);
  expect(summary(item({ software: undefined as unknown as Resolved["software"] }), "login1", "slurm")).not.toContain("deploys");
});

const compute = (over: Partial<Compute> = {}): Compute => ({
  ...{ name: "mylab", label: null, executor: "slurm", slurm: { account: "lab-a" }, local: null, software: ["conda", "apptainer"] },
  ...{ apptainer_args: "--bind /g", builtin: false, usable: true, unusable_reason: null, etag: '"c"' },
  ...over,
});
const profile = (over: Partial<ExecutionProfile> = {}): ExecutionProfile => ({
  name: "gpu",
  label: null,
  compute: "mylab",
  resources: { partition: "gpu-el10", constraint: null, gres: "gpu:H100:1", time_min: 240, mem_mib: 65536, cpus: 8 },
  software: ["apptainer"],
  engine_profiles: { nextflow: "slurm", snakemake: null },
  builtin: false,
  etag: '"p"',
  ...over,
});

test("a profile resolves on its compute: the account and binds are the compute's, the resources the profile's", () => {
  const r = resolve(profile(), compute());
  expect(r).toMatchObject({
    ...{ name: "gpu", compute: "mylab", executor: "slurm", local: null, software: ["apptainer"], apptainer_args: "--bind /g" },
    slurm: { partition: "gpu-el10", account: "lab-a", time_min: 240, mem_mib: 65536, gres: "gpu:H100:1", cpus: 8 },
    profiles: { nextflow: "slurm", snakemake: null },
  });
});

test("on a local compute the profile's CPUs and memory win over the caps, the caps fill the rest", () => {
  const local = compute({ executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 } });
  expect(resolve(profile({ resources: { ...profile().resources, cpus: 4, mem_mib: null } }), local).local).toEqual({ cpus: 4, mem_mib: 8192 });
  expect(resolve(profile(), local).slurm).toBeNull();
});
