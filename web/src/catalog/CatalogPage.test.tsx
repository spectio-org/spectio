// The Catalog pages (FU-P3-87d; ui-spec §4.7.1; boards LiteCatalog, LiteCatalogEntry,
// LiteCatalogStates, MLiteCatalog): the list and its states, Delete and its focus, and the form.
import { render, screen, waitFor, within } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import type { CatalogList as List } from "../api";
import { VERSION, app, json, serve, stubStream, viewport } from "../testing";
import { providerProps } from "../shell/theme";
import { CatalogList } from "./CatalogList";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/catalog";
const SLURM = { ...VERSION, executor: "slurm" };
const PATH = "/home/amartin/.spectio/catalog.toml";
const entry = (name: string, over: Record<string, unknown> = {}) => ({
  name,
  label: null,
  engine: "nextflow",
  location: "nf-core/rnaseq",
  revision: "3.27.0",
  profile: null,
  params_file: null,
  etag: `"${name}-1"`,
  ...over,
});
const list = (items: unknown[], state = "ok", detail: string | null = null) => ({ items, file: { path: PATH, state, detail } });
const ITEMS = [
  entry("liver-qc", { label: "Liver time course QC", engine: "snakemake", location: "/g/demo-lab/pipelines/liver-tc-qc", revision: null, profile: "slurm", params_file: "config/liver.yaml" }),
  entry("rnaseq-test", { profile: "test", params_file: "conf/test.yaml" }),
  entry("strandseq-qc", { label: "Strand-seq QC", engine: "snakemake", location: "ssh://git@git.demo-lab.org/mylab/strandseq-qc.git", revision: "v1.4.0" }),
];

test("/catalog: Launch is marked, the head reads Launch › Catalog, rows name their actions", async () => {
  serve({ [API]: list(ITEMS), "/api/v1/version": SLURM });
  app("/catalog");
  const row = (await screen.findByRole("heading", { name: "Liver time course QC" })).closest("article")!;
  expect(row).toHaveTextContent("liver-qc");
  expect(row).toHaveTextContent("Snakemake");
  expect(row).toHaveTextContent("/g/demo-lab/pipelines/liver-tc-qc");
  expect(row).toHaveTextContent("profile slurm · parameters from config/liver.yaml");
  expect(within(row).getByRole("link", { name: "Edit liver-qc" })).toHaveAttribute("href", "/catalog/liver-qc");
  expect(within(row).getByRole("button", { name: "Delete liver-qc" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "rnaseq-test" }).closest("article")).toHaveTextContent("@3.27.0");
  expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(["Liver time course QC", "rnaseq-test", "Strand-seq QC"]);
  expect(screen.getByText(/^Saved in/)).toHaveTextContent(`Saved in ${PATH}`);
  expect(screen.getByRole("link", { name: "Add pipeline" })).toHaveAttribute("href", "/catalog/new");
  expect(screen.getByRole("link", { name: "Back to Launch" })).toHaveAttribute("href", "/launch");
  const nav = screen.getByRole("navigation", { name: "Main" });
  expect(within(nav).getByRole("link", { name: "Launch" })).toHaveAttribute("aria-current", "page");
  expect(within(nav).getAllByRole("link")).toHaveLength(4); // no NAV item for the catalog
  const crumbs = screen.getByRole("navigation", { name: "Breadcrumb" });
  expect(within(crumbs).getByRole("link", { name: "Launch" })).toHaveAttribute("href", "/launch");
  expect(within(crumbs).getByText("Catalog")).toHaveAttribute("aria-current", "page");
});

test("loading, then an empty catalog", async () => {
  let answer: (r: Response) => void = () => {};
  serve({ [API]: () => new Promise<Response>((r) => (answer = r)) });
  app("/catalog");
  expect(await screen.findByText("Loading the catalog…")).toBeInTheDocument();
  answer(json(200, list([], "missing")));
  expect(await screen.findByText(/^Your catalog is empty\. Add pipeline saves a path or a repository/)).toBeInTheDocument();
  expect(screen.queryByText("Loading the catalog…")).toBeNull();
});

test("a list error says so, with Retry", async () => {
  let fail = true;
  serve({ [API]: () => (fail ? json(500, { title: "Server error", detail: "boom" }) : json(200, list(ITEMS))) });
  app("/catalog");
  expect(await screen.findByRole("alert")).toHaveTextContent("The catalog could not be read.");
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByRole("heading", { name: "rnaseq-test" })).toBeInTheDocument();
});

test.each([
  ["refused", "group-writable: chmod 600", `Spectio does not read ${PATH}: group-writable: chmod 600. Fix it with the command shown`, /waits until the catalog file can be read/],
  ["invalid", "Expected (at line 7, column 12)", `${PATH} has a mistake: Expected (at line 7, column 12). No pipeline is listed until it is fixed.`, /waits until the mistake in the file is fixed/],
  ["unreachable", null, "Spectio cannot read the cluster's files right now. Your catalog is not listed until they answer.", /waits until the cluster's files can be read/],
])("the file %s: its line, Add pipeline waits with its reason", async (state, detail, line, why) => {
  serve({ [API]: list([], state, detail) });
  app("/catalog");
  expect(await screen.findByText((_, el) => el?.classList.contains("sp-note") === true && el.textContent!.startsWith(line))).toBeInTheDocument();
  const add = screen.getByRole("button", { name: "Add pipeline" });
  expect(add).toHaveAttribute("aria-disabled", "true");
  expect(add).toHaveAccessibleDescription(why);
  expect(screen.queryByText(/Your catalog is empty/)).toBeNull();
  if (state === "unreachable") expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

test("/catalog/<name> that is gone: No entry named <name>, with a link to the list", async () => {
  serve({ [`${API}/wgs-2024`]: () => json(404, { type: "/problems/not-found", title: "Not found", detail: "No such catalog entry." }) });
  app("/catalog/wgs-2024");
  expect(await screen.findByRole("heading", { level: 1, name: "No entry named wgs-2024" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Your catalog" })).toHaveAttribute("href", "/catalog");
});

test("Delete asks first; after it, focus on the next row's heading and a polite line", async () => {
  let items = [...ITEMS];
  serve({
    [`${API}/rnaseq-test`]: (_u: URL, init?: RequestInit) => {
      expect(init?.method).toBe("DELETE");
      expect(new Headers(init?.headers).get("if-match")).toBe('"rnaseq-test-1"');
      items = items.filter((i) => i.name !== "rnaseq-test");
      return new Response(null, { status: 204 });
    },
    [API]: () => json(200, list(items)),
  });
  app("/catalog");
  await userEvent.click(await screen.findByRole("button", { name: "Delete rnaseq-test" }));
  const dialog = await screen.findByRole("dialog", { name: "Delete rnaseq-test?" });
  expect(dialog).toHaveTextContent("Runs launched from it keep their pipeline.");
  await waitFor(() => expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus());
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete rnaseq-test" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "Strand-seq QC" })).toHaveFocus());
  expect(screen.getByText("Deleted rnaseq-test")).toHaveAttribute("role", "status");
});

test.each([
  [412, "/problems/etag-mismatch", "This entry changed in another tab."],
  [409, "/problems/catalog-file-changed", "The file changed on disk since this page read it."],
  [409, "/problems/catalog-file-unusable", "The catalog file cannot be changed right now."],
])("a %i %s in the Delete dialog is shown in place with Reload", async (status, type, words) => {
  serve({ [`${API}/rnaseq-test`]: () => json(status, { type, title: "x", detail: "x" }), [API]: list(ITEMS) });
  app("/catalog");
  await userEvent.click(await screen.findByRole("button", { name: "Delete rnaseq-test" }));
  const dialog = await screen.findByRole("dialog");
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete rnaseq-test" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent(words);
  expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
});

test("Add pipeline: focus on the heading, Revision once Pipeline is a repository, Save posts, focus on the saved row", async () => {
  const bodies: unknown[] = [];
  let items: unknown[] = [];
  serve({
    [API]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list(items));
      const body = JSON.parse(String(init.body));
      bodies.push(body);
      if (bodies.length === 1) return json(409, { type: "/problems/catalog-entry-exists", title: "x", detail: "A catalog entry named rnaseq-test exists." });
      items = [entry(body.name, body)];
      return json(201, items[0]);
    },
  });
  app("/catalog/new");
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Add pipeline" })).toHaveFocus());
  await userEvent.type(screen.getByLabelText("Name"), "rnaseq-test");
  expect(screen.queryByLabelText(/^Revision/)).toBeNull();
  await userEvent.type(screen.getByLabelText("Pipeline"), "nf-core/rnaseq");
  const save = screen.getByRole("button", { name: "Save" });
  expect(save).toHaveAttribute("aria-disabled", "true");
  expect(save).toHaveAccessibleDescription("Fix Revision first");
  await userEvent.type(screen.getByLabelText(/^Revision/), "3.27.0");
  await userEvent.type(screen.getByLabelText("Default profile (optional)"), "test");
  await userEvent.type(screen.getByLabelText("Params file (optional)"), "conf/test.yaml");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("An entry named rnaseq-test exists")).toBeInTheDocument();
  expect(bodies[0]).toEqual({
    name: "rnaseq-test", label: null, engine: "nextflow", location: "nf-core/rnaseq", revision: "3.27.0", profile: "test", params_file: "conf/test.yaml",
  });
  await userEvent.clear(screen.getByLabelText("Name"));
  await userEvent.type(screen.getByLabelText("Name"), "rnaseq-2");
  await userEvent.click(screen.getByRole("radio", { name: "Snakemake" }));
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "rnaseq-2" })).toHaveFocus());
  expect(bodies[1]).toMatchObject({ name: "rnaseq-2", engine: "snakemake" });
  expect(screen.getByText("Saved rnaseq-2")).toHaveAttribute("role", "status");
});

test("the form's rules: a path takes no revision, a bad params file, and a server 422 on its field", async () => {
  serve({
    [API]: (_u: URL, init?: RequestInit) =>
      init?.method === "POST"
        ? json(422, { type: "/problems/validation-failed", title: "x", detail: "x", errors: [{ field: "location", message: "not an absolute path or a Git location" }] })
        : json(200, list([])),
  });
  app("/catalog/new");
  await userEvent.type(await screen.findByLabelText("Name"), "new");
  expect(screen.getByText("new is a reserved name")).toBeInTheDocument();
  await userEvent.clear(screen.getByLabelText("Name"));
  await userEvent.type(screen.getByLabelText("Name"), "liver-qc");
  await userEvent.type(screen.getByLabelText("Pipeline"), "/g/demo-lab/pipelines/liver-tc-qc");
  expect(screen.queryByLabelText(/^Revision/)).toBeNull();
  await userEvent.type(screen.getByLabelText("Params file (optional)"), "../x.txt");
  expect(screen.getByText(/A path inside the pipeline: no '\.\.' and no leading '\/'/)).toBeInTheDocument();
  await userEvent.clear(screen.getByLabelText("Params file (optional)"));
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByText("not an absolute path or a Git location")).toBeInTheDocument();
  expect(screen.getByLabelText("Pipeline")).toHaveAttribute("aria-invalid", "true");
});

test("Edit: Name is read only, PUT carries If-Match, a 412 shows Reload; Cancel returns focus to Edit", async () => {
  const sent: RequestInit[] = [];
  serve({
    [`${API}/rnaseq-test`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "PUT") return json(200, ITEMS[1]);
      sent.push(init);
      return json(412, { type: "/problems/etag-mismatch", title: "x", detail: "x" });
    },
    [API]: list(ITEMS),
  });
  app("/catalog");
  await userEvent.click(await screen.findByRole("link", { name: "Edit rnaseq-test" }));
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "rnaseq-test" })).toHaveFocus());
  expect(screen.getByLabelText("Name")).toHaveAttribute("readonly");
  expect(screen.getByText(/comments in it are not kept/)).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Label (optional)"), "RNA-seq test");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This entry changed in another tab.");
  expect(screen.getByRole("button", { name: "Reload" })).toHaveAccessibleDescription("Reload discards your changes");
  expect(new Headers(sent[0].headers).get("if-match")).toBe('"rnaseq-test-1"');
  expect(JSON.parse(String(sent[0].body))).toMatchObject({ name: "rnaseq-test", label: "RNA-seq test" });
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "Edit rnaseq-test" })).toHaveFocus());
});

test("phone: a row is a link to the entry's page, which stacks Delete under the form", async () => {
  viewport(390);
  serve({ [`${API}/rnaseq-test`]: ITEMS[1], [API]: list(ITEMS) });
  app("/catalog");
  const link = await screen.findByRole("link", { name: "rnaseq-test" });
  expect(link).toHaveAttribute("href", "/catalog/rnaseq-test");
  expect(screen.queryByRole("button", { name: "Delete rnaseq-test" })).toBeNull();
  await userEvent.click(link);
  expect(await screen.findByRole("button", { name: "Delete rnaseq-test" })).toBeInTheDocument();
});

test("the list is shared: with onEdit, Edit is a button that calls it (the Manage dialog, FU-P3-87e)", async () => {
  const onEdit = vi.fn();
  render(
    <MantineProvider {...providerProps}>
      <CatalogList data={list(ITEMS) as List} onEdit={onEdit} onChanged={() => {}} onReload={() => {}} />
    </MantineProvider>,
  );
  await userEvent.click(screen.getByRole("button", { name: "Edit rnaseq-test" }));
  expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ name: "rnaseq-test" }));
});
