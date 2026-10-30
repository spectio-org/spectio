import { ENGINES, ENGINE_FILES, type Engine } from "../api";

/** The engine that inspect's `engine_files` point to; null for both or neither (Assumption 2). */
export function guessEngine(files: string[]): Engine | null {
  const found = ENGINES.filter((e) => ENGINE_FILES[e].some((f) => files.includes(f)));
  return found.length === 1 ? found[0] : null;
}
