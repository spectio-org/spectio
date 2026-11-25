import { ENGINES, ENGINE_FILES, type Engine, type Inspected } from "../api";

/** The entry files inspect found: `engine_files`, and the Nextflow main scripts (#351). */
export function entryFiles(found: Pick<Inspected, "engine_files" | "main_scripts">): string[] {
  return [...new Set([...found.engine_files, ...found.main_scripts])];
}

/** Whether `files` hold an entry of `engine`: for Nextflow, `main.nf` or another main script (#351). */
export function hasEntry(engine: Engine, files: string[]): boolean {
  return ENGINE_FILES[engine].some((f) => files.includes(f)) || (engine === "nextflow" && files.some((f) => f.endsWith(".nf")));
}

/** The engine that inspect's entry files point to; null for both or neither (Assumption 2). */
export function guessEngine(files: string[]): Engine | null {
  const found = ENGINES.filter((e) => hasEntry(e, files));
  return found.length === 1 ? found[0] : null;
}
