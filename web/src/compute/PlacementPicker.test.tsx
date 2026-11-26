// The placement picker in the Profile editor (#401, #408): the filters, the fill of the three
// fields and the fallback to plain fields.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const SLURM = { ...VERSION, executor: "slurm" };
const group = (over: Record<string, unknown> = {}) => ({ nodes: 10, idle: 3, cpus: 64, mem_mib: 262144, features: ["amd"], gpus: [], ...over });
const FACTS = {
  scheduler: "slurm",
  fetched_at: "2026-11-26T10:00:00Z",
  accounts: ["lab-a", "lab-b"],
  partitions: [
    { name: "htc", default: true, allowed: true, max_time_min: 10080, groups: [group({ features: ["amd", "zen4", "avx512"] }), group({ mem_mib: 1048576, features: ["amd"] })] },
    { name: "gpu", default: false, allowed: true, max_time_min: 2880, groups: [group({ features: ["intel"], gpus: [{ type: "H100", count: 4 }] })] },
    { name: "short", default: false, allowed: true, max_time_min: 60, groups: [group({ features: ["amd"] })] },
    { name: "private", default: false, allowed: false, max_time_min: null, groups: [group()] },
  ],
};
const FILE = { path: "/x", state: "ok", detail: null };
const compute = (name: string, executor: string) => ({
  ...{ name, label: null, executor, slurm: null, local: null, software: ["conda", "apptainer"], apptainer_args: "" },
  ...{ builtin: true, usable: true, unusable_reason: null, etag: `"${name}"` },
});
const COMPUTES = { items: [compute("slurm", "slurm"), compute("local", "local")], file: FILE };
const open = async (facts: unknown) => {
  serve({ "/api/v1/version": SLURM, "/api/v1/computes": COMPUTES, "/api/v1/cluster/facts": facts });
  app("/profiles/new");
  await screen.findByRole("textbox", { name: "Partition" });
};
const listed = () => within(screen.queryByRole("list", { name: "Partitions that fit" }) ?? document.body).queryAllByRole("button").map((b) => b.getAttribute("aria-label"));

test("the picker lists the partitions your accounts can use; the others sit behind a toggle", async () => {
  await open(FACTS);
  expect(await screen.findByRole("button", { name: "Use partition htc" })).toBeInTheDocument();
  expect(listed()).toEqual(["Use partition htc", "Use partition gpu", "Use partition short"]);
  const htc = screen.getByRole("button", { name: "Use partition htc" }).closest("li")!;
  expect(htc).toHaveTextContent("Default");
  expect(htc).toHaveTextContent("max time 168 h");
  expect(htc).toHaveTextContent("3 of 10 nodes idle · 64 CPUs · 256 GiB · amd, zen4, avx512");
  await userEvent.click(screen.getByRole("checkbox", { name: "Show partitions your accounts can't use" }));
  expect(listed()).toContain("Use partition private");
});

test("the filters narrow the list: GPU type, memory, time and features", async () => {
  await open(FACTS);
  await screen.findByRole("button", { name: "Use partition htc" });
  await userEvent.type(screen.getByRole("textbox", { name: "Memory per node ≥ GB" }), "512");
  expect(listed()).toEqual(["Use partition htc"]);
  await userEvent.clear(screen.getByRole("textbox", { name: "Memory per node ≥ GB" }));
  await userEvent.type(screen.getByRole("textbox", { name: "Time ≥ h" }), "24");
  expect(listed()).toEqual(["Use partition htc", "Use partition gpu"]);
  await userEvent.click(screen.getByRole("textbox", { name: "GPU" }));
  await userEvent.click(await screen.findByRole("option", { name: "H100" }));
  expect(listed()).toEqual(["Use partition gpu"]);
  await userEvent.click(screen.getByRole("textbox", { name: "GPU" }));
  await userEvent.click(await screen.findByRole("option", { name: "No GPU needed" }));
  await userEvent.click(screen.getByRole("textbox", { name: "CPU features" }));
  await userEvent.click(await screen.findByRole("option", { name: "zen4" }));
  expect(listed()).toEqual(["Use partition htc"]);
  expect(screen.getByText("1 of 4 partitions fit")).toBeInTheDocument();
});

test("choosing a partition fills partition, constraint and gres; the fields stay editable", async () => {
  await open(FACTS);
  await userEvent.click(await screen.findByRole("textbox", { name: "GPU" }));
  await userEvent.click(await screen.findByRole("option", { name: "H100" }));
  await userEvent.click(screen.getByRole("textbox", { name: "CPU features" }));
  await userEvent.click(await screen.findByRole("option", { name: "intel" }));
  await userEvent.click(screen.getByRole("button", { name: "Use partition gpu" }));
  expect(screen.getByRole("textbox", { name: "Partition" })).toHaveValue("gpu");
  expect(screen.getByRole("textbox", { name: "Constraint" })).toHaveValue("intel");
  expect(screen.getByRole("textbox", { name: "GRES" })).toHaveValue("gpu:H100:1");
  expect(screen.getByRole("button", { name: "Use partition gpu" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.type(screen.getByRole("textbox", { name: "Constraint" }), "&avx512");
  expect(screen.getByRole("textbox", { name: "Constraint" })).toHaveValue("intel&avx512");
});

test("two features join with & and any GPU is gpu:1; a filter left empty keeps what was typed", async () => {
  await open({ ...FACTS, partitions: [{ ...FACTS.partitions[0], groups: [group({ features: ["amd", "zen4"], gpus: [{ type: null, count: 1 }] })] }] });
  await userEvent.type(await screen.findByRole("textbox", { name: "GRES" }), "gpu:2");
  await userEvent.click(screen.getByRole("button", { name: "Use partition htc" }));
  expect(screen.getByRole("textbox", { name: "GRES" })).toHaveValue("gpu:2");
  await userEvent.click(screen.getByRole("textbox", { name: "GPU" }));
  await userEvent.click(await screen.findByRole("option", { name: "Any GPU" }));
  await userEvent.click(screen.getByRole("textbox", { name: "CPU features" }));
  await userEvent.click(await screen.findByRole("option", { name: "amd" }));
  await userEvent.click(await screen.findByRole("option", { name: "zen4" })); // a MultiSelect stays open
  await userEvent.click(screen.getByRole("button", { name: "Use partition htc" }));
  expect(screen.getByRole("textbox", { name: "Constraint" })).toHaveValue("amd&zen4");
  expect(screen.getByRole("textbox", { name: "GRES" })).toHaveValue("gpu:1");
});

test.each([
  ["no SLURM on the host", { scheduler: null, fetched_at: null, partitions: [], accounts: [] }],
  ["the request fails", null],
])("%s: today's plain fields, plus constraint and gres, and no picker", async (_why, facts) => {
  serve({ "/api/v1/version": SLURM, "/api/v1/computes": COMPUTES, ...(facts ? { "/api/v1/cluster/facts": facts } : {}) });
  app("/profiles/new");
  for (const name of ["Partition", "Constraint", "GRES"]) {
    expect(await screen.findByRole("textbox", { name })).toBeInTheDocument();
  }
  expect(screen.queryByRole("region", { name: "Find a partition by need" })).toBeNull();
});

test("Save sends the constraint and gres the form holds, under resources", async () => {
  const sent: unknown[] = [];
  const created = (body: unknown) => new Response(JSON.stringify(body), { status: 201, headers: { "content-type": "application/json" } });
  serve({
    "/api/v1/version": SLURM,
    "/api/v1/computes": COMPUTES,
    "/api/v1/execution-profiles": (_u: URL, init?: RequestInit) =>
      init?.method === "POST"
        ? (sent.push(JSON.parse(String(init.body))), created({ name: "gpu-env", etag: '"1"' }))
        : new Response(JSON.stringify({ items: [], file: FILE }), { headers: { "content-type": "application/json" } }),
    "/api/v1/cluster/facts": { scheduler: null, fetched_at: null, partitions: [], accounts: [] },
  });
  app("/profiles/new");
  await userEvent.type(await screen.findByRole("textbox", { name: /^Name/ }), "gpu-env");
  await userEvent.type(screen.getByRole("textbox", { name: "Constraint" }), "a100&avx512");
  await userEvent.type(screen.getByRole("textbox", { name: "GRES" }), "gpu:A100:1");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(sent[0]).toMatchObject({ compute: "slurm", resources: { constraint: "a100&avx512", gres: "gpu:A100:1" } });
});

test("a local compute has no partition, constraint or GRES, and no picker", async () => {
  await open(FACTS);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: "Compute" }), "local");
  expect(screen.queryByRole("textbox", { name: "Partition" })).toBeNull();
  expect(screen.queryByRole("textbox", { name: "GRES" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Find a partition by need" })).toBeNull();
  expect(screen.getByRole("textbox", { name: "CPUs per job" })).toBeInTheDocument();
});

test("a constraint with a space is refused where it is typed", async () => {
  await open({ scheduler: null, fetched_at: null, partitions: [], accounts: [] });
  await userEvent.type(screen.getByRole("textbox", { name: "Constraint" }), "a b");
  expect(await screen.findByText(/no spaces/)).toBeInTheDocument();
});
