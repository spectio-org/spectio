// The Compute pages (FU-P3-86f, #408; ui-spec §4.8.1; boards LiteEnvironments, LiteEnvironmentEdit,
// LiteEnvironmentsStates): the list, Delete with its focus, and the form.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, json, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/computes";
const SLURM = { ...VERSION, executor: "slurm" };
const item = (name: string, over: Record<string, unknown> = {}) => ({
  name,
  label: null,
  executor: "slurm",
  slurm: { account: "mylab" },
  local: null,
  software: ["conda", "apptainer"],
  apptainer_args: "",
  builtin: false,
  usable: true,
  unusable_reason: null,
  etag: `"${name}-1"`,
  ...over,
});
const BUILTINS = [
  item("slurm", { label: "SLURM (from spectio init)", builtin: true, slurm: { account: null }, etag: '"s"' }),
  item("local", { label: "Login node", executor: "local", builtin: true, slurm: null, local: { cpus: 2, mem_mib: 8192 } }),
];
const list = (items: unknown[], state = "ok", detail: string | null = null) => ({
  items,
  file: { path: "/home/amartin/.spectio/computes.toml", state, detail },
});
const MINE = [item("embl-slurm", { label: "EMBL cluster", apptainer_args: "--bind /g" }), item("gpu-box")];

test("Compute and Profiles are in the main navigation, after Launch; the old Environments link lands on Profiles", async () => {
  serve({ [API]: list([...BUILTINS]), "/api/v1/execution-profiles": list([]), "/api/v1/version": SLURM });
  const router = app("/environments");
  const nav = await screen.findByRole("navigation", { name: "Main" });
  await waitFor(() => expect(router.state.location.pathname).toBe("/profiles"));
  expect(within(nav).getAllByRole("link").map((a) => a.textContent).slice(-3)).toEqual(["Launch", "Compute", "Profiles"]);
  expect(within(nav).getByRole("link", { name: "Profiles" })).toHaveAttribute("aria-current", "page");
});

test("the list: one card per compute, badges in words, actions named with the card", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  app("/compute");
  const card = (await screen.findByRole("heading", { name: "EMBL cluster" })).closest("article")!;
  expect(card).toHaveTextContent("embl-slurm");
  expect(card).toHaveTextContent("SLURM account mylab · deploys with conda and apptainer");
  expect(card).toHaveTextContent("Apptainer arguments: --bind /g");
  expect(within(card).getByRole("button", { name: "Delete embl-slurm" })).toBeInTheDocument();
  expect(within(card).queryByText("Default")).toBeNull();
  const builtin = screen.getByRole("heading", { name: "SLURM (from spectio init)" }).closest("article")!;
  expect(within(builtin).getByText("Built-in")).toBeInTheDocument();
  expect(within(builtin).queryByRole("link", { name: /^Edit/ })).toBeNull();
  expect(within(builtin).queryByRole("button", { name: /Delete/ })).toBeNull();
  expect(within(builtin).getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/compute/new?from=slurm");
  expect(screen.getByText(/on login1 \(the login node\) · at most 2 CPUs and 8 GiB/)).toBeInTheDocument();
  expect(screen.getByText(/Saved in/)).toHaveTextContent("Saved in /home/amartin/.spectio/computes.toml");
});

test("only the built-ins: the empty state says what New compute does", async () => {
  serve({ [API]: list([...BUILTINS]), "/api/v1/version": SLURM });
  app("/compute");
  expect(await screen.findByText(/Only the built-in computes so far/)).toBeInTheDocument();
});

test("a name is encoded in the links built from it (SEC-P3FU86F-02)", async () => {
  serve({ [API]: list([...BUILTINS, item("a/b?c")]), "/api/v1/version": SLURM });
  app("/compute");
  expect(await screen.findByRole("link", { name: "Edit a/b?c" })).toHaveAttribute("href", "/compute/a%2Fb%3Fc");
  expect(screen.getByRole("link", { name: "Duplicate a/b?c" })).toHaveAttribute("href", "/compute/new?from=a%2Fb%3Fc");
});

test("an invalid file: its line above the cards, New compute waits with its reason", async () => {
  serve({ [API]: list(BUILTINS, "invalid", "Expected (at line 7, column 13)"), "/api/v1/version": SLURM });
  app("/compute");
  expect(await screen.findByText(/has a mistake: Expected \(at line 7, column 13\)/)).toBeInTheDocument();
  expect(screen.queryByText(/Only the built-in computes so far/)).toBeNull();
  const create = screen.getByRole("button", { name: "New compute" });
  expect(create).toHaveAttribute("aria-disabled", "true");
  expect(create).toHaveAccessibleDescription(/waits until the mistake in the file is fixed/);
  expect(screen.getByRole("button", { name: "Duplicate to edit slurm" })).toHaveAttribute("aria-disabled", "true");
});

test("Delete asks first; after it, focus on the next card's heading and a polite line", async () => {
  let items = [...BUILTINS, ...MINE];
  serve({
    "/api/v1/version": SLURM,
    [`${API}/embl-slurm`]: (_u: URL, init?: RequestInit) => {
      expect(init?.method).toBe("DELETE");
      expect(new Headers(init?.headers).get("if-match")).toBe('"embl-slurm-1"');
      items = items.filter((i) => i.name !== "embl-slurm");
      return new Response(null, { status: 204 });
    },
    [API]: () => json(200, list(items)),
  });
  app("/compute");
  await userEvent.click(await screen.findByRole("button", { name: "Delete embl-slurm" }));
  const dialog = await screen.findByRole("dialog", { name: "Delete embl-slurm?" });
  expect(dialog).toHaveTextContent("Runs that used it keep their settings");
  expect(dialog).toHaveTextContent("a profile uses cannot be deleted");
  await waitFor(() => expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus());
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete embl-slurm" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "gpu-box" })).toHaveFocus());
  expect(screen.getByText("Deleted embl-slurm")).toHaveAttribute("role", "status");
});

test("a compute a profile uses: the server's 409 is shown in the dialog, with Reload", async () => {
  serve({
    "/api/v1/version": SLURM,
    [`${API}/embl-slurm`]: () => json(409, { type: "/problems/compute-in-use", title: "In use", detail: "Profile gpu-h100 uses this compute." }),
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/compute");
  await userEvent.click(await screen.findByRole("button", { name: "Delete embl-slurm" }));
  const dialog = await screen.findByRole("dialog");
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete embl-slurm" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("Profile gpu-h100 uses this compute.");
  expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
});

test("a 412 in the Delete dialog is shown in place with Reload", async () => {
  serve({
    "/api/v1/version": SLURM,
    [`${API}/embl-slurm`]: () => json(412, { type: "/problems/etag-mismatch", title: "ETag mismatch", detail: "x" }),
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/compute");
  await userEvent.click(await screen.findByRole("button", { name: "Delete embl-slurm" }));
  const dialog = await screen.findByRole("dialog");
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete embl-slurm" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("This compute changed in another tab.");
});

test("the form posts the typed values: SLURM account, software and Apptainer arguments; a 409 lands on the name", async () => {
  const bodies: unknown[] = [];
  serve({
    "/api/v1/version": SLURM,
    [API]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list(BUILTINS));
      bodies.push(JSON.parse(String(init.body)));
      return bodies.length === 1
        ? json(409, { type: "/problems/compute-exists", title: "x", detail: "A compute named embl-slurm exists." })
        : json(201, item("embl-slurm"));
    },
  });
  app("/compute/new");
  await userEvent.type(await screen.findByLabelText("Name"), "embl-slurm");
  await userEvent.type(screen.getByLabelText("SLURM account"), "lab-a");
  const group = screen.getByRole("group", { name: "Software available" });
  expect(within(group).getByRole("checkbox", { name: "Conda" })).toBeChecked(); // both by default
  expect(within(group).getByRole("checkbox", { name: "Apptainer" })).toBeChecked();
  await userEvent.click(within(group).getByRole("checkbox", { name: "Conda" }));
  await userEvent.type(screen.getByLabelText("Apptainer arguments"), "--bind /g,/scratch");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByLabelText("Name")).toHaveAccessibleDescription(/A compute named embl-slurm exists/));
  expect(bodies[0]).toEqual({
    ...{ name: "embl-slurm", label: null, executor: "slurm", slurm: { account: "lab-a" }, local: null },
    ...{ software: ["apptainer"], apptainer_args: "--bind /g,/scratch" },
  });
});

test("the SLURM account is a select of the cluster's accounts when the facts have them", async () => {
  serve({
    "/api/v1/version": SLURM,
    [API]: list(BUILTINS),
    "/api/v1/cluster/facts": { scheduler: "slurm", fetched_at: null, partitions: [], accounts: ["lab-a", "lab-b"] },
  });
  app("/compute/new");
  await waitFor(() => expect(screen.getByRole("textbox", { name: "SLURM account" })).toHaveClass("mantine-Select-input"));
});

test("Local on a SLURM server starts at small caps; the form then sends them", async () => {
  const bodies: Record<string, unknown>[] = [];
  serve({
    "/api/v1/version": SLURM,
    [API]: (_u: URL, init?: RequestInit) => (init?.method === "POST" ? (bodies.push(JSON.parse(String(init.body))), json(201, item("box"))) : json(200, list(BUILTINS))),
  });
  app("/compute/new");
  await userEvent.type(await screen.findByLabelText("Name"), "box");
  await userEvent.click(screen.getByRole("radio", { name: /^Local/ }));
  expect(screen.getByLabelText("CPUs at most")).toHaveValue("2");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(bodies[0]).toMatchObject({ executor: "local", slurm: null, local: { cpus: 2, mem_mib: 8192 } }));
});

test("a server without SLURM: the executor is Local, and the form says so", async () => {
  serve({ "/api/v1/version": VERSION, [API]: list(BUILTINS) });
  app("/compute/new");
  expect(await screen.findByText(/spectio init --local/)).toBeInTheDocument();
  expect(screen.queryByRole("radio", { name: /SLURM/ })).toBeNull();
  expect(screen.getByLabelText("CPUs at most")).toBeInTheDocument();
});

test("editing: 412 says the compute changed, with Reload; after Save, the list with focus", async () => {
  let status = 412;
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-box`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "PUT") return json(200, MINE[1]);
      expect(new Headers(init.headers).get("if-match")).toBe('"gpu-box-1"');
      return status === 412 ? json(412, { type: "/problems/etag-mismatch", title: "x", detail: "x" }) : json(200, MINE[1]);
    },
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/compute/gpu-box");
  expect(await screen.findByLabelText("Name")).toHaveAttribute("readonly");
  expect(screen.getByText(/computes\.toml; comments in it are not kept/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This compute changed in another tab.");
  expect(screen.getByRole("button", { name: "Reload" })).toHaveAccessibleDescription("Reload discards your changes");
  status = 200;
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "gpu-box" })).toHaveFocus());
  expect(screen.getByText("Saved gpu-box")).toHaveAttribute("role", "status");
});

test("a missing compute is a 404 page with a link to the list", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/old`]: () => json(404, { title: "Not found", detail: "No such compute." }) });
  app("/compute/old");
  expect(await screen.findByRole("heading", { name: "No compute named old" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "All computes" })).toHaveAttribute("href", "/compute");
});

test("a built-in opens read only, with Duplicate to edit", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/slurm`]: BUILTINS[0], [API]: list(BUILTINS) });
  app("/compute/slurm");
  expect(await screen.findByLabelText("SLURM account")).toHaveAttribute("readonly");
  expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  expect(screen.getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/compute/new?from=slurm");
});

test("a 422 on a field the form does not show is a banner", async () => {
  serve({
    "/api/v1/version": SLURM,
    [API]: (_u: URL, init?: RequestInit) =>
      init?.method === "POST" ? json(422, { title: "x", detail: "Invalid", errors: [{ field: "body", message: "Nope." }] }) : json(200, list(BUILTINS)),
  });
  app("/compute/new");
  await userEvent.type(await screen.findByLabelText("Name"), "mylab");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Nope.");
});

test("a compute that cannot be read is an alert with Retry, not a missing one", async () => {
  let status = 500;
  serve({ "/api/v1/version": SLURM, [`${API}/gpu-box`]: () => (status === 500 ? json(500, { title: "x", detail: "Server error" }) : json(200, MINE[1])) });
  app("/compute/gpu-box");
  expect(await screen.findByRole("alert")).toHaveTextContent("gpu-box could not be read. Server error");
  status = 200;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByLabelText("Name")).toHaveValue("gpu-box");
});

test("FU-P3-111: Duplicate to edit names the copy <name>-copy, unique, clears a built-in's label, and saves a new compute", async () => {
  const bodies: Record<string, unknown>[] = [];
  serve({
    "/api/v1/version": SLURM,
    [`${API}/slurm`]: BUILTINS[0],
    [API]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list([...BUILTINS, item("slurm-copy")]));
      bodies.push(JSON.parse(String(init.body)));
      return json(201, item("slurm-copy-2"));
    },
  });
  app("/compute/new?from=slurm");
  expect(await screen.findByLabelText("Name")).toHaveValue("slurm-copy-2");
  expect(screen.getByLabelText("Name")).not.toHaveAttribute("readonly");
  expect(screen.getByLabelText("Label (optional)")).toHaveValue("");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(bodies[0]).toMatchObject({ name: "slurm-copy-2", executor: "slurm" }));
});

test("FU-P3-111: a duplicate's name stays within 32 characters", async () => {
  const long = item("a-very-long-compute-name-xyzabc1");
  serve({ "/api/v1/version": SLURM, [`${API}/${long.name}`]: long, [API]: list([...BUILTINS, long]) });
  app(`/compute/new?from=${long.name}`);
  expect(await screen.findByLabelText("Name")).toHaveValue("a-very-long-compute-name-xy-copy");
});

test("FU-P3-111: each kind has its icon; Cards and Table are a SegmentedControl kept in the URL", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  const router = app("/compute");
  const card = (await screen.findByRole("heading", { name: "EMBL cluster" })).closest("article")!;
  expect(card.querySelector('[data-kind="slurm"] svg')).toHaveAttribute("aria-hidden", "true");
  expect(screen.getByRole("heading", { name: "Login node" }).closest("article")!.querySelector('[data-kind="local"] svg')).not.toBeNull();
  const views = screen.getByRole("radiogroup", { name: "Show computes as" });
  const table = within(views).getByRole("radio", { name: "Table" });
  await userEvent.click(table);
  await waitFor(() => expect(router.state.location.search).toEqual({ view: "table" }));
  const grid = screen.getByRole("table", { name: "Compute, built-ins first" });
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Compute", "Kind", "Settings", "State", "Actions"]);
  const row = within(grid).getByRole("rowheader", { name: /EMBL cluster/ }).closest("tr")!;
  expect(within(row).getByRole("link", { name: "Edit embl-slurm" })).toBeInTheDocument();
  expect(screen.queryByRole("article")).toBeNull();
  await userEvent.click(within(views).getByRole("radio", { name: "Cards" }));
  await waitFor(() => expect(router.state.location.search).toEqual({}));
});

test("FU-P3-111: Cancel from the form returns to the table view", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/gpu-box`]: MINE[1], [API]: list([...BUILTINS, ...MINE]) });
  const router = app("/compute?view=table");
  await userEvent.click(await screen.findByRole("link", { name: "Edit gpu-box" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(router.state.location.search).toEqual({ view: "table" }));
  expect(await screen.findByRole("table")).toBeInTheDocument();
});

test("phone: cards by default, a card is one link to its page with no action buttons; the table has no Actions", async () => {
  viewport(390);
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  app("/compute");
  const link = await screen.findByRole("link", { name: "EMBL cluster" });
  expect(link).toHaveAttribute("href", "/compute/embl-slurm");
  const card = link.closest("article")!;
  expect(within(card).queryAllByRole("button")).toEqual([]);
  await userEvent.click(screen.getByRole("radio", { name: "Table" }));
  const grid = await screen.findByRole("table");
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Compute", "Kind", "Settings", "State"]);
  expect(within(grid).getByRole("link", { name: "EMBL cluster" })).toHaveAttribute("href", "/compute/embl-slurm");
});

test("phone: the page stacks Duplicate and Delete, named with the compute, Delete last behind its sheet", async () => {
  viewport(390);
  let items = [...BUILTINS, ...MINE];
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-box`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "DELETE") return json(200, MINE[1]);
      items = items.filter((i) => i.name !== "gpu-box");
      return new Response(null, { status: 204 });
    },
    [API]: () => json(200, list(items)),
  });
  app("/compute/gpu-box");
  const more = await screen.findByRole("group", { name: "More for this compute" });
  expect([...more.querySelectorAll("a, button")].map((b) => b.textContent)).toEqual(["Duplicate gpu-box", "Delete gpu-box"]);
  await userEvent.click(within(more).getByRole("button", { name: "Delete gpu-box" }));
  const sheet = await screen.findByRole("dialog", { name: "Delete gpu-box?" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete gpu-box" }));
  expect(await screen.findByText("Deleted gpu-box")).toHaveAttribute("role", "status");
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Compute" })).toHaveFocus());
});

test("FU-P3-108b: Edit and New move focus to the form's heading; Cancel returns it to the opener", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/gpu-box`]: MINE[1], [API]: list([...BUILTINS, ...MINE]) });
  app("/compute");
  await userEvent.click(await screen.findByRole("link", { name: "Edit gpu-box" }));
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "gpu-box" })).toHaveFocus());
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "Edit gpu-box" })).toHaveFocus());
  await userEvent.click(screen.getByRole("link", { name: "New compute" }));
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "New compute" })).toHaveFocus());
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "New compute" })).toHaveFocus());
});

test("UI-14: the shared states, the view switch in the toolbar with the count, one compute in the singular", async () => {
  let fail = true;
  serve({ [API]: () => (fail ? json(500, { title: "Server error", detail: "boom" }) : json(200, list([BUILTINS[0]]))), "/api/v1/version": SLURM });
  app("/compute");
  expect((await screen.findByRole("alert")).closest(".sp-errorpanel")).not.toBeNull();
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  const bar = await screen.findByRole("group", { name: "Compute view" });
  expect(bar).toHaveClass("sp-toolbar");
  expect(bar).toHaveTextContent("1 compute");
  expect(bar).not.toHaveTextContent("1 computes");
});

test("UI-14: loading is the shared skeleton; a pristine form shows no error", async () => {
  serve({ [API]: () => new Promise<Response>(() => {}), "/api/v1/version": SLURM });
  app("/compute");
  expect((await screen.findByText("Loading computes…")).closest(".sp-skelrows")).not.toBeNull();
  serve({ [API]: list([...BUILTINS]), "/api/v1/version": SLURM });
  app("/compute/new");
  expect(await screen.findByText(/^Fix .* first$/)).not.toHaveClass("sp-alert");
});
