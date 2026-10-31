import { type KeyboardEvent, type ReactNode, memo, useEffect, useMemo, useRef, useState } from "react";
import { ICONS, Icon } from "../icons";

// The run's log viewer (LiteRunLogs; P3-parD, Thomas 2026-10-31: "logs pas searchable"): the lines
// tinted by level, a level filter, and a search whose matches are marked, with an "n / m" counter,
// previous and next (Enter, Shift+Enter) and Escape to clear. The query lands 150 ms after typing;
// each line is a memoised component, so a keystroke or a step re-renders only the lines it changes.

/** A log line's level, as a secondary tint (LiteRunLogs): the level word is in the text already.
 * Errors, then warnings and retries, then a task or job done, then Nextflow's progress line; INFO
 * keeps the viewer's text colour. */
export function level(line: string): string | undefined {
  if (/\bERROR\b|\bError\b|exception/.test(line)) return "failed";
  if (/\bWARN|\bretry/i.test(line)) return "review";
  if (/\bcompleted\b|\bFinished job\b|\(100%\) done/.test(line)) return "ok";
  if (/\bprogress \d/.test(line)) return "progress";
  return undefined;
}

type Level = "all" | "info" | "warn" | "error";
const LEVELS: { key: Level; label: string; tone?: string }[] = [
  { key: "all", label: "All" },
  { key: "info", label: "INFO" },
  { key: "warn", label: "WARN", tone: "review" },
  { key: "error", label: "ERROR", tone: "failed" },
];
/** A tint's level: the error and warning tints, and INFO for every other line. */
const levelOf = (tone: string | undefined): Level => (tone === "failed" ? "error" : tone === "review" ? "warn" : "info");

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** One line, its matches marked; `current` is the index of the current match in `hits`, or -1. */
const Line = memo(function Line({ text, tone, hits, size, current }: { text: string; tone?: string; hits?: number[]; size: number; current: number }) {
  if (!hits) {
    return (
      <span data-tone={tone}>
        {text}
        {"\n"}
      </span>
    );
  }
  const parts: ReactNode[] = [];
  let at = 0;
  hits.forEach((start, i) => {
    parts.push(text.slice(at, start));
    parts.push(
      <mark key={i} data-current={i === current || undefined}>
        {text.slice(start, start + size)}
      </mark>,
    );
    at = start + size;
  });
  parts.push(text.slice(at));
  return (
    <span data-tone={tone}>
      {parts}
      {"\n"}
    </span>
  );
});

/** A log's lines, each tinted by its level (the Summary's last lines). */
export function LogLines({ text }: { text: string }) {
  return text.split("\n").map((line, i) => <Line key={i} text={line} tone={level(line)} size={0} current={-1} />);
}

/** The whole viewer: the search and level tools, then the lines, opened at their end. */
export function LogViewer({ text, label }: { text: string | null; label: string }) {
  const [typed, setTyped] = useState("");
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState<Level>("all");
  const [current, setCurrent] = useState(0);
  const viewer = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setQuery(typed), 150);
    return () => clearTimeout(timer);
  }, [typed]);

  const lines = useMemo(() => (text ?? "").split("\n").map((line) => ({ text: line, tone: level(line) })), [text]);
  const counts = useMemo(() => {
    const found: Record<Level, number> = { all: lines.length, info: 0, warn: 0, error: 0 };
    for (const line of lines) found[levelOf(line.tone)] += 1;
    return found;
  }, [lines]);
  const visible = useMemo(
    () => lines.flatMap((line, i) => (shown === "all" || levelOf(line.tone) === shown ? [i] : [])),
    [lines, shown],
  );
  // Every match of the query in the lines shown: by line, its starts; in order, [line, n-th on it].
  const { hits, matches } = useMemo(() => {
    const byLine = new Map<number, number[]>();
    const all: [number, number][] = [];
    if (query) {
      const pattern = new RegExp(escape(query), "gi");
      for (const i of visible) {
        const starts = [...lines[i].text.matchAll(pattern)].map((m) => m.index);
        if (!starts.length) continue;
        starts.forEach((_, n) => all.push([i, n]));
        byLine.set(i, starts);
      }
    }
    return { hits: byLine, matches: all };
  }, [lines, visible, query]);

  useEffect(() => setCurrent(0), [matches]);
  const at = matches.length ? Math.min(current, matches.length - 1) : -1;
  useEffect(() => {
    viewer.current?.querySelector("mark[data-current]")?.scrollIntoView?.({ block: "center", inline: "nearest" });
  }, [at, matches]);
  // opened at the end: the newest lines
  useEffect(() => {
    if (text !== null && viewer.current) viewer.current.scrollTop = viewer.current.scrollHeight;
  }, [text]);

  const step = (by: number) => matches.length && setCurrent((at + by + matches.length) % matches.length);
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      setTyped("");
      setQuery("");
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (typed !== query) setQuery(typed);
      else step(e.shiftKey ? -1 : 1);
    }
  };
  const name = label.toLowerCase();
  return (
    <>
      <div className="sp-filters sp-log-search">
        <label className="sp-search-field">
          <Icon path={ICONS.search} size={16} />
          <input
            type="search"
            aria-label={`Search the ${name}`}
            placeholder={`Search the ${name}`}
            value={typed}
            onChange={(e) => setTyped(e.currentTarget.value)}
            onKeyDown={onKey}
            spellCheck={false}
            autoComplete="off"
          />
        </label>
        <span className="sp-muted sp-log-count" data-testid="log-search-count" aria-live="polite">
          {query ? (matches.length ? `${at + 1} / ${matches.length}` : "No match") : ""}
        </span>
        <span className="sp-actions">
          <button type="button" className="sp-key" aria-label="Previous match" disabled={!matches.length} onClick={() => step(-1)}>
            <Icon path={ICONS.chevronLeft} size={16} />
          </button>
          <button type="button" className="sp-key" aria-label="Next match" disabled={!matches.length} onClick={() => step(1)}>
            <Icon path={ICONS.chevronRight} size={16} />
          </button>
        </span>
        <div className="sp-segments" role="group" aria-label="Show lines">
          {LEVELS.map((l) => (
            <button key={l.key} type="button" aria-pressed={shown === l.key} data-tone={l.tone} onClick={() => setShown(l.key)}>
              {l.label}
              <span className="sp-count">{counts[l.key]}</span>
            </button>
          ))}
        </div>
      </div>
      <pre ref={viewer} className="sp-log sp-nowrap" tabIndex={0} aria-label={label}>
        {text === null
          ? "Loading…"
          : visible.length === 0
            ? "No line at this level."
            : visible.map((i) => (
                <Line
                  key={i}
                  text={lines[i].text}
                  tone={lines[i].tone}
                  hits={hits.get(i)}
                  size={query.length}
                  current={at >= 0 && matches[at][0] === i ? matches[at][1] : -1}
                />
              ))}
      </pre>
    </>
  );
}
