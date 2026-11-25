import type { Task } from "../api";
import { lastSegment } from "./stateWord";

/** One wildcard (`key` set) or a Nextflow tag (`key` null). */
export interface TaskPart {
  key: string | null;
  value: string;
}

/** Splits at the commas outside (), [] and {}; null when a bracket is left open. */
function topLevel(text: string): string[] | null {
  const pieces: string[] = [];
  let depth = 0;
  let from = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if ("([{".includes(c)) depth++;
    else if (")]}".includes(c)) depth = Math.max(0, depth - 1);
    else if (c === "," && depth === 0) {
      pieces.push(text.slice(from, i));
      from = i + 1;
    }
  }
  pieces.push(text.slice(from));
  return depth === 0 ? pieces.map((p) => p.trim()) : null;
}

/** The tag as parts: `k=v, k=v` (Snakemake's wildcards, projector/snakemake.py) one part each, any
 * other text (a Nextflow tag, or a tag that does not parse) one part with no key. */
function parts(tag: string | null): TaskPart[] {
  const raw = tag?.trim();
  if (!raw) return [];
  const pairs = topLevel(raw)?.map((p) => /^([A-Za-z_][\w.-]*)=(.*)$/s.exec(p));
  if (!pairs || pairs.some((m) => !m)) return [{ key: null, value: raw }];
  return pairs.map((m) => ({ key: m![1], value: m![2] }));
}

/** A job's name as a title (the rule, or the process's last segment) and its labelled parts (#385). */
export function taskName(task: Task): { title: string; parts: TaskPart[] } {
  return { title: lastSegment(task.process), parts: parts(task.tag) };
}

/** The parts on one line: `k=v · k=v`. */
export const partsLine = (parts: TaskPart[]) => parts.map((p) => (p.key === null ? p.value : `${p.key}=${p.value}`)).join(" · ");
