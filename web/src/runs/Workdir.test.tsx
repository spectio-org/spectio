// The work directory of one Nextflow attempt (ui-spec §4.4.1, FU-P3-85e; board LiteWorkdir; api
// §5.3): the results explorer and preview on the attempt's `workdir` routes, with the task's name
// in the h1, the folder page's back link and the title; an HTML file is never opened; a dot name is refused.
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { DETAIL, app, fetched, json, run, serve, stubStream } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const ID = "run_01JBC6Q4ZK7M8N2P3R5S7T9V1W";
const URL_ = `/api/v1/runs/${ID}`;
const WORK = "/scratch/amartin/spectio-runs/run_01JBC6Q4ZK7M8N2P3R5S7T9V1W/work/9d/77c2140f5be3a1c96e04d2b88a7f13";
const API = "/api/v1/tasks/tsk_19/attempts/2/workdir";
const T = "2026-10-31T08:47:00+00:00";
const TASK = { id: "tsk_19", process: "NFCORE:RNASEQ:SUBREAD_FEATURECOUNTS", tag: "S19", name: "SUBREAD_FEATURECOUNTS (S19)", state: "succeeded", stage_id: null, attempt_n: 2, resources: null };
const NAME = "SUBREAD_FEATURECOUNTS (S19)";

const ROOT_LISTING = {
  root: WORK,
  path: "",
  exists: true,
  truncated: false,
  entries: [
    { name: "S19_featurecounts", type: "dir", size: null, mtime: T },
    { name: "S19.featureCounts.txt", type: "file", size: 2048, mtime: T },
    { name: "S19.featureCounts.html", type: "file", size: 90112, mtime: T },
    { name: "S19.markdup.sorted.bam", type: "link_outside", size: null, mtime: T },
  ],
};

function work(answers: Record<string, unknown>) {
  return serve({
    [`${URL_}/tasks`]: { items: [TASK], next: null },
    [URL_]: { ...DETAIL, ...run({ state: "succeeded", name: "rnaseq-2026-10-25" }) },
    ...answers,
  });
}
const query = (a: HTMLElement) => Object.fromEntries(new URL(a.getAttribute("href")!, "http://x").searchParams);
const pathOf = (a: HTMLElement) => new URL(a.getAttribute("href")!, "http://x").pathname;

test("the folder page: h1, back link to the task sheet, 'work directory' crumb, the card, HTML (not opened), the title", async () => {
  const mock = work({ [API]: ROOT_LISTING });
  app(`/runs/${ID}/workdir?task=tsk_19&attempt=2`);
  expect(await screen.findByRole("heading", { level: 1, name: `Work directory · ${NAME} · attempt 2` })).toBeInTheDocument();
  const back = await screen.findByRole("link", { name: `${NAME} · attempt 2` });
  expect(pathOf(back)).toBe(`/runs/${ID}`);
  expect(query(back)).toEqual({ task: "tsk_19", attempt: "2" });
  const bar = screen.getByRole("navigation", { name: "Folder" });
  expect(within(bar).getByText("work directory")).toHaveAttribute("aria-current", "page");
  expect(await screen.findByRole("heading", { level: 2, name: "Work directory · 1 folder, 3 files" })).toBeInTheDocument();
  expect(screen.getByText(`${WORK}/`)).toBeInTheDocument(); // the path bar, as the results root
  const t = screen.getByRole("table", { name: "work directory" });
  const html = within(t).getByRole("link", { name: "S19.featureCounts.html" });
  expect(pathOf(html)).toBe(`/runs/${ID}/workdir/file`); // the preview page, never the report viewer
  expect(query(html)).toEqual({ path: "S19.featureCounts.html", task: "tsk_19", attempt: "2" });
  expect(html.closest("tr")!.querySelector("[data-kind]")).toHaveTextContent("HTML (not opened)");
  const folder = within(t).getByRole("link", { name: "S19_featurecounts" });
  expect(pathOf(folder)).toBe(`/runs/${ID}/workdir`);
  expect(query(folder)).toEqual({ path: "S19_featurecounts", task: "tsk_19", attempt: "2" });
  expect(within(t).getByRole("link", { name: "Download S19.featureCounts.txt" }).getAttribute("href")).toBe(`${API}/raw/S19.featureCounts.txt?download=true`);
  expect(within(t).queryByRole("link", { name: "S19.markdup.sorted.bam" })).toBeNull();
  expect(screen.getByText(/Names that start with a dot are not listed: the job's own files are in the task sheet/)).toBeInTheDocument();
  await waitFor(() => expect(document.title).toBe(`work directory · ${NAME} · rnaseq-2026-10-25 · Spectio`));
  expect(fetched(mock)).toContain(API);
});

test("a subfolder: the crumb's root links back with the task and attempt; the title names the folder", async () => {
  work({ [`${API}?path=S19_featurecounts`]: { ...ROOT_LISTING, path: "S19_featurecounts", entries: [] } });
  app(`/runs/${ID}/workdir?task=tsk_19&attempt=2&path=S19_featurecounts`);
  const bar = await screen.findByRole("navigation", { name: "Folder" });
  const rootLink = await within(bar).findByRole("link", { name: "work directory" });
  expect(pathOf(rootLink)).toBe(`/runs/${ID}/workdir`);
  expect(query(rootLink)).toEqual({ task: "tsk_19", attempt: "2" });
  await waitFor(() => expect(document.title).toBe(`S19_featurecounts · ${NAME} · rnaseq-2026-10-25 · Spectio`));
});

test("a dot name in the URL is refused before any read; 410 says the directory was removed; not there yet", async () => {
  const mock = work({ [`${API}?path=sub`]: () => json(410, { title: "Gone", detail: "the work directory was cleaned" }), [API]: { ...ROOT_LISTING, exists: false, entries: [] } });
  const router = app(`/runs/${ID}/workdir?task=tsk_19&attempt=2&path=.command.env`);
  expect(await screen.findByText("Not a folder of this job's work directory.")).toHaveAttribute("role", "alert");
  expect(fetched(mock).some((u) => u.startsWith(API))).toBe(false);
  await router.navigate({ to: "/runs/$id/workdir", params: { id: ID }, search: { task: "tsk_19", attempt: 2, path: "sub" } });
  expect(await screen.findByText("The work directory was removed")).toBeInTheDocument();
  await router.navigate({ to: "/runs/$id/workdir", params: { id: ID }, search: { task: "tsk_19", attempt: 2 } });
  expect(await screen.findByText("The work directory is not there yet")).toBeInTheDocument();
});

test("the file page of an HTML file: not opened, Download only, back to its folder, the task in the title", async () => {
  const path = "S19.featureCounts.html";
  const mock = work({ [`${API}/stat/${path}`]: { root: WORK, path, name: path, type: "file", size: 90112, mtime: T } });
  app(`/runs/${ID}/workdir/file?task=tsk_19&attempt=2&sort=size&q=S19&path=${path}`);
  expect(await screen.findByText("Spectio does not open HTML from a work directory. Download it to open it.")).toBeInTheDocument();
  expect(screen.getByText(/^HTML \(not opened\) · 88 KiB/)).toBeInTheDocument();
  const downloads = screen.getAllByRole("link", { name: `Download ${path}` });
  for (const d of downloads) expect(d.getAttribute("href")).toBe(`${API}/raw/${path}?download=true`);
  expect(screen.queryByRole("link", { name: /report viewer/ })).toBeNull();
  // CR-P3FU85E-01: back to its folder, with sort, q and focus (ui-spec §4.4.1 Preview)
  const bar = screen.getByRole("navigation", { name: "Folder" });
  const backs = screen.getAllByRole("link", { name: "work directory" }).filter((a) => !bar.contains(a));
  expect(backs).toHaveLength(1);
  expect(pathOf(backs[0])).toBe(`/runs/${ID}/workdir`);
  expect(query(backs[0])).toEqual({ sort: "size", q: "S19", focus: path, task: "tsk_19", attempt: "2" });
  expect(query(within(bar).getByRole("link", { name: "work directory" }))).toEqual({ task: "tsk_19", attempt: "2" });
  await waitFor(() => expect(document.title).toBe(`${path} · ${NAME} · rnaseq-2026-10-25 · Spectio`));
  expect(fetched(mock).some((u) => u.includes("/results"))).toBe(false);
});

test("the file page: a text file read from the workdir text route; a dot name or a 422 is 'Not a file of this job's work directory.'", async () => {
  const path = "S19.featureCounts.txt";
  const mock = work({
    [`${API}/stat/${path}`]: { root: WORK, path, name: path, type: "file", size: 6, mtime: T },
    [`${API}/text/${path}`]: () => new Response("Geneid\n", { headers: { "content-type": "text/plain" } }),
    [`${API}/stat/x.txt`]: () => json(422, { title: "File not allowed", detail: "not served here" }),
  });
  const router = app(`/runs/${ID}/workdir/file?task=tsk_19&attempt=2&path=.command.env`);
  expect(await screen.findByText("Not a file of this job's work directory.")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.startsWith(API))).toBe(false);
  await router.navigate({ to: "/runs/$id/workdir/file", params: { id: ID }, search: { task: "tsk_19", attempt: 2, path } });
  expect(await screen.findByText("Geneid")).toBeInTheDocument();
  expect(fetched(mock).some((u) => u.startsWith(`${API}/text/${path}`))).toBe(true);
  await router.navigate({ to: "/runs/$id/workdir/file", params: { id: ID }, search: { task: "tsk_19", attempt: 2, path: "x.txt" } });
  expect(await screen.findByText("Not a file of this job's work directory.")).toBeInTheDocument();
});

test.each([
  [409, "The run's directory is not reachable", "the runs root /scratch/amartin/spectio-runs is not there"],
  [503, "Spectio cannot read the cluster's files right now", null],
])("CR-P3FU85E-03: the folder page answered %i says '%s', with Retry", async (status, title, detail) => {
  let calls = 0;
  work({ [API]: () => (++calls === 1 ? json(status, { title: "No", detail: "the runs root /scratch/amartin/spectio-runs is not there" }) : json(200, ROOT_LISTING)) });
  app(`/runs/${ID}/workdir?task=tsk_19&attempt=2`);
  const alert = await screen.findByRole("alert");
  expect(within(alert).getByText(title)).toBeInTheDocument();
  if (detail) expect(within(alert).getByText(detail)).toBeInTheDocument();
  fireEvent.click(within(alert).getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("heading", { level: 2, name: "Work directory · 1 folder, 3 files" })).toBeInTheDocument();
});

test("without a task and an attempt the page is not found", async () => {
  work({});
  app(`/runs/${ID}/workdir`);
  expect(await screen.findByRole("heading", { level: 1, name: "Page not found" })).toBeInTheDocument();
});
