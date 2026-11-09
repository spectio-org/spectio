// The run's Environment fact and Executor row, and Resume's environment line (FU-P3-86g; ui-spec
// §4.8.1 "Run detail" and "Resume"; boards LiteRunDetail and LiteStatesRun): from the run's own
// snapshot, never GET /version.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, VERSION, app, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const NONE = { name: null, label: null, executor: null, slurm: null, local: null };
const MYLAB = {
  ...{ name: "mylab-long", label: "Long jobs, mylab", executor: "slurm", local: null, state: "recorded" },
  slurm: { partition: "htc", account: "mylab", time_min: 120, mem_mib: 8192 },
};

function show(environment: unknown, over: Record<string, unknown> = {}, executor = "local") {
  serve({
    "/api/v1/version": { ...VERSION, executor }, // the server's kind: never the run's
    [`${URL_}/processes`]: { items: [] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/logs`]: () => new Response(""),
    [`${URL_}/results`]: { root: "/g/out", path: "", exists: false, entries: [], truncated: false, reports: [] },
    [`${URL_}:relaunch`]: () => json(500, { title: "unexpected" }),
    [URL_]: { ...DETAIL, ...run({ environment, ...over }) },
  });
  app(`/runs/${ID}`);
}
const fact = async (name: string) => (await screen.findByText(name, { selector: "dt" })).nextElementSibling!;

test("a recorded environment: its name, executor badge and summary line; Executor reads the run", async () => {
  show(MYLAB);
  const env = await fact("Environment");
  expect(env).toHaveTextContent("mylab-long · SLURM");
  expect(env).toHaveTextContent("partition htc · SLURM account mylab · 2 h per job · 8 GiB per job");
  expect(await fact("Executor")).toHaveTextContent(/^SLURM$/);
});

test("a built-in shows its label; a Snakemake run with a profile says the profile owns the resources", async () => {
  show(
    { ...MYLAB, name: "slurm", label: "SLURM (from spectio init)" },
    { profiles: ["slurm"], workflow: { engine: "snakemake", engine_version: "9", location: "/g/p", name: "p", version: null } },
  );
  const env = await fact("Environment");
  expect(env).toHaveTextContent("SLURM (from spectio init) · SLURM");
  expect(env).toHaveTextContent("resources and partition from the profile slurm (this environment's are not passed)");
});

test("not recorded", async () => {
  show({ ...NONE, state: "not_recorded" });
  expect(await fact("Environment")).toHaveTextContent(/^not recorded$/);
  expect(await fact("Executor")).toHaveTextContent(/^not recorded$/);
});

test("cannot be read", async () => {
  show({ ...NONE, state: "not_readable" });
  expect(await fact("Environment")).toHaveTextContent(/^cannot be read$/);
  expect(await fact("Executor")).toHaveTextContent(/^cannot be read$/);
});

test("a run started from a terminal has no Environment row", async () => {
  show(null, { origin: "cli-observed" });
  expect(await fact("Executor")).toHaveTextContent(/^not recorded$/);
  expect(screen.queryByText("Environment", { selector: "dt" })).toBeNull();
});

const failed = { state: "failed", ended_at: "2026-10-31T08:00:00+00:00", actions: { resume: { allowed: true, reason: null } } };
const head = { session: "s", node: "login1", alive: false, exit_code: 1, checked: true };

test("Resume says where it runs: as before, or on the server's default", async () => {
  show(MYLAB, { ...failed, head });
  await userEvent.click(await screen.findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(within(dialog).getByText("Runs on mylab-long as before.")).toBeInTheDocument();
});

test("Resume of a run with no recorded environment names the server's default", async () => {
  show({ ...NONE, state: "not_recorded" }, { ...failed, head });
  await userEvent.click(await screen.findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(within(dialog).getByText("This run has no recorded environment: it resumes on the server's default (local).")).toBeInTheDocument();
});

test("Resume of a run whose environment cannot be read waits, with why", async () => {
  show({ ...NONE, state: "not_readable" }, { ...failed, head });
  const resume = await screen.findByRole("button", { name: "Resume" });
  expect(resume).toHaveAttribute("aria-disabled", "true");
  expect(resume).toHaveAccessibleDescription("Its recorded environment cannot be read.");
});

test("Resume of an uncapped local run on a SLURM server says it gets the login node's limits", async () => {
  const uncapped = { ...NONE, name: "local", label: "This machine", executor: "local", local: { cpus: null, mem_mib: null }, state: "recorded" };
  show(uncapped, { ...failed, head }, "slurm");
  await userEvent.click(await screen.findByRole("button", { name: "Resume" }));
  const dialog = await screen.findByRole("dialog", { name: "Resume this run?" });
  expect(within(dialog).getByText("It runs with the login node's limits (2 CPUs, 8 GiB).")).toBeInTheDocument();
});
