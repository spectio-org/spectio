import { type KeyboardEvent, type ReactNode, memo, useEffect, useMemo, useRef, useState } from "react";
import { ActionIcon, Button, TextInput, Tooltip } from "@mantine/core";
import { Icon, type IconName } from "../icons";
import { SkeletonRows } from "../shell/States";
import { Toolbar } from "../shell/Toolbar";

// The run's log viewer (LiteRunLogs; P3-parD, Thomas 2026-10-31: "logs pas searchable"): the lines
// tinted by level, a level filter, and a search whose matches are marked, with an "n / m" counter,
// previous and next (Enter, Shift+Enter) and Escape to clear. The query lands 150 ms after typing;
// each line is a memoised component, so a keystroke or a step re-renders only the lines it changes.

/** A log's lines; a final newline ends the last line, it does not start an empty one. */
const splitLines = (text: string) => text.replace(/\n$/, "").split("\n");

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

/** One line, its matches marked; `current` is the index of the current match in `hits`, or -1.
 * `n`: its number, in a gutter that is aria-hidden and not selected, so not copied. */
const Line = memo(function Line({ text, tone, hits = [], size, current, n }: { text: string; tone?: string; hits?: number[]; size: number; current: number; n?: number }) {
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
  if (n !== undefined) {
    return (
      <span className="sp-log-row" data-tone={tone}>
        <span className="sp-log-n" data-gutter aria-hidden="true">
          {n}
        </span>
        <span>
          {parts}
          {"\n"}
        </span>
      </span>
    );
  }
  return (
    <span data-tone={tone}>
      {parts}
      {"\n"}
    </span>
  );
});

/** An icon-only toolbar action (ui-spec §12.4): named by `label`, which its tooltip shows on hover
 * and focus; `pressed` makes it a toggle; `href` makes it a link that opens a new tab. */
export function ToolButton({ label, icon, pressed, onClick, disabled, href }: { label: string; icon: IconName; pressed?: boolean; onClick?: () => void; disabled?: boolean; href?: string }) {
  const link = href ? ({ component: "a", href, target: "_blank", rel: "noopener noreferrer" } as const) : {};
  return (
    <Tooltip label={label} withinPortal={false}>
      <ActionIcon variant={pressed ? "light" : "default"} size="lg" aria-label={label} aria-pressed={pressed} onClick={onClick} disabled={disabled} {...link}>
        <Icon name={icon} />
      </ActionIcon>
    </Tooltip>
  );
}

/** A log's lines, each tinted by its level (the Summary's last lines). */
export function LogLines({ text }: { text: string }) {
  return splitLines(text).map((line, i) => <Line key={i} text={line} tone={level(line)} size={0} current={-1} />);
}

/** The whole viewer: one toolbar (ui-spec §12.6: search, the stream and level filters, the match
 * counter, then the actions), then the lines. A run log opens at its end, follows it (Follow the
 * end) and has its own Wrap lines; the file preview (ui-spec §4.4.1) passes `start: "top"`, `levels`
 * only for .log, .out and .err, `gutterFrom` (the first line's number; no gutter for an End
 * read), its own `wrap`, and on the phone `searchButton`: the search behind a Search button.
 * `filters` and `actions` join the toolbar; `placeholder` (an empty or error state) replaces the
 * lines, and while `text` is null skeleton lines do (ui-spec §12.12). */
export function LogViewer({
  text,
  label,
  start = "end",
  levels = true,
  gutterFrom,
  wrap,
  searchButton = false,
  filters,
  actions,
  placeholder,
}: {
  text: string | null;
  label: string;
  start?: "top" | "end";
  levels?: boolean;
  gutterFrom?: number;
  wrap?: boolean;
  searchButton?: boolean;
  filters?: ReactNode;
  actions?: ReactNode;
  placeholder?: ReactNode;
}) {
  const [wrapping, setWrapping] = useState(false);
  const [follow, setFollow] = useState(start === "end");
  const wrapped = wrap ?? wrapping;
  const [typed, setTyped] = useState("");
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState<Level>("all");
  const [current, setCurrent] = useState(0);
  const [searching, setSearching] = useState(false);
  const open = !searchButton || searching; // a desktop always shows the field; the phone, once Search is pressed
  const viewer = useRef<HTMLPreElement>(null);
  const field = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setQuery(typed), 150);
    return () => clearTimeout(timer);
  }, [typed]);

  const lines = useMemo(() => splitLines(text ?? "").map((line) => ({ text: line, tone: levels ? level(line) : undefined })), [text, levels]);
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
  // a log opens at the end, the newest lines, and stays there while Follow the end is on
  useEffect(() => {
    if (follow && text !== null && viewer.current) viewer.current.scrollTop = viewer.current.scrollHeight;
  }, [text, follow]);

  useEffect(() => {
    if (searching) field.current?.focus(); // Search pressed: focus moves into the field
  }, [searching]);

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
  const frame = placeholder ?? (text === null ? <SkeletonRows rows={6} height={18} label={`Loading the ${name}…`} /> : null);
  return (
    <>
      <Toolbar
        label={`${label} tools`}
        search={
          <>
            {searchButton && (
              // the style of Wrap lines beside it (FU-P3-104)
              <Button variant="default" size="xs" aria-expanded={open} onClick={() => setSearching(!open)}>
                Search
              </Button>
            )}
            {open && (
              <TextInput
                ref={field}
                type="search"
                size="sm"
                aria-label={`Search the ${name}`}
                placeholder={`Search the ${name}`}
                value={typed}
                onChange={(e) => setTyped(e.currentTarget.value)}
                onKeyDown={onKey}
                spellCheck={false}
                autoComplete="off"
                leftSection={<Icon name="search" />}
              />
            )}
          </>
        }
        filters={
          <>
            {filters}
            {levels && !frame && (
              <div className="sp-segments sp-log-levels" role="group" aria-label="Show lines">
                {LEVELS.map((l) => (
                  <button key={l.key} type="button" aria-pressed={shown === l.key} data-tone={l.tone} onClick={() => setShown(l.key)}>
                    {l.label}
                    <span className="sp-count">{counts[l.key]}</span>
                  </button>
                ))}
              </div>
            )}
          </>
        }
        caption={
          open && (
            <span className="sp-log-count" data-testid="log-search-count" aria-live="polite">
              {query ? (matches.length ? `${at + 1} / ${matches.length}` : "No match") : ""}
            </span>
          )
        }
        actions={
          <span className="sp-actions">
            {query && (
              <>
                <ToolButton label="Previous match" icon="chevronLeft" disabled={!matches.length} onClick={() => step(-1)} />
                <ToolButton label="Next match" icon="chevronRight" disabled={!matches.length} onClick={() => step(1)} />
              </>
            )}
            {wrap === undefined && <ToolButton label="Wrap lines" icon="wrap" pressed={wrapping} onClick={() => setWrapping(!wrapping)} />}
            {start === "end" && <ToolButton label="Follow the end" icon="follow" pressed={follow} onClick={() => setFollow(!follow)} />}
            {actions}
          </span>
        }
      />
      {frame ? (
        <div className="sp-log-frame">{frame}</div>
      ) : (
        <pre ref={viewer} className={wrapped ? "sp-log" : "sp-log sp-nowrap"} data-wrap={wrapped || undefined} tabIndex={0} aria-label={label}>
          {visible.length === 0
            ? "No line at this level."
            : visible.map((i) => (
                <Line
                  key={i}
                  text={lines[i].text}
                  tone={lines[i].tone}
                  hits={hits.get(i)}
                  size={query.length}
                  current={at >= 0 && matches[at][0] === i ? matches[at][1] : -1}
                  n={gutterFrom === undefined ? undefined : gutterFrom + i}
                />
              ))}
        </pre>
      )}
    </>
  );
}
