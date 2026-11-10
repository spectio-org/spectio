// The OME-TIFF viewer's lifecycle (FU-P3-102e; ui-spec §4.4.1, dev-env §15.3 req. 19 WebGL): a
// file with no OME-XML gets the flat view, and a WebGL failure ends the viewer and the open before
// the flat view takes its place. Viv, deck.gl and the open are mocked: jsdom has no WebGL.
import { MantineProvider } from "@mantine/core";
import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

const m = vi.hoisted(() => ({
  openWalked: vi.fn(),
  loadOmeTiff: vi.fn(),
  decks: [] as { props: Record<string, unknown>; finalize: ReturnType<typeof vi.fn> }[],
  pools: [] as { destroy: ReturnType<typeof vi.fn> }[],
  lose: vi.fn(),
}));
vi.mock("./flat", async (actual) => ({ ...(await actual<typeof import("./flat")>()), openWalked: m.openWalked }));
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
  isInterleaved: () => false,
  getImageSize: (s: { shape: number[] }) => ({ height: s.shape[3], width: s.shape[4] }),
  getDefaultInitialViewState: () => ({ target: [0, 0, 0], zoom: 0 }),
  MultiscaleImageLayer: class {},
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

import OmeView from "./OmeView";

const client = { size: 100, onBusy: null, failure: null };
const tiff = { parseFileDirectoryAt: vi.fn() };
const ifd = { ImageWidth: 100, ImageLength: 50 };

function view() {
  render(
    <MantineProvider>
      <OmeView url="/raw" size={100} name="a.ome.tif" fallback={<p>the flat view</p>} stateView={(s) => <p>{"title" in s ? s.title : "problem"}</p>} />
    </MantineProvider>,
  );
}

beforeEach(() => {
  m.decks.length = m.pools.length = 0;
  m.lose.mockReset();
  HTMLCanvasElement.prototype.getContext = (() => ({ getExtension: (n: string) => (n === "WEBGL_lose_context" ? { loseContext: m.lose } : null) })) as never;
  m.loadOmeTiff.mockResolvedValue({
    data: [{ shape: [1, 1, 1, 50, 100], tileSize: 512, getRaster: async () => ({ data: new Uint8Array([0, 9]) }) }],
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
