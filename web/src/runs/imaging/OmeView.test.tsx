// The OME-TIFF viewer's lifecycle (FU-P3-102e; ui-spec §4.4.1, dev-env §15.3 req. 19 WebGL): a
// file with no OME-XML gets the flat view, and a WebGL failure ends the viewer and the open before
// the flat view takes its place. Viv, deck.gl and the open are mocked: jsdom has no WebGL.
import { MantineProvider } from "@mantine/core";
import { RouterProvider, createRootRoute, createRoute, createRouter } from "@tanstack/react-router";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

const m = vi.hoisted(() => ({
  openWalked: vi.fn(),
  loadOmeTiff: vi.fn(),
  openZarr: vi.fn(),
  loadZarr: vi.fn(),
  decks: [] as { props: Record<string, unknown>; finalize: ReturnType<typeof vi.fn> }[],
  pools: [] as { destroy: ReturnType<typeof vi.fn> }[],
  lose: vi.fn(),
  layers: [] as Record<string, unknown>[],
}));
vi.mock("./flat", async (actual) => ({ ...(await actual<typeof import("./flat")>()), openWalked: m.openWalked }));
vi.mock("./zarr", async (actual) => ({ ...(await actual<typeof import("./zarr")>()), openZarr: m.openZarr }));
vi.mock("./pool", () => ({
  DecoderPool: class {
    destroy = vi.fn();
    constructor() {
      m.pools.push(this);
    }
  },
}));
vi.mock("@hms-dbmi/viv", () => ({
  loadOmeTiff: m.loadOmeTiff,
  loadOmeZarrFromStore: m.loadZarr,
  ZarrPixelSource: class {},
  isInterleaved: (shape: number[]) => shape.at(-1) === 3, // as Viv: an interleaved RGB source ends with its 3 samples
  getImageSize: (s: { shape: number[] }) => ({ height: s.shape[3], width: s.shape[4] }),
  getDefaultInitialViewState: () => ({ target: [0, 0, 0], zoom: 0 }),
  MultiscaleImageLayer: class {
    constructor(props: Record<string, unknown>) {
      m.layers.push(props);
    }
  },
}));
vi.mock("@deck.gl/core", () => ({
  OrthographicView: class {},
  Deck: class {
    finalize = vi.fn();
    constructor(public props: Record<string, unknown>) {
      m.decks.push(this);
    }
    setProps() {}
  },
}));

import { resultsSearch } from "../ResultsBrowser";
import OmeView from "./OmeView";
import { NotImage } from "./zarr";

const TCZYX = ["t", "c", "z", "y", "x"];
const client = { size: 100, onBusy: null, failure: null };
const tiff = { parseFileDirectoryAt: vi.fn() };
const ifd = { ImageWidth: 100, ImageLength: 50 };

const ome = () => <OmeView url="/raw" size={100} name="a.ome.tif" fallback={<p>the flat view</p>} stateView={(s) => <p>{"title" in s ? s.title : "problem"}</p>} />;

function view() {
  return render(<MantineProvider>{ome()}</MantineProvider>);
}

/** The viewer under a real router on the browser's history, with the file route's search. */
function routed() {
  const root = createRootRoute();
  const file = createRoute({ getParentRoute: () => root, path: "/runs/$id/results/file", component: ome, validateSearch: resultsSearch });
  const router = createRouter({ routeTree: root.addChildren([file]) });
  return render(
    <MantineProvider>
      <RouterProvider router={router} />
    </MantineProvider>,
  );
}

function multi() {
  m.loadOmeTiff.mockResolvedValue({
    data: [{ shape: [2, 3, 3, 50, 100], labels: TCZYX, tileSize: 512, getRaster: async () => ({ data: new Uint8Array([0, 9]) }) }],
    metadata: { Pixels: { SizeX: 100, SizeY: 50, SizeC: 3, SizeZ: 3, SizeT: 2, Type: "uint8", Channels: [{ Name: "DAPI" }, {}, {}] } },
  });
  m.openWalked.mockResolvedValue({ tiff, client, ifds: Array(18).fill(ifd), files: "one", walked: { offsets: [8], values: 0 } });
}

beforeEach(() => {
  m.decks.length = m.pools.length = m.layers.length = 0;
  window.history.replaceState(null, "", "/runs/r1/results/file?path=a.ome.tif");
  m.lose.mockReset();
  HTMLCanvasElement.prototype.getContext = (() => ({ getExtension: (n: string) => (n === "WEBGL_lose_context" ? { loseContext: m.lose } : null) })) as never;
  m.loadOmeTiff.mockResolvedValue({
    data: [{ shape: [1, 1, 1, 50, 100], labels: TCZYX, tileSize: 512, getRaster: async () => ({ data: new Uint8Array([0, 9]) }) }],
    metadata: { Pixels: { SizeX: 100, SizeY: 50, SizeC: 1, SizeZ: 1, SizeT: 1, Type: "uint8" } },
  });
});

test("an .ome.tif with no OME-XML gets the flat view, and Viv is never called", async () => {
  m.openWalked.mockResolvedValue({ tiff, client, ifds: [ifd], files: "none", walked: { offsets: [8], values: 0 } });
  view();
  expect(await screen.findByText("the flat view")).toBeInTheDocument();
  expect(m.loadOmeTiff).not.toHaveBeenCalled();
  expect(m.pools[0].destroy).toHaveBeenCalled(); // the open's pool ends with it
});

test("a WebGL failure ends the viewer (its deck and its context) and the open's pool, then shows the flat view", async () => {
  m.openWalked.mockResolvedValue({ tiff, client, ifds: [ifd], files: "one", walked: { offsets: [8], values: 0 } });
  view();
  await waitFor(() => expect(m.decks).toHaveLength(1));
  expect(m.lose).not.toHaveBeenCalled();
  act(() => (m.decks[0].props.onError as (e: Error) => void)(new Error("no WebGL 2")));
  expect(await screen.findByText("the flat view")).toBeInTheDocument();
  expect(m.decks[0].finalize).toHaveBeenCalledOnce();
  expect(m.lose).toHaveBeenCalledOnce();
  expect(m.pools.every((p) => p.destroy.mock.calls.length > 0)).toBe(true);
  expect(m.decks).toHaveLength(1); // no second viewer
});

test("the view comes from the URL, is written back with a replace, and a reload keeps it", async () => {
  multi();
  window.history.replaceState(null, "", "/runs/r1/results/file?path=a.ome.tif&z=2&t=NaN&ch=2,9&zoom=1&x=10&y=5");
  const push = vi.spyOn(window.history, "pushState");
  const first = view();
  await waitFor(() => expect(m.decks).toHaveLength(1));
  await waitFor(() => expect(m.layers.at(-1)?.selections).toEqual([{ z: 1, t: 0, c: 2 }]));
  expect(screen.getByRole("slider", { name: /^Z plane/ })).toHaveValue("2");
  expect(screen.getByRole("switch", { name: "Show channel 1, DAPI" })).toHaveAttribute("aria-checked", "false");
  expect(screen.getByText("Zoom 200 %")).toBeInTheDocument();
  fireEvent.change(screen.getByRole("slider", { name: /^Z plane/ }), { target: { value: "3" } });
  fireEvent.click(screen.getByRole("switch", { name: "Show channel 1, DAPI" }));
  await waitFor(() => expect(window.location.search).toBe("?path=a.ome.tif&z=3&t=1&ch=2,0&zoom=1&x=10&y=5"));
  expect(push).not.toHaveBeenCalled(); // Back is not flooded
  first.unmount();
  view(); // a reload: the URL gives the view back
  await waitFor(() => expect(m.layers.at(-1)?.selections).toEqual([{ z: 2, t: 0, c: 2 }, { z: 2, t: 0, c: 0 }]));
});

// the router keeps the keys its validateSearch leaves out (@tanstack/router-core 1.170.46
// `dist/esm/router.js:913-925`, `{ ...result, ...validated }`), so its first commit does not strip them
test("a pasted link keeps the view through the router: the file route keeps z, t, ch, zoom, x and y (CR-P3FU102F-01)", async () => {
  multi();
  window.history.replaceState(null, "", "/runs/r1/results/file?path=a.ome.tif&z=2&ch=2,0&zoom=1&x=10&y=5");
  routed();
  await waitFor(() => expect(m.layers.at(-1)?.selections).toEqual([{ z: 1, t: 0, c: 2 }, { z: 1, t: 0, c: 0 }]));
  expect(screen.getByRole("slider", { name: /^Z plane/ })).toHaveValue("2");
  expect(screen.getByText("Zoom 200 %")).toBeInTheDocument();
  await waitFor(() => expect(window.location.search).toBe("?path=a.ome.tif&z=2&t=1&ch=2,0&zoom=1&x=10&y=5"));
});

test.each(["", "0,1,2"])("an RGB image ignores the URL's ch=%s: one selection, channel 0 (CR-P3FU102F-02)", async (ch) => {
  m.loadOmeTiff.mockResolvedValue({
    data: [{ shape: [1, 1, 1, 50, 100, 3], labels: TCZYX, tileSize: 512, getRaster: async () => ({ data: new Uint8Array([0, 9]) }) }],
    metadata: { Pixels: { SizeX: 100, SizeY: 50, SizeC: 3, SizeZ: 1, SizeT: 1, Type: "uint8" } },
  });
  m.openWalked.mockResolvedValue({ tiff, client, ifds: [{ ...ifd, SamplesPerPixel: 3 }], files: "one", walked: { offsets: [8], values: 0 } });
  window.history.replaceState(null, "", `/runs/r1/results/file?path=a.ome.tif&ch=${ch}`);
  view();
  await waitFor(() => expect(m.layers.at(-1)?.selections).toEqual([{ z: 0, t: 0, c: 0 }]));
});

test("an OME-Zarr opens through our store (no TIFF read), its axes deciding the selections; a NotImage folder ends in its state", async () => {
  m.openWalked.mockClear();
  m.openZarr.mockResolvedValue({ labels: ["c", "y", "x"], names: ["DAPI", "GFP"], colours: [[0, 0, 255], null] });
  m.loadZarr.mockResolvedValue({ data: [{ shape: [2, 50, 100], labels: ["c", "y", "x"], dtype: "Uint16", tileSize: 512, getRaster: async () => ({ data: new Uint16Array([0, 9]) }) }] });
  const zarr = (key: string) => `/raw/a.ome.zarr/${key}?as=zarr`;
  const first = render(<MantineProvider><OmeView url="" size={0} zarr={zarr} name="a.ome.zarr" fallback={<p>the flat view</p>} stateView={(s) => <p>{"title" in s ? s.title : "problem"}</p>} /></MantineProvider>);
  expect(await screen.findByText("100 × 50 px · 2 channels · 1 plane · 1 time point · uint16")).toBeInTheDocument();
  await waitFor(() => expect(m.layers.at(-1)?.selections).toEqual([{ c: 0 }, { c: 1 }]));
  expect(m.openWalked).not.toHaveBeenCalled();
  expect(m.openZarr.mock.calls[0][0].log).toEqual([]); // the store itself, unread here: openZarr is mocked
  first.unmount();
  m.openZarr.mockRejectedValue(new NotImage("This folder has no OME-Zarr image metadata."));
  render(<MantineProvider><OmeView url="" size={0} zarr={zarr} name="a.ome.zarr" fallback={<p>the flat view</p>} stateView={(s) => <p>{"title" in s ? s.title : "problem"}</p>} /></MantineProvider>);
  expect(await screen.findByText("This folder has no OME-Zarr image metadata.")).toBeInTheDocument();
});
