// The OME-TIFF WebGL viewer (FU-P3-102e; ui-spec §4.4.1, imaging; boards LiteImageViewer), in
// the lazy chunk with Viv and deck.gl (FilePreview imports it with React.lazy, so the main bundle
// does not grow): the TIFF opened and walked through the pinned client, its later IFD parses
// guarded, then handed to Viv. A canvas on a black backdrop in a focusable region, keys and
// buttons for the zoom, Z and T ranges, and a status line for what stopped the reading. The
// channel list and the view in the URL (FU-P3-102f): read once when the viewer opens, written back
// with a history replace after a pause, so a Reload of the page or of the open keeps the view.
// An OME-Zarr folder (FU-P3-102g) is read through our own store instead, key by key (`zarr`), its
// chunks decoded in the decoder workers (FU-P3-102h).
import { Button } from "@mantine/core";
import { type ReactNode, useEffect, useRef, useState } from "react";
import type { ApiError } from "../../api";
import { Stopped } from "./client";
import { type ImageState, imageState, openWalked } from "./flat";
import { type ChannelState, Channels, initialChannels } from "./Channels";
import { DecoderPool } from "./pool";
import { ZOOM, parseView, writeView } from "./url-state";
import { type Pixels, type Stats, type ViewState, Viewer, openPixels, openZarrPixels } from "./viv";
import { guardParses } from "./walk";
import { ZarrStore, inWorkers } from "./zarr";

type Opened = { pixels: Pixels; client: { failure: Error | null } }; // the TIFF's pinned client or the Zarr store
type Status = { title: string; action: "reload" | "retry" } | null;

interface Props {
  url: string;
  size: number;
  name: string;
  /** An OME-Zarr folder: the raw route's URL of each key below it (as=zarr); `url` and `size` unused. */
  zarr?: (key: string) => string;
  /** The folder is in a work directory, which serves no Zarr v2 metadata. */
  workdir?: boolean;
  /** The flat view, shown when WebGL fails or the file has no OME-XML. */
  fallback: ReactNode;
  /** A problem before the first tile, as the file page shows it. */
  stateView: (state: ImageState | { problem: ApiError }, retry: () => void) => ReactNode;
}

function Plane({ label, value, count, onChange }: { label: string; value: number; count: number; onChange: (v: number) => void }) {
  if (count <= 1) return null;
  const text = `${value + 1} of ${count}`;
  return (
    <label className="sp-file-line">
      {label}
      <input type="range" min={1} max={count} value={value + 1} aria-valuetext={text} onChange={(e) => onChange(Number(e.target.value) - 1)} />
      <span>{text}</span>
    </label>
  );
}

export default function OmeView({ url, size, name, zarr, workdir = false, fallback, stateView }: Props) {
  const [opens, setOpens] = useState(0); // Reload: a new open, so a new budget; the view is kept
  const [opened, setOpened] = useState<Opened | null>(null);
  const [state, setState] = useState<ImageState | { problem: ApiError } | null>(null);
  const [flatOnly, setFlatOnly] = useState(false); // no OME-XML, or WebGL failed: the flat view, and nothing of ours left open
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);
  const [view, setView] = useState<ViewState | null>(null);
  const [shown, setShown] = useState({ z: 0, t: 0 }); // the ranges' values
  const [plane, setPlane] = useState(shown); // read 200 ms after the last change
  const [epoch, setEpoch] = useState(0);
  const [chans, setChans] = useState<ChannelState | null>(null); // kept across a Reload of the open
  const [stats, setStats] = useState<Record<number, Stats>>({});
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Viewer | null>(null);
  const restored = useRef(false);

  useEffect(() => {
    setOpened(null);
    setStatus(null);
    if (flatOnly) return;
    const controller = new AbortController();
    let pool: DecoderPool | undefined; // the decoder workers: the TIFF's tiles, or the Zarr's chunks
    (async () => {
      if (zarr) {
        const store = new ZarrStore(zarr, inWorkers((pool = new DecoderPool())), controller.signal);
        store.work = workdir;
        store.onBusy = (b) => controller.signal.aborted || setBusy(b);
        const pixels = await openZarrPixels(store);
        return controller.signal.aborted || setOpened({ pixels, client: store });
      }
      const { tiff, client, ifds, files, walked } = await openWalked(url, size, name, true, controller.signal);
      if (files === "none") return controller.signal.aborted || setFlatOnly(true); // the flat view says "no OME metadata"
      guardParses(tiff, client, walked);
      client.onBusy = (b) => controller.signal.aborted || setBusy(b);
      if (controller.signal.aborted) return; // the cleanup has run: no pool left behind it
      pool = new DecoderPool();
      const pixels = await openPixels(tiff, pool, name, ifds);
      if (!controller.signal.aborted) setOpened({ pixels, client });
    })().catch((err) => controller.signal.aborted || setState(imageState(err)));
    return () => (controller.abort(), pool?.destroy());
  }, [url, size, name, zarr, workdir, opens, flatOnly]);

  useEffect(() => {
    if (flatOnly || !opened || !canvas.current) return;
    const tileError = () => {
      const stopped = opened.client.failure instanceof Stopped; // BlockedSource hides it behind its own error
      setStatus(stopped ? { title: (imageState(opened.client.failure) as ImageState).title, action: "reload" } : { title: "Some tiles could not be read.", action: "retry" });
    };
    const v = new Viewer(canvas.current, opened.pixels, { onView: setView, onTileError: tileError, onError: () => setFlatOnly(true) }); // the cleanups end the viewer and the open
    viewer.current = v;
    const url = parseView(window.location.search, opened.pixels.sizes);
    setView((kept) => kept ?? url.view ?? v.fit());
    if (!restored.current) {
      restored.current = true; // the first open only: a Reload of the open keeps the view it has
      setShown({ z: url.z, t: url.t });
      setPlane({ z: url.z, t: url.t });
      setChans(initialChannels(opened.pixels.colours, opened.pixels.rgb ? null : url.ch, opened.pixels.channels.length)); // RGB has one channel and no panel to undo a URL's ch
    }
    return () => {
      v.destroy();
      viewer.current = null;
    };
  }, [opened, flatOnly]);

  useEffect(() => {
    if (!opened || !chans) return;
    for (const c of chans.on.filter((c) => !stats[c])) opened.pixels.stats(c).then((s) => setStats((all) => ({ ...all, [c]: s })), () => setStatus({ title: "Some tiles could not be read.", action: "retry" }));
  }, [opened, chans, stats, epoch]);

  useEffect(() => {
    if (!view || !chans) return;
    const drawn = chans.on.filter((c) => stats[c]).map((c) => ({ c, colour: chans.colours[c], limits: chans.limits[c] ?? stats[c].limits }));
    viewer.current?.draw(view, plane, epoch, drawn);
    const timer = setTimeout(() => writeView({ ...plane, ch: opened?.pixels.rgb ? null : chans.on, view }), 300); // replaceState is throttled
    return () => clearTimeout(timer);
  }, [view, plane, epoch, opened, chans, stats]);

  useEffect(() => {
    const timer = setTimeout(() => setPlane(shown), 200);
    return () => clearTimeout(timer);
  }, [shown]);

  if (flatOnly) return fallback;
  if (state) return stateView(state, () => (setState(null), setOpens((n) => n + 1)));

  const zoom = (by: number) => view && setView({ ...view, zoom: Math.min(ZOOM.max, Math.max(ZOOM.min, view.zoom + by)) });
  const fit = () => viewer.current && setView(viewer.current.fit());
  const keys = (e: React.KeyboardEvent) => {
    if (!view) return;
    const step = (0.1 * (canvas.current?.clientWidth || 800)) / 2 ** view.zoom;
    const pan: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (pan[e.key]) setView({ ...view, target: [view.target[0] + pan[e.key][0], view.target[1] + pan[e.key][1], 0] });
    else if (e.key === "+" || e.key === "=") zoom(1);
    else if (e.key === "-") zoom(-1);
    else if (e.key === "0") fit();
    else return;
    e.preventDefault();
  };
  const again = () => {
    if (status?.action === "reload") setOpens((n) => n + 1);
    else if (opened) {
      opened.client.failure = null;
      setEpoch((n) => n + 1);
    }
    setStatus(null);
  };

  return (
    <div className="sp-ome-layout">
      <div className="sp-file-viewer">
        <div className="sp-file-line">
          <span role="status">{status?.title ?? (!opened ? "Loading the image…" : busy ? "Reading tiles…" : "")}</span>
          {status && (
            <Button variant="default" size="xs" onClick={again}>
              {status.action === "reload" ? "Reload" : "Retry"}
            </Button>
          )}
        </div>
        <section className="sp-ome-region" tabIndex={0} aria-label={`${name}, image viewer`} onKeyDown={keys}>
          <canvas ref={canvas} className="sp-ome-canvas" />
        </section>
        <p className="sp-muted">Arrows pan · + or = zoom in · − zoom out · 0 fits</p>
        <div className="sp-actions">
          <Button variant="default" size="xs" onClick={() => zoom(1)}>Zoom in</Button>
          <Button variant="default" size="xs" onClick={() => zoom(-1)}>Zoom out</Button>
          <Button variant="default" size="xs" onClick={fit}>Fit</Button>
          <span>{view ? `Zoom ${Math.round(2 ** view.zoom * 100)} %` : ""}</span>
        </div>
        {opened && (
          <>
            <p className="sp-file-natural">{opened.pixels.facts}</p>
            <Plane label="Z plane" value={shown.z} count={opened.pixels.sizes.z} onChange={(z) => setShown({ ...shown, z })} />
            <Plane label="Time point" value={shown.t} count={opened.pixels.sizes.t} onChange={(t) => setShown({ ...shown, t })} />
          </>
        )}
      </div>
      {opened && chans && !opened.pixels.rgb && <Channels names={opened.pixels.names} meta={opened.pixels.colours} state={chans} stats={stats} onChange={setChans} />}
    </div>
  );
}
