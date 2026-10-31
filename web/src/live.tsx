// Live refresh (P1 Task 20; api §8.3): one EventSource per browser tab on GET /events/stream,
// shared by every screen. A screen subscribes with `useFrames` and refetches what it shows; the
// stream's frames only say which run changed. `LiveStatus` says "live, updated N s ago" from the
// age of the last frame, or "Reconnecting…" while the EventSource reconnects (ui-spec §11).
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

export const STREAM = "/api/v1/events/stream";
const RETRY_MS = 5000; // after a refusal (429) the browser does not retry by itself

export interface Frame {
  run_id: string;
}
type Status = "connecting" | "live" | "reconnecting";
type Listener = (frame: Frame | null) => void; // null: (re)connected, so refetch everything

let source: EventSource | null = null;
let state: { status: Status; at: number } = { status: "connecting", at: Date.now() };
const listeners = new Set<Listener>();
const watchers = new Set<() => void>();

function set(status: Status, at = state.at) {
  if (status === state.status && at === state.at) return;
  state = { status, at };
  watchers.forEach((w) => w());
}

function open() {
  if (source || typeof EventSource === "undefined") return;
  const es = new EventSource(STREAM);
  source = es;
  es.onopen = () => {
    set("live", Date.now());
    listeners.forEach((l) => l(null));
  };
  es.onerror = () => {
    set("reconnecting");
    if (es.readyState === EventSource.CLOSED) {
      es.close();
      source = null;
      setTimeout(open, RETRY_MS);
    }
  };
  es.addEventListener("spectio.run.delta", (event) => {
    let frame: Frame;
    try {
      frame = JSON.parse((event as MessageEvent<string>).data);
    } catch {
      return;
    }
    if (typeof frame?.run_id !== "string") return;
    set("live", Date.now());
    listeners.forEach((l) => l(frame));
  });
}

/** For tests: forget the stream, so the next subscriber opens a new one. */
export function resetLive() {
  source?.close();
  source = null;
  state = { status: "connecting", at: Date.now() };
  listeners.clear();
}

/** Calls `refetch` after each frame (for `runId` only, when given) and on each (re)connection,
 * at most once a second. `enabled` false: stops listening (a terminal run). */
export function useFrames(refetch: () => void, runId?: string, enabled = true) {
  const latest = useRef(refetch);
  latest.current = refetch;
  useEffect(() => {
    if (!enabled) return;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let last = 0;
    const fire = () => {
      timer = null;
      last = Date.now();
      latest.current();
    };
    const listener: Listener = (frame) => {
      if (frame && runId && frame.run_id !== runId) return;
      if (timer) return;
      timer = setTimeout(fire, Math.max(0, 1000 - (Date.now() - last)));
    };
    listeners.add(listener);
    open();
    return () => {
      listeners.delete(listener);
      if (timer) clearTimeout(timer);
    };
  }, [runId, enabled]);
}

function useLive() {
  return useSyncExternalStore(
    (watch) => {
      watchers.add(watch);
      return () => watchers.delete(watch);
    },
    () => state,
  );
}

/** "live, updated 4 s ago" or "Reconnecting…", with a word and never colour alone. */
export function LiveStatus() {
  const { status, at } = useLive();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (status === "reconnecting") return <span className="sp-live" data-live="reconnecting">Reconnecting…</span>;
  if (status === "connecting") return <span className="sp-live">connecting…</span>;
  const age = Math.max(0, Math.round((now - at) / 1000));
  return (
    <span className="sp-live" data-live="live">
      live, updated {age} s ago
    </span>
  );
}
