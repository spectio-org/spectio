// Run detail's Default resources and Extra config file facts, and the kept file's sheet
// (FU-P3-110d; ui-spec §4.6 "Run detail facts" and the drawn layout of FU-P3-110c; api §5.7;
// board LiteRunDetail). GET /runs/{id}/config-file is fetched only when View is pressed.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());
beforeEach(() => {
  let last = "";
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: async (text: string) => void (last = text), readText: async () => last },
  });
});
afterEach(() => {
  Reflect.deleteProperty(navigator, "clipboard");
});

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const SHA = "4f1c9a0b7e2d".padEnd(64, "0");
const LONG = {
  name: "mylab-long",
  label: null,
  executor: "slurm",
  slurm: { partition: "long", account: "mylab", time_min: 2880, mem_mib: 32768 },
  local: null,
  state: "recorded",
};
const KEPT = { path: "/home/amartin/configs/lab-tweaks.config", kept_as: "extra.config", sha256: SHA, size: 3174, includes: false, state: "recorded" };
const RESOURCES = { cpus: 8, mem_mib: 65536, time_min: 720, state: "recorded" };
const TEXT = "process {\n  withName: 'STAR_ALIGN' { memory = 96.GB }\n}\n";

function detail(over: Record<string, unknown>, file?: () => Response) {
  return serve({
    [`${URL_}/processes`]: { items: [] },
    [`${URL_}/stages`]: { items: [] },
    [`${URL_}/logs`]: () => new Response(""),
    [`${URL_}/results`]: { root: "/g/out", path: "", exists: false, entries: [], truncated: false, reports: [] },
    [`${URL_}/config-file`]: file ?? (() => new Response(TEXT, { headers: { "content-type": "text/plain; charset=utf-8", etag: `"${SHA}"` } })),
    [URL_]: { ...DETAIL, ...run({ environment: LONG }), default_resources: null, config_file: null, ...over },
  });
}
const facts = async () => {
  await screen.findByRole("heading", { level: 1 });
  return screen.getByRole("region", { name: /^Facts/ });
};
const fact = (name: string) => within(document.querySelector(".sp-facts") as HTMLElement).getByText(name, { selector: "dt" }).nextElementSibling as HTMLElement;

test("a run that set neither has no rows", async () => {
  detail({});
  app(`/runs/${ID}`);
  const f = await facts();
  expect(within(f).queryByText("Default resources")).toBeNull();
  expect(within(f).queryByText("Extra config file")).toBeNull();
});

test("Default resources: the values, and what they replaced in the run's environment", async () => {
  detail({ default_resources: RESOURCES });
  app(`/runs/${ID}`);
  await facts();
  expect(fact("Default resources")).toHaveTextContent("8 CPUs · 64 GiB · 12 h per task");
  expect(fact("Default resources")).toHaveTextContent("Set at Launch, in place of mylab-long's 48 h and 32 GiB · processes that set their own keep them");
});

test("Default resources on Snakemake with keys left out: worded from the environment, or the pipeline's default", async () => {
  const env = { ...LONG, slurm: { ...LONG.slurm, mem_mib: null } };
  detail({ ...run({ environment: env, workflow: { ...run().workflow, engine: "snakemake" } }), default_resources: { cpus: null, mem_mib: 16384, time_min: null, state: "recorded" } });
  app(`/runs/${ID}`);
  await facts();
  expect(fact("Default resources")).toHaveTextContent("16 GiB per task · time: 48 h from mylab-long");
  expect(fact("Default resources")).toHaveTextContent("Set at Launch · rules that set their own keep them");
  expect(fact("Default resources")).not.toHaveTextContent("in place of");
});

test("a key left out: the environment's value, or none set when it has none", async () => {
  detail({
    ...run({ environment: { ...LONG, slurm: { ...LONG.slurm, time_min: null } } }),
    default_resources: { cpus: 2, mem_mib: null, time_min: null, state: "recorded" },
  });
  app(`/runs/${ID}`);
  await facts();
  expect(fact("Default resources")).toHaveTextContent("2 CPUs per task · memory: 32 GiB from mylab-long · time: none set, the pipeline's default");
});

test("the environment's record not readable: the values alone", async () => {
  detail({ ...run({ environment: { ...LONG, slurm: null, state: "not_readable" } }), default_resources: RESOURCES });
  app(`/runs/${ID}`);
  await facts();
  expect(fact("Default resources")).toHaveTextContent("8 CPUs · 64 GiB · 12 h per task");
  expect(fact("Default resources")).toHaveTextContent("Set at Launch · processes that set their own keep them");
});

test("not readable: the words, and no path, hash or buttons", async () => {
  const blank = { path: null, kept_as: null, sha256: null, size: null, includes: null, state: "not_readable" };
  detail({ default_resources: { cpus: null, mem_mib: null, time_min: null, state: "not_readable" }, config_file: blank });
  app(`/runs/${ID}`);
  await facts();
  expect(fact("Default resources")).toHaveTextContent("Not readable");
  expect(fact("Default resources")).toHaveTextContent("The run's record of them is damaged; the run itself is not affected.");
  expect(fact("Extra config file")).toHaveTextContent("Not readable");
  expect(fact("Extra config file")).toHaveTextContent("The run's record of it is damaged");
  expect(within(fact("Extra config file")).queryByRole("button")).toBeNull();
});

test("Extra config file: path, kept as, size and hash; Copy SHA-256 copies it whole and says so; the file is not fetched", async () => {
  const mock = detail({ config_file: { ...KEPT, includes: true } });
  app(`/runs/${ID}`);
  await facts();
  const f = fact("Extra config file");
  expect(within(f).getByText(KEPT.path)).toHaveClass("sp-mono");
  expect(f).toHaveTextContent("kept as extra.config · 3.1 KiB · SHA-256 4f1c9a0b7e2d…");
  expect(f).toHaveTextContent("It loads other files with includeConfig; those are not kept with the run.");
  await userEvent.click(within(f).getByRole("button", { name: "Copy SHA-256 of extra.config" }));
  expect(await within(f).findByRole("status")).toHaveTextContent("Copied the SHA-256 of extra.config");
  expect(await navigator.clipboard.readText()).toBe(SHA);
  expect(fetched(mock).some((u) => u.endsWith("/config-file"))).toBe(false);
});

test("View opens a modal sheet that reads the kept copy; Escape returns focus to View", async () => {
  const mock = detail({ config_file: KEPT });
  app(`/runs/${ID}`);
  await facts();
  const view = within(fact("Extra config file")).getByRole("button", { name: "View extra.config" });
  expect(view).toHaveAttribute("aria-haspopup", "dialog");
  await userEvent.click(view);
  const sheet = await screen.findByRole("dialog", { name: "extra.config" });
  expect(sheet).toHaveAttribute("aria-modal", "true");
  expect(sheet).toHaveTextContent("/home/amartin/configs/lab-tweaks.config · 3.1 KiB");
  expect((await within(sheet).findByLabelText("Contents of extra.config")).textContent).toBe(TEXT);
  expect(sheet).not.toHaveTextContent("Changed since the launch");
  expect(fetched(mock).filter((u) => u.endsWith("/config-file"))).toHaveLength(1);
  await userEvent.keyboard("{Escape}");
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  await waitFor(() => expect(view).toHaveFocus());
});

test("the sheet says when the kept copy changed since the launch", async () => {
  detail({ config_file: KEPT }, () => new Response("edited\n", { headers: { etag: `"${"9".repeat(64)}"` } }));
  app(`/runs/${ID}`);
  await facts();
  await userEvent.click(within(fact("Extra config file")).getByRole("button", { name: "View extra.config" }));
  const sheet = await screen.findByRole("dialog", { name: "extra.config" });
  expect(await within(sheet).findByText(/^Changed since the launch: the kept copy's SHA-256 is not the one recorded\./)).toBeInTheDocument();
  expect(within(sheet).getByLabelText("Contents of extra.config").textContent).toBe("edited\n");
});

test("the kept copy gone (404), then a 503 with Retry", async () => {
  let answer = 404;
  detail({ config_file: KEPT }, () =>
    answer === 200
      ? new Response(TEXT, { headers: { etag: `"${SHA}"` } })
      : json(answer, { title: answer === 404 ? "Not found" : "File system not answering", detail: "x" }),
  );
  app(`/runs/${ID}`);
  await facts();
  const view = within(fact("Extra config file")).getByRole("button", { name: "View extra.config" });
  await userEvent.click(view);
  let sheet = await screen.findByRole("dialog", { name: "extra.config" });
  expect(await within(sheet).findByRole("alert")).toHaveTextContent("The kept copy of extra.config is not in the run directory any more.");
  await userEvent.click(within(sheet).getByRole("button", { name: "Close" }));
  await waitFor(() => expect(view).toHaveFocus());
  answer = 503;
  await userEvent.click(view);
  sheet = await screen.findByRole("dialog", { name: "extra.config" });
  expect(await within(sheet).findByRole("alert")).toHaveTextContent("The run directory did not answer; try again.");
  answer = 200;
  await userEvent.click(within(sheet).getByRole("button", { name: "Retry" }));
  expect((await within(sheet).findByLabelText("Contents of extra.config")).textContent).toBe(TEXT);
});
