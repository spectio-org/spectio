// The OME-TIFF WebGL viewer (FU-P3-102e; ui-spec §4.4.1, imaging; boards LiteImageViewer), in
// the lazy chunk with Viv and deck.gl (FilePreview imports it with React.lazy, so the main bundle
// does not grow): the TIFF opened and walked through the pinned client, its later IFD parses
// guarded, then handed to Viv. A canvas on a black backdrop in a focusable region, keys and
// buttons for the zoom, Z and T ranges, and a status line for what stopped the reading.
import { Button } from "@mantine/core";
import { type ReactNode, useEffect, useRef, useState } from "react";
import type { ApiError } from "../../api";
import { type PinnedClient, Stopped } from "./client";
import { type ImageState, imageState, openWalked } from "./flat";
import { DecoderPool } from "./pool";
import { type Pixels, type ViewState, Viewer, openPixels } from "./viv";
import { guardParses } from "./walk";

type Opened = { pixels: Pixels; client: PinnedClient };
type Status = { title: string; action: "reload" | "retry" } | null;
const ZOOM = { min: -12, max: 6 };

interface Props {
  url: string;
  size: number;
  name: string;
  /** The flat view, shown when WebGL fails. */
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

export default function OmeView({ url, size, name, fallback, stateView }: Props) {
  const [opens, setOpens] = useState(0); // Reload: a new open, so a new budget; the view is kept
  const [opened, setOpened] = useState<Opened | null>(null);
  const [state, setState] = useState<ImageState | { problem: ApiError } | null>(null);
  const [noGl, setNoGl] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status>(null);
  const [view, setView] = useState<ViewState | null>(null);
  const [shown, setShown] = useState({ z: 0, t: 0 }); // the ranges' values
  const [plane, setPlane] = useState(shown); // read 200 ms after the last change
  const [epoch, setEpoch] = useState(0);
  const canvas = useRef<HTMLCanvasElement>(null);
  const viewer = useRef<Viewer | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const pool = new DecoderPool();
    setOpened(null);
    setStatus(null);
    (async () => {
      const { tiff, client } = await openWalked(url, size, name, true, controller.signal);
      guardParses(tiff, client);
      client.onBusy = (b) => controller.signal.aborted || setBusy(b);
      const pixels = await openPixels(tiff, pool, name);
      if (!controller.signal.aborted) setOpened({ pixels, client });
    })().catch((err) => controller.signal.aborted || setState(imageState(err)));
    return () => (controller.abort(), pool.destroy());
  }, [url, size, name, opens]);

  useEffect(() => {
    if (!opened || !canvas.current) return;
    const tileError = () => {
      const stopped = opened.client.failure instanceof Stopped; // BlockedSource hides it behind its own error
      setStatus(stopped ? { title: (imageState(opened.client.failure) as ImageState).title, action: "reload" } : { title: "Some tiles could not be read.", action: "retry" });
    };
    const v = new Viewer(canvas.current, opened.pixels, { onView: setView, onTileError: tileError, onError: () => setNoGl(true) });
    viewer.current = v;
    setView((kept) => kept ?? v.fit());
    return () => {
      v.destroy();
      viewer.current = null;
    };
  }, [opened]);

  useEffect(() => {
    if (view) viewer.current?.draw(view, plane, epoch);
  }, [view, plane, epoch, opened]);

  useEffect(() => {
    const timer = setTimeout(() => setPlane(shown), 200);
    return () => clearTimeout(timer);
  }, [shown]);

  if (noGl) return fallback;
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
  );
}
