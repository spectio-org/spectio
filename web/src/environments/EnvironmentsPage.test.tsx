// The Environments pages (FU-P3-86f; ui-spec §4.8.1; boards LiteEnvironments, LiteEnvironmentEdit,
// LiteEnvironmentsStates): the list, Delete and Make default with their focus, and the form.
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { VERSION, app, json, serve, stubStream, viewport } from "../testing";

beforeEach(stubStream);
afterEach(() => vi.unstubAllGlobals());

const API = "/api/v1/environments";
const SLURM = { ...VERSION, executor: "slurm" };
const item = (name: string, over: Record<string, unknown> = {}) => ({
  name,
  label: null,
  executor: "slurm",
  builtin: false,
  default: false,
  usable: true,
  unusable_reason: null,
  slurm: { partition: "htc", account: "mylab", time_min: null, mem_mib: null },
  local: null,
  profiles: { nextflow: null, snakemake: null },
  etag: `"${name}-1"`,
  ...over,
});
const BUILTINS = [
  item("slurm", { label: "SLURM (from spectio init)", builtin: true, etag: '"s"' }),
  item("local", { label: "Login node", executor: "local", builtin: true, slurm: null, local: { cpus: 2, mem_mib: 8192 } }),
];
const list = (items: unknown[], state = "ok", detail: string | null = null) => ({
  items,
  default: "mylab-long",
  file: { path: "/home/amartin/.spectio/environments.toml", state, detail },
});
const MINE = [item("mylab-long", { label: "Long jobs, mylab", default: true }), item("gpu-test")];

test("Environments is in the main navigation, after Launch", async () => {
  serve({ [API]: list([...BUILTINS]), "/api/v1/version": SLURM });
  app("/environments");
  const nav = await screen.findByRole("navigation", { name: "Main" });
  const links = within(nav).getAllByRole("link").map((a) => a.textContent);
  expect(links.slice(-2)).toEqual(["Launch", "Environments"]);
  expect(within(nav).getByRole("link", { name: "Environments" })).toHaveAttribute("aria-current", "page");
  expect(await screen.findByText(/Only the built-in environments so far/)).toBeInTheDocument();
});

test("the list: one card per environment, badges in words, actions named with the card", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  app("/environments");
  const card = (await screen.findByRole("heading", { name: "Long jobs, mylab" })).closest("article")!;
  expect(card).toHaveTextContent("mylab-long");
  expect(card).toHaveTextContent("partition htc · SLURM account mylab");
  expect(within(card).getByText("Default")).toBeInTheDocument();
  expect(within(card).getByRole("button", { name: "Delete mylab-long" })).toBeInTheDocument();
  expect(within(card).queryByRole("button", { name: "Make default mylab-long" })).toBeNull();
  const builtin = screen.getByRole("heading", { name: "SLURM (from spectio init)" }).closest("article")!;
  expect(within(builtin).getByText("Built-in")).toBeInTheDocument();
  expect(within(builtin).queryByRole("link", { name: /^Edit/ })).toBeNull();
  expect(within(builtin).queryByRole("button", { name: /Delete/ })).toBeNull();
  expect(within(builtin).getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/environments/new?from=slurm");
  expect(within(card).getByRole("link", { name: "Duplicate mylab-long" })).toBeInTheDocument();
  expect(screen.getByText("on login1 (the login node) · at most 2 CPUs and 8 GiB")).toBeInTheDocument();
  expect(screen.getByText(/Saved in/)).toHaveTextContent("Saved in /home/amartin/.spectio/environments.toml");
});

test("a name is encoded in the links built from it (SEC-P3FU86F-02)", async () => {
  serve({ [API]: list([...BUILTINS, item("a/b?c")]), "/api/v1/version": SLURM });
  app("/environments");
  expect(await screen.findByRole("link", { name: "Edit a/b?c" })).toHaveAttribute("href", "/environments/a%2Fb%3Fc");
  expect(screen.getByRole("link", { name: "Duplicate a/b?c" })).toHaveAttribute("href", "/environments/new?from=a%2Fb%3Fc");
});

test("an invalid file: its line above the cards, New environment waits with its reason", async () => {
  serve({ [API]: list(BUILTINS, "invalid", "Expected (at line 7, column 13)"), "/api/v1/version": SLURM });
  app("/environments");
  expect(await screen.findByText(/has a mistake: Expected \(at line 7, column 13\)/)).toBeInTheDocument();
  const create = screen.getByRole("button", { name: "New environment" });
  expect(create).toHaveAttribute("aria-disabled", "true");
  expect(create).toHaveAccessibleDescription(/waits until the mistake in the file is fixed/);
  expect(screen.getByRole("button", { name: "Duplicate to edit slurm" })).toHaveAttribute("aria-disabled", "true");
});

test("Delete asks first; after it, focus on the next card's heading and a polite line", async () => {
  let items = [...BUILTINS, ...MINE];
  const mock = serve({
    "/api/v1/version": SLURM,
    [`${API}/mylab-long`]: (_u: URL, init?: RequestInit) => {
      expect(init?.method).toBe("DELETE");
      expect(new Headers(init?.headers).get("if-match")).toBe('"mylab-long-1"');
      items = items.filter((i) => i.name !== "mylab-long");
      return new Response(null, { status: 204 });
    },
    [API]: () => json(200, list(items)),
  });
  app("/environments");
  const del = await screen.findByRole("button", { name: "Delete mylab-long" });
  await userEvent.click(del);
  const dialog = await screen.findByRole("dialog", { name: "Delete mylab-long?" });
  expect(dialog).toHaveTextContent("Runs that used it keep their settings");
  expect(dialog).toHaveTextContent("slurm becomes the default again");
  await waitFor(() => expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus());
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete mylab-long" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "gpu-test" })).toHaveFocus());
  expect(screen.getByText("Deleted mylab-long")).toHaveAttribute("role", "status");
  expect(mock).toHaveBeenCalled();
});

test("a 412 in the Delete dialog is shown in place with Reload", async () => {
  serve({
    "/api/v1/version": SLURM,
    [`${API}/mylab-long`]: () => json(412, { type: "/problems/etag-mismatch", title: "ETag mismatch", detail: "x" }),
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/environments");
  await userEvent.click(await screen.findByRole("button", { name: "Delete mylab-long" }));
  const dialog = await screen.findByRole("dialog");
  await userEvent.click(within(dialog).getByRole("button", { name: "Delete mylab-long" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("This environment changed in another tab.");
  expect(within(dialog).getByRole("button", { name: "Reload" })).toBeInTheDocument();
});

test("Make default moves focus to the card's heading and says so", async () => {
  let def = "mylab-long";
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-test:make-default`]: () => ((def = "gpu-test"), new Response(null, { status: 204 })),
    [API]: () => json(200, list([...BUILTINS, ...MINE].map((i) => ({ ...i, default: i.name === def })))),
  });
  app("/environments");
  await userEvent.click(await screen.findByRole("button", { name: "Make default gpu-test" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "gpu-test" })).toHaveFocus());
  expect(screen.getByText("gpu-test is now the default")).toHaveAttribute("role", "status");
});

test("the form posts the typed values; a 422 lands on its field", async () => {
  const bodies: unknown[] = [];
  serve({
    "/api/v1/version": SLURM,
    [API]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "POST") return json(200, list(BUILTINS));
      bodies.push(JSON.parse(String(init.body)));
      return json(409, { type: "/problems/environment-exists", title: "x", detail: "An environment named mylab exists." });
    },
  });
  app("/environments/new");
  await userEvent.type(await screen.findByLabelText("Name"), "mylab");
  await userEvent.type(screen.getByLabelText("Hours"), "2");
  await userEvent.type(screen.getByLabelText("Minutes"), "30");
  await userEvent.type(screen.getByLabelText("Memory per job"), "1.5");
  await userEvent.selectOptions(screen.getByLabelText("Unit"), "GiB");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByLabelText("Name")).toHaveAccessibleDescription(/An environment named mylab exists/));
  expect(bodies[0]).toMatchObject({ name: "mylab", executor: "slurm", slurm: { time_min: 150, mem_mib: 1536 } });
});

test("the form: 0 h 0 min is refused before sending, and Save says why", async () => {
  serve({ "/api/v1/version": SLURM, [API]: list(BUILTINS) });
  app("/environments/new");
  await userEvent.type(await screen.findByLabelText("Name"), "x");
  await userEvent.type(screen.getByLabelText("Hours"), "0");
  await userEvent.type(screen.getByLabelText("Minutes"), "0");
  expect(screen.getByLabelText("Hours")).toHaveAccessibleDescription(/At least 1 minute/);
  const save = screen.getByRole("button", { name: "Save" });
  expect(save).toHaveAttribute("aria-disabled", "true");
  expect(save).toHaveAccessibleDescription("Fix Time per job first");
});

test("editing: 412 says the environment changed, with Reload; after Save, the list with focus", async () => {
  let status = 412;
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-test`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "PUT") return json(200, MINE[1]);
      expect(new Headers(init.headers).get("if-match")).toBe('"gpu-test-1"');
      return status === 412 ? json(412, { type: "/problems/etag-mismatch", title: "x", detail: "x" }) : json(200, MINE[1]);
    },
    [API]: list([...BUILTINS, ...MINE]),
  });
  app("/environments/gpu-test");
  expect(await screen.findByLabelText("Name")).toHaveAttribute("readonly");
  expect(screen.getByText(/comments in it are not kept/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This environment changed in another tab.");
  expect(screen.getByRole("button", { name: "Reload" })).toHaveAccessibleDescription("Reload discards your changes");
  status = 200;
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(screen.getByRole("heading", { name: "gpu-test" })).toHaveFocus());
  expect(screen.getByText("Saved gpu-test")).toHaveAttribute("role", "status");
});

test("a missing environment is a 404 page with a link to the list", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/mylab-old`]: () => json(404, { title: "Not found", detail: "No such environment." }) });
  app("/environments/mylab-old");
  expect(await screen.findByRole("heading", { name: "No environment named mylab-old" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "All environments" })).toHaveAttribute("href", "/environments");
});

test("a built-in opens read only, with Duplicate to edit", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/slurm`]: BUILTINS[0], [API]: list(BUILTINS) });
  app("/environments/slurm");
  expect(await screen.findByLabelText("Partition")).toHaveAttribute("readonly");
  expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  expect(screen.getByRole("link", { name: "Duplicate to edit slurm" })).toHaveAttribute("href", "/environments/new?from=slurm");
});

test("a 422 on a field the form does not show is a banner", async () => {
  serve({
    "/api/v1/version": SLURM,
    [API]: (_u: URL, init?: RequestInit) =>
      init?.method === "POST"
        ? json(422, { title: "x", detail: "Invalid", errors: [{ field: "executor", message: "This server has no SLURM." }] })
        : json(200, list(BUILTINS)),
  });
  app("/environments/new");
  await userEvent.type(await screen.findByLabelText("Name"), "mylab");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("This server has no SLURM.");
});

test("an environment that cannot be read is an alert with Retry, not a missing one", async () => {
  let status = 500;
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-test`]: () => (status === 500 ? json(500, { title: "x", detail: "Server error" }) : json(200, MINE[1])),
  });
  app("/environments/gpu-test");
  expect(await screen.findByRole("alert")).toHaveTextContent("gpu-test could not be read. Server error");
  expect(screen.queryByText(/deleted in another tab/)).toBeNull();
  status = 200;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByLabelText("Name")).toHaveValue("gpu-test");
});

test("FU-P3-111: Duplicate to edit names the copy <name>-copy, unique, clears a built-in's label, and saves a new file environment", async () => {
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
  app("/environments/new?from=slurm");
  expect(await screen.findByLabelText("Name")).toHaveValue("slurm-copy-2");
  expect(screen.getByLabelText("Name")).not.toHaveAttribute("readonly");
  expect(screen.getByLabelText("Label (optional)")).toHaveValue("");
  expect(screen.getByLabelText("Partition")).toHaveValue("htc");
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(bodies[0]).toMatchObject({ name: "slurm-copy-2", executor: "slurm", slurm: { partition: "htc", account: "mylab" } }));
});

test("FU-P3-111: a duplicate's name stays within 32 characters", async () => {
  const long = item("a-very-long-environment-name-xyz");
  serve({ "/api/v1/version": SLURM, [`${API}/${long.name}`]: long, [API]: list([...BUILTINS, long]) });
  app(`/environments/new?from=${long.name}`);
  expect(await screen.findByLabelText("Name")).toHaveValue("a-very-long-environment-nam-copy");
});

test("FU-P3-111: each kind has its icon; Cards and Table are a pressed pair kept in the URL", async () => {
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  const router = app("/environments");
  const card = (await screen.findByRole("heading", { name: "Long jobs, mylab" })).closest("article")!;
  expect(card.querySelector('[data-kind="slurm"] svg')).toHaveAttribute("aria-hidden", "true");
  const local = screen.getByRole("heading", { name: "Login node" }).closest("article")!;
  expect(local.querySelector('[data-kind="local"] svg')).not.toBeNull();
  const views = screen.getByRole("group", { name: "Show environments as" });
  const cards = within(views).getByRole("button", { name: "Cards" });
  const table = within(views).getByRole("button", { name: "Table" });
  expect(cards).toHaveAttribute("aria-pressed", "true");
  expect(table).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(table);
  await waitFor(() => expect(router.state.location.search).toEqual({ view: "table" }));
  expect(table).toHaveAttribute("aria-pressed", "true");
  const grid = screen.getByRole("table", { name: "Environments, built-ins first" });
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Environment", "Kind", "Settings", "State", "Actions"]);
  const row = within(grid).getByRole("rowheader", { name: /Long jobs, mylab/ }).closest("tr")!;
  expect(row).toHaveTextContent("partition htc · SLURM account mylab");
  expect(within(row).getByRole("link", { name: "Edit mylab-long" })).toBeInTheDocument();
  const builtin = within(grid).getByRole("rowheader", { name: /SLURM \(from spectio init\)/ }).closest("tr")!;
  expect(within(builtin).getByRole("link", { name: "Duplicate to edit slurm" })).toBeInTheDocument();
  expect(within(builtin).queryByRole("link", { name: /^Edit/ })).toBeNull();
  expect(screen.queryByRole("article")).toBeNull();
  await userEvent.click(cards);
  await waitFor(() => expect(router.state.location.search).toEqual({}));
  expect(screen.queryByRole("table")).toBeNull();
});

test("FU-P3-111: ?view=table opens the table; Make default focuses the row's header", async () => {
  let def = "mylab-long";
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-test:make-default`]: () => ((def = "gpu-test"), new Response(null, { status: 204 })),
    [API]: () => json(200, list([...BUILTINS, ...MINE].map((i) => ({ ...i, default: i.name === def })))),
  });
  app("/environments?view=table");
  await userEvent.click(await screen.findByRole("button", { name: "Make default gpu-test" }));
  await waitFor(() => expect(screen.getByRole("rowheader", { name: /gpu-test/ })).toHaveFocus());
});

test("FU-P3-111: Cancel from the form returns to the table view", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/gpu-test`]: MINE[1], [API]: list([...BUILTINS, ...MINE]) });
  const router = app("/environments?view=table");
  await userEvent.click(await screen.findByRole("link", { name: "Edit gpu-test" }));
  await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(router.state.location.search).toEqual({ view: "table" }));
  expect(await screen.findByRole("table")).toBeInTheDocument();
});

test("FU-P3-111 phone: cards by default; the table has no Actions and its names are links", async () => {
  viewport(390);
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  app("/environments");
  await screen.findByRole("link", { name: "Long jobs, mylab" });
  expect(screen.getByRole("button", { name: "Cards" })).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(screen.getByRole("button", { name: "Table" }));
  const grid = await screen.findByRole("table");
  expect(within(grid).getAllByRole("columnheader").map((h) => h.textContent)).toEqual(["Environment", "Kind", "Settings", "State"]);
  expect(within(grid).queryAllByRole("button")).toEqual([]);
  expect(within(grid).getByRole("link", { name: "Long jobs, mylab" })).toHaveAttribute("href", "/environments/mylab-long");
});

test("an invalid file: no empty line beside the file line", async () => {
  serve({ [API]: list(BUILTINS, "invalid", "Expected"), "/api/v1/version": SLURM });
  app("/environments");
  await screen.findByText(/has a mistake/);
  expect(screen.queryByText(/Only the built-in environments so far/)).toBeNull();
});

test("while the list loads: its line and the cards' skeleton", async () => {
  serve({ [API]: () => new Promise<Response>(() => {}), "/api/v1/version": SLURM });
  app("/environments");
  expect(await screen.findByText("Loading environments…")).toBeInTheDocument();
  expect(document.querySelectorAll(".sp-env[aria-hidden]").length).toBeGreaterThan(0);
});

test("phone: a card is one link to its page, with no action buttons", async () => {
  viewport(390);
  serve({ [API]: list([...BUILTINS, ...MINE]), "/api/v1/version": SLURM });
  app("/environments");
  const link = await screen.findByRole("link", { name: "Long jobs, mylab" });
  expect(link).toHaveAttribute("href", "/environments/mylab-long");
  expect(screen.getByRole("link", { name: "SLURM (from spectio init)" })).toHaveAttribute("href", "/environments/slurm");
  const card = link.closest("article")!;
  expect(within(card).queryAllByRole("button")).toEqual([]);
  expect(within(card).queryAllByRole("link")).toEqual([link]);
});

test("phone: the page stacks its actions, named with the environment, Delete last behind its sheet", async () => {
  viewport(390);
  let items = [...BUILTINS, ...MINE];
  serve({
    "/api/v1/version": SLURM,
    [`${API}/gpu-test`]: (_u: URL, init?: RequestInit) => {
      if (init?.method !== "DELETE") return json(200, MINE[1]);
      items = items.filter((i) => i.name !== "gpu-test");
      return new Response(null, { status: 204 });
    },
    [API]: () => json(200, list(items)),
  });
  app("/environments/gpu-test");
  const more = await screen.findByRole("group", { name: "More for this environment" });
  const names = [...more.querySelectorAll("a, button")].map((b) => b.textContent);
  expect(names).toEqual(["Make default gpu-test", "Duplicate gpu-test", "Delete gpu-test"]);
  await userEvent.click(within(more).getByRole("button", { name: "Delete gpu-test" }));
  const sheet = await screen.findByRole("dialog", { name: "Delete gpu-test?" });
  await userEvent.click(within(sheet).getByRole("button", { name: "Delete gpu-test" }));
  expect(await screen.findByText("Deleted gpu-test")).toHaveAttribute("role", "status");
  expect(screen.queryByRole("link", { name: "gpu-test" })).toBeNull();
  // CR-P3UI03-01: the title row's h1 takes the focus, not <body>.
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "Environments" })).toHaveFocus());
});

test("FU-P3-111 phone: a built-in's page offers Duplicate to edit, and no Delete", async () => {
  viewport(390);
  serve({ "/api/v1/version": SLURM, [`${API}/slurm`]: BUILTINS[0], [API]: list(BUILTINS) });
  app("/environments/slurm");
  const more = await screen.findByRole("group", { name: "More for this environment" });
  expect([...more.querySelectorAll("a, button")].map((b) => b.textContent)).toEqual(["Make default slurm", "Duplicate to edit slurm"]);
});

test("FU-P3-108b: Edit and New move focus to the form's heading; Cancel returns it to the opener", async () => {
  serve({ "/api/v1/version": SLURM, [`${API}/gpu-test`]: MINE[1], [API]: list([...BUILTINS, ...MINE]) });
  app("/environments");
  await userEvent.click(await screen.findByRole("link", { name: "Edit gpu-test" }));
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "gpu-test" })).toHaveFocus());
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "Edit gpu-test" })).toHaveFocus());
  await userEvent.click(screen.getByRole("link", { name: "New environment" }));
  await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "New environment" })).toHaveFocus());
  await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await waitFor(() => expect(screen.getByRole("link", { name: "New environment" })).toHaveFocus());
});

test("CR-P3FU111-02: New does not read the list, only a duplicate does", async () => {
  const reads: string[] = [];
  serve({
    "/api/v1/version": SLURM,
    [API]: (u: URL, init?: RequestInit) => (init?.method !== "POST" && reads.push(u.pathname), json(200, list(BUILTINS))),
  });
  app("/environments/new");
  await screen.findByLabelText("Name");
  expect(reads).toEqual([]);
});
