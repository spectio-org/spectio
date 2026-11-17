// The server's feature flags (`GET /features`), read once per page load: the Graph tab and the
// Launch map show only with `graph_view` (0.0.2 behind a flag, dev-env §15).
import { useEffect, useState } from "react";
import { getFeatures } from "./types";

let cached: Promise<string[]> | null = null;

/** For tests: read the flags again on the next use. */
export function resetFeatures() {
  cached = null;
}

/** The flags; empty until read, and when the read fails. */
export function useFeatures(): string[] {
  const [features, setFeatures] = useState<string[]>([]);
  useEffect(() => {
    let live = true;
    cached ??= getFeatures().catch(() => {
      cached = null; // a failed read is tried again next time
      return [];
    });
    cached.then((f) => live && setFeatures(f));
    return () => {
      live = false;
    };
  }, []);
  return features;
}

export const GRAPH_VIEW = "graph_view";
