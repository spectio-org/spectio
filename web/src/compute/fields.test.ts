import { expect, test } from "vitest";
import type { Compute, ExecutionProfile } from "../api";
import { EMPTY_COMPUTE, EMPTY_PROFILE, type ComputeDraft, type ProfileDraft, computeFromItem, profileFromItem, toComputeBody, toProfileBody } from "./fields";

const profile = (over: Partial<ProfileDraft> = {}): ProfileDraft => ({ ...EMPTY_PROFILE, name: "gpu-h100", compute: "embl-slurm", ...over });
const compute = (over: Partial<ComputeDraft> = {}): ComputeDraft => ({ ...EMPTY_COMPUTE, name: "embl-slurm", ...over });
const onSlurm = (d: ProfileDraft) => toProfileBody(d, "slurm");

test("hours and minutes become time_min; both empty is unset; 0 and 0 is an error", () => {
  expect(onSlurm(profile({ hours: "2", minutes: "30" })).body?.resources.time_min).toBe(150);
  expect(onSlurm(profile({ hours: "2", minutes: "" })).body?.resources.time_min).toBe(120);
  expect(onSlurm(profile({ hours: "", minutes: "45" })).body?.resources.time_min).toBe(45);
  expect(onSlurm(profile()).body?.resources.time_min).toBeNull();
  expect(onSlurm(profile({ hours: "0", minutes: "0" })).errors).toEqual({ "resources.time_min": "At least 1 minute" });
  expect(onSlurm(profile({ hours: "721" })).errors["resources.time_min"]).toMatch(/Hours 0 to 720/);
  expect(onSlurm(profile({ hours: "720", minutes: "1" })).errors["resources.time_min"]).toMatch(/720 h/);
  expect(onSlurm(profile({ minutes: "60" })).errors["resources.time_min"]).toMatch(/minutes 0 to 59/);
  expect(onSlurm(profile({ hours: "1.5" })).errors["resources.time_min"]).toBeDefined();
});

test("GiB becomes mem_mib, rounded to MiB, with one decimal at most", () => {
  expect(onSlurm(profile({ mem: "1.5", memUnit: "GiB" })).body?.resources.mem_mib).toBe(1536);
  expect(onSlurm(profile({ mem: "8", memUnit: "GiB" })).body?.resources.mem_mib).toBe(8192);
  expect(onSlurm(profile({ mem: "500", memUnit: "MiB" })).body?.resources.mem_mib).toBe(500);
  expect(onSlurm(profile({ mem: "1.25", memUnit: "GiB" })).errors["resources.mem_mib"]).toBeDefined();
  expect(onSlurm(profile({ mem: "0", memUnit: "MiB" })).errors["resources.mem_mib"]).toBeDefined();
  expect(onSlurm(profile({ mem: "4097", memUnit: "GiB" })).errors["resources.mem_mib"]).toBeDefined();
});

test("the profile's rules: name, built-in names, compute, partition, CPUs, engine profiles", () => {
  expect(onSlurm(profile({ name: "" })).errors.name).toMatch(/Lowercase letters/);
  expect(onSlurm(profile({ name: "slurm" })).errors.name).toBe("slurm is a built-in name");
  expect(onSlurm(profile({ name: "new" })).errors.name).toBe("new is a reserved name");
  expect(toProfileBody(profile({ compute: "" }), null).errors.compute).toBe("Choose a compute");
  expect(onSlurm(profile({ partition: "gpu el10" })).errors["resources.partition"]).toBeDefined();
  expect(onSlurm(profile({ constraint: "a b" })).errors["resources.constraint"]).toBeDefined();
  expect(onSlurm(profile({ gres: "gpu 1" })).errors["resources.gres"]).toBeDefined();
  expect(onSlurm(profile({ cpus: "257" })).errors["resources.cpus"]).toMatch(/1 to 256/);
  expect(onSlurm(profile({ nextflow: "a,b" })).errors["engine_profiles.nextflow"]).toBeDefined();
  expect(onSlurm(profile({ label: "x".repeat(81) })).errors.label).toBeDefined();
});

test("a valid profile is the POST body; a local compute sends no partition, constraint or GRES", () => {
  const typed = profile({ label: "One H100", partition: "gpu-el10", constraint: "avx512", gres: "gpu:H100:1", hours: "4", mem: "64", cpus: "8", nextflow: "singularity", software: ["apptainer"] });
  const { body, errors } = onSlurm(typed);
  expect(errors).toEqual({});
  expect(body).toEqual({
    name: "gpu-h100",
    label: "One H100",
    compute: "embl-slurm",
    resources: { partition: "gpu-el10", constraint: "avx512", gres: "gpu:H100:1", time_min: 240, mem_mib: 65536, cpus: 8 },
    software: ["apptainer"],
    engine_profiles: { nextflow: "singularity", snakemake: null },
  });
  expect(toProfileBody(typed, "local").body?.resources).toEqual({ partition: null, constraint: null, gres: null, time_min: 240, mem_mib: 65536, cpus: 8 });
});

const stored = (over: Partial<ExecutionProfile> = {}): ExecutionProfile => ({
  name: "gpu-h100",
  label: null,
  compute: "embl-slurm",
  resources: { partition: "gpu", constraint: null, gres: "gpu:H100:1", time_min: 150, mem_mib: 1536, cpus: 4 },
  software: ["apptainer"],
  engine_profiles: { nextflow: null, snakemake: "slurm-prof" },
  builtin: false,
  etag: '"p"',
  ...over,
});

test("a profile reads back into the form: hours and minutes, GiB when it divides by 1024, and saves as it was", () => {
  const back = profileFromItem(stored());
  expect([back.hours, back.minutes, back.mem, back.memUnit, back.cpus, back.software]).toEqual(["2", "30", "1536", "MiB", "4", ["apptainer"]]);
  expect(onSlurm(back).body).toMatchObject({ resources: { time_min: 150, mem_mib: 1536, cpus: 4 }, engine_profiles: { snakemake: "slurm-prof" } });
  const gib = profileFromItem(stored({ resources: { ...stored().resources, time_min: 120, mem_mib: 8192 } }));
  expect([gib.hours, gib.minutes, gib.mem, gib.memUnit]).toEqual(["2", "0", "8", "GiB"]);
});

test("a compute: SLURM sends its account, local its caps; software and Apptainer arguments as typed", () => {
  const slurm = toComputeBody(compute({ account: "lab-a", software: ["apptainer"], apptainerArgs: "--bind /g" }));
  expect(slurm.errors).toEqual({});
  expect(slurm.body).toEqual({
    ...{ name: "embl-slurm", label: null, executor: "slurm", slurm: { account: "lab-a" }, local: null },
    ...{ software: ["apptainer"], apptainer_args: "--bind /g" },
  });
  const local = toComputeBody(compute({ executor: "local", cpus: "2", localMem: "8" }));
  expect(local.body).toMatchObject({ slurm: null, local: { cpus: 2, mem_mib: 8192 } });
  expect(toComputeBody(compute({ account: "-x" })).errors["slurm.account"]).toBeDefined();
  expect(toComputeBody(compute({ executor: "local", cpus: "257" })).errors["local.cpus"]).toMatch(/1 to 256/);
  expect(toComputeBody(compute({ apptainerArgs: "--bind\rtouch x" })).errors["apptainer_args"]).toMatch(/control character/);
  expect(toComputeBody(compute({ apptainerArgs: "a".repeat(501) })).errors["apptainer_args"]).toMatch(/500/);
});

test("a compute reads back into the form; one without the software field keeps both methods", () => {
  const item: Compute = {
    ...{ name: "embl-slurm", label: "EMBL", executor: "slurm", slurm: { account: "lab-a" }, local: null },
    ...{ software: ["conda"], apptainer_args: "--bind /g", builtin: false, usable: true, unusable_reason: null, etag: '"c"' },
  };
  const back = computeFromItem(item);
  expect([back.account, back.software, back.apptainerArgs]).toEqual(["lab-a", ["conda"], "--bind /g"]);
  expect(computeFromItem({ ...item, software: undefined as unknown as Compute["software"] }).software).toEqual(["conda", "apptainer"]);
});
