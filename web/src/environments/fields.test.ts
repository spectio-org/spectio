import { expect, test } from "vitest";
import type { EnvironmentItem } from "../api";
import { type Draft, EMPTY, fromItem, summary, toBody } from "./fields";

const draft = (over: Partial<Draft> = {}): Draft => ({ ...EMPTY, name: "mylab-long", ...over });

test("hours and minutes become time_min; both empty is unset; 0 and 0 is an error", () => {
  expect(toBody(draft({ hours: "2", minutes: "30" })).body?.slurm?.time_min).toBe(150);
  expect(toBody(draft({ hours: "2", minutes: "" })).body?.slurm?.time_min).toBe(120);
  expect(toBody(draft({ hours: "", minutes: "45" })).body?.slurm?.time_min).toBe(45);
  expect(toBody(draft()).body?.slurm?.time_min).toBeNull();
  expect(toBody(draft({ hours: "0", minutes: "0" })).errors).toEqual({ "slurm.time_min": "At least 1 minute" });
  expect(toBody(draft({ hours: "721" })).errors["slurm.time_min"]).toMatch(/Hours 0 to 720/);
  expect(toBody(draft({ hours: "720", minutes: "1" })).errors["slurm.time_min"]).toMatch(/720 h/);
  expect(toBody(draft({ minutes: "60" })).errors["slurm.time_min"]).toMatch(/minutes 0 to 59/);
  expect(toBody(draft({ hours: "1.5" })).errors["slurm.time_min"]).toBeDefined();
});

test("GiB becomes mem_mib, rounded to MiB, with one decimal at most", () => {
  expect(toBody(draft({ mem: "1.5", memUnit: "GiB" })).body?.slurm?.mem_mib).toBe(1536);
  expect(toBody(draft({ mem: "8", memUnit: "GiB" })).body?.slurm?.mem_mib).toBe(8192);
  expect(toBody(draft({ mem: "500", memUnit: "MiB" })).body?.slurm?.mem_mib).toBe(500);
  expect(toBody(draft({ mem: "1.25", memUnit: "GiB" })).errors["slurm.mem_mib"]).toBeDefined();
  expect(toBody(draft({ mem: "1.5", memUnit: "MiB" })).errors["slurm.mem_mib"]).toBeDefined();
  expect(toBody(draft({ mem: "0", memUnit: "MiB" })).errors["slurm.mem_mib"]).toBeDefined();
  expect(toBody(draft({ mem: "4097", memUnit: "GiB" })).errors["slurm.mem_mib"]).toBeDefined();
});

test("the field rules: name, reserved names, partition, account, CPUs, profiles", () => {
  expect(toBody(draft({ name: "" })).errors.name).toMatch(/Lowercase letters/);
  expect(toBody(draft({ name: "Mylab" })).errors.name).toMatch(/Lowercase letters/);
  expect(toBody(draft({ name: "a".repeat(33) })).errors.name).toBeDefined();
  expect(toBody(draft({ name: "slurm" })).errors.name).toBe("slurm is a built-in name");
  expect(toBody(draft({ name: "new" })).errors.name).toBe("new is a reserved name");
  expect(toBody(draft({ partition: "htc long" })).errors["slurm.partition"]).toBeDefined();
  expect(toBody(draft({ account: "-x" })).errors["slurm.account"]).toBeDefined();
  expect(toBody(draft({ label: "x".repeat(81) })).errors.label).toBeDefined();
  expect(toBody(draft({ nextflow: "a,b" })).errors["profiles.nextflow"]).toBeDefined();
  const local = draft({ executor: "local", cpus: "257", localMem: "8", localUnit: "GiB" });
  expect(toBody(local).errors["local.cpus"]).toMatch(/1 to 256/);
});

test("a valid draft is the POST body, with the other executor's values null", () => {
  const { body, errors } = toBody(
    draft({ label: "Long jobs, mylab", partition: "htc", account: "mylab", hours: "48", mem: "32", memUnit: "GiB", nextflow: "singularity" }),
  );
  expect(errors).toEqual({});
  expect(body).toEqual({
    name: "mylab-long",
    label: "Long jobs, mylab",
    executor: "slurm",
    slurm: { partition: "htc", account: "mylab", time_min: 2880, mem_mib: 32768 },
    local: null,
    profiles: { nextflow: "singularity", snakemake: null },
  });
  const local = toBody(draft({ executor: "local", cpus: "2", localMem: "8", localUnit: "GiB" })).body;
  expect(local?.slurm).toBeNull();
  expect(local?.local).toEqual({ cpus: 2, mem_mib: 8192 });
});

const item = (over: Partial<EnvironmentItem> = {}): EnvironmentItem => ({
  name: "mylab-long",
  label: null,
  executor: "slurm",
  builtin: false,
  default: false,
  usable: true,
  unusable_reason: null,
  slurm: { partition: "htc", account: "mylab", time_min: 150, mem_mib: 1536 },
  local: null,
  profiles: { nextflow: null, snakemake: null },
  etag: '"e"',
  ...over,
});

test("an item reads back into the form: hours and minutes, GiB when it divides by 1024", () => {
  const back = fromItem(item());
  expect([back.hours, back.minutes, back.mem, back.memUnit]).toEqual(["2", "30", "1536", "MiB"]);
  const gib = fromItem(item({ slurm: { partition: null, account: null, time_min: 120, mem_mib: 8192 } }));
  expect([gib.hours, gib.minutes, gib.mem, gib.memUnit, gib.partition]).toEqual(["2", "0", "8", "GiB", ""]);
});

test("the summary line, in words; an unset value is left out", () => {
  expect(summary(item(), "login1", "slurm")).toBe("partition htc · SLURM account mylab · 2 h 30 min per job · 1536 MiB per job");
  expect(summary(item({ slurm: { partition: null, account: null, time_min: 120, mem_mib: 8192 } }), "login1", "slurm")).toBe(
    "2 h per job · 8 GiB per job",
  );
  expect(summary(item({ slurm: { partition: null, account: null, time_min: null, mem_mib: null } }), "login1", "slurm")).toBe(
    "SLURM's defaults for your account",
  );
  const local = item({ executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 } });
  expect(summary(local, "login1", "slurm")).toBe("on login1 (the login node) · at most 2 CPUs and 8 GiB");
  expect(summary(item({ executor: "local", slurm: null, local: { cpus: null, mem_mib: null } }), "pc", "local")).toBe(
    "this machine · no limit",
  );
});

test("one CPU is singular (DW-P3B11-02)", () => {
  const one = item({ executor: "local", slurm: null, local: { cpus: 1, mem_mib: null } });
  expect(summary(one, "login1", "slurm")).toBe("on login1 (the login node) · at most 1 CPU");
});
