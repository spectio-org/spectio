import { Modal } from "@mantine/core";
import { useNavigate } from "@tanstack/react-router";
import { type KeyboardEvent, useEffect, useId, useState } from "react";
import { ApiError, type Run, getRun, listCatalog, listRuns } from "../api";
import { type IconName, Icon } from "../icons";
import { RUN_ID } from "../runs/RunDetailPage";
import { TONE_ICONS } from "../runs/RunState";
import { type Tone, engineName, runWord, tone } from "../runs/stateWord";
import { EngineMark } from "./EngineMark";
import { ago } from "./NotificationsBell";
import { EmptyState } from "./States";

// Search in 0.0.1 (FU-P3-89; ui-spec §2 top bar note): no GET /search yet (api §5 is later), so
// the dialog asks what the API already serves: runs by name prefix (GET /runs?q=), one run by its
// exact ID (GET /runs/{id}), the catalog's pipelines (GET /catalog), and the app's pages by name.
// Results are native buttons under headings; the arrow keys move between the input and them.
// The short ID the UI shows (the last 6 characters of the run ID, `shortId`) finds its run among
// the 200 newest, in any case (FU-P3-116): the API has no ID-suffix match until GET /search.
// UI-06 (ui-spec §12): a spotlight panel near the top; each result is a row like a notification
// row (§12.13): a 28 px tile, line 1 the name and the state word, line 2 the engine mark and time.

type Group = "Runs" | "Pipelines" | "Pages";
type Go = ReturnType<typeof useNavigate>;
interface Hit {
  key: string;
  group: Group;
  label: string;
  detail: string | null;
  /** The tile: a run's tone and state icon, else a plain icon. */
  tile: { icon: IconName; tone?: Tone };
  /** A run's state word, in its tone. */
  word?: string;
  engine?: string | null;
  /** A run's relative time (§12.8), with its ISO stamp. */
  at?: { iso: string; text: string };
  open: (navigate: Go) => void;
}

const GROUPS: Group[] = ["Runs", "Pipelines", "Pages"];
const KIND: Record<Group, string> = { Runs: "Run", Pipelines: "Pipeline", Pages: "Page" };
const page = (label: string, to: "/" | "/runs" | "/launch" | "/catalog" | "/environments" | "/profile"): Hit => ({
  key: to,
  group: "Pages",
  label,
  detail: null,
  tile: { icon: "arrowRight" },
  open: (navigate) => navigate({ to }),
});
const PAGES = [
  page("Home", "/"),
  page("Runs", "/runs"),
  page("Launch", "/launch"),
  page("Pipelines (catalog)", "/catalog"),
  page("Environments", "/environments"),
  page("Profile", "/profile"),
];

/** A short run ID: 6 characters of the ULID alphabet (Crockford base32), in any case. */
const SHORT_ID = /^[0-9A-HJKMNP-TV-Z]{6}$/i;
const NEWEST = 200;

function runHit(r: Run): Hit {
  const t = tone(r.state);
  const iso = r.ended_at ?? r.started_at ?? r.created_at;
  return {
    key: r.id,
    group: "Runs",
    label: r.name ?? r.id,
    detail: null,
    tile: { icon: TONE_ICONS[t], tone: t },
    word: runWord(r.state),
    engine: r.workflow.engine,
    at: { iso, text: ago(iso) },
    open: (navigate) => navigate({ to: "/runs/$id", params: { id: r.id } }),
  };
}

/** The row's accessible name: "Run rnaseq-a, Running, Nextflow, 1 h ago" (§12.13). */
const hitLabel = (h: Hit): string =>
  h.group === "Runs"
    ? [`Run ${h.label}`, h.word, engineName(h.engine ?? null), h.at?.text].join(", ")
    : `${KIND[h.group]} ${h.label}${h.detail ? `, ${h.detail}` : ""}`;

/** Every hit for `q`, and the first failure's words; an aborted search throws. */
async function search(q: string, signal: AbortSignal): Promise<{ hits: Hit[]; error: string | null }> {
  const needle = q.toLowerCase();
  const short = SHORT_ID.test(q) ? q.toUpperCase() : null;
  const [runs, exact, bySuffix, catalog] = await Promise.allSettled([
    listRuns({ q, limit: 5 }, signal),
    // a 404 is no match, not a failure
    RUN_ID.test(q) ? getRun(q, signal).catch((e) => (e instanceof ApiError && e.status === 404 ? null : Promise.reject(e))) : null,
    short ? listRuns({ limit: NEWEST }, signal).then((page) => page.items.filter((r) => r.id.endsWith(short))) : [],
    listCatalog(signal),
  ]);
  if (signal.aborted) throw new DOMException("aborted", "AbortError");
  const hits: Hit[] = [];
  if (exact.status === "fulfilled" && exact.value) hits.push(runHit(exact.value));
  if (bySuffix.status === "fulfilled") hits.push(...bySuffix.value.map(runHit));
  if (runs.status === "fulfilled") hits.push(...runs.value.items.filter((r) => !hits.some((h) => h.key === r.id)).map(runHit));
  if (catalog.status === "fulfilled") {
    for (const p of catalog.value.items) {
      if (![p.name, p.label ?? "", p.location].some((s) => s.toLowerCase().includes(needle))) continue;
      hits.push({ key: p.name, group: "Pipelines", label: p.label ?? p.name, detail: p.location, tile: { icon: "layers" }, engine: p.engine, open: (n) => n({ to: "/catalog/$name", params: { name: p.name } }) });
    }
  }
  hits.push(...PAGES.filter((p) => p.label.toLowerCase().includes(needle)));
  const failed = [runs, exact, bySuffix, catalog].find((r) => r.status === "rejected");
  return { hits, error: failed ? `Search failed: ${(failed.reason as Error).message}` : null };
}

/** The search dialog: a spotlight panel near the top, full screen on the phone; Mantine's Modal is
 * aria-modal, traps focus, closes on Escape and returns focus to its opener. */
export function SearchDialog({ opened, onClose, phone }: { opened: boolean; onClose: () => void; phone: boolean }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<{ hits: Hit[]; error: string | null } | null>(null);
  const listId = useId();
  // the row Enter on the input opens (the first), or the row the arrows focused
  const [active, setActive] = useState(0);

  useEffect(() => {
    const text = q.trim();
    setFound(null);
    setActive(0);
    if (!text) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      search(text, controller.signal).then(setFound, () => {});
    }, 150);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [q]);

  const close = () => {
    setQ("");
    onClose();
  };
  const open = (hit: Hit) => {
    close();
    hit.open(navigate);
  };
  /** ArrowDown/ArrowUp move focus through the input and the result buttons, in order. */
  const move = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    const box = event.currentTarget.closest(".sp-search-dialog");
    const stops = Array.from(box?.querySelectorAll<HTMLElement>("input, .sp-search-hit") ?? []);
    const next = stops[stops.indexOf(document.activeElement as HTMLElement) + (event.key === "ArrowDown" ? 1 : -1)];
    if (next) {
      event.preventDefault();
      next.focus();
    }
  };

  const hits = found?.hits ?? [];
  const count = !found ? "" : hits.length === 0 ? "No match" : `${hits.length} result${hits.length === 1 ? "" : "s"}`;
  const ordered = GROUPS.flatMap((group) => hits.filter((h) => h.group === group));
  return (
    <Modal
      opened={opened}
      onClose={close}
      title="Search"
      withCloseButton={false}
      returnFocus
      fullScreen={phone}
      size={640}
      radius={phone ? 0 : "md"}
      yOffset="12vh"
      padding={0}
      classNames={{ header: "sp-sr", body: "sp-search-body" }}
    >
      <div className="sp-search-dialog" onKeyDown={move}>
        <div className="sp-search-bar">
          <Icon name="search" />
          <input
            type="search"
            className="sp-search-input"
            aria-label="Search runs, pipelines and pages"
            placeholder="Run name or ID, pipeline, page"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ordered[0] && open(ordered[0])}
            onFocus={() => setActive(0)}
            aria-controls={listId}
            data-autofocus
          />
          {!phone && <kbd className="sp-search-esc">Esc</kbd>}
        </div>
        <p role="status" aria-live="polite" className="sp-sr">
          {count}
        </p>
        {found?.error && <p className="sp-search-error">{found.error}</p>}
        {!q.trim() && <EmptyState icon="search">Type a run name or ID, a pipeline or a page.</EmptyState>}
        {found && hits.length === 0 && !found.error && (
          <EmptyState icon="search">No run, pipeline or page matches “{q.trim()}”.</EmptyState>
        )}
        <div id={listId} className="sp-search-results">
          {GROUPS.map((group) => {
            const mine = hits.filter((h) => h.group === group);
            if (mine.length === 0) return null;
            return (
              <section key={group} aria-labelledby={`${listId}-${group}`}>
                <h3 id={`${listId}-${group}`} className="sp-search-group">
                  {group}
                </h3>
                <ul className="sp-search-hits">
                  {mine.map((hit) => {
                    const i = ordered.indexOf(hit);
                    return (
                      <li key={hit.key}>
                        <button
                          type="button"
                          className="sp-search-hit"
                          aria-label={hitLabel(hit)}
                          data-active={i === active ? "" : undefined}
                          onFocus={() => setActive(i)}
                          onClick={() => open(hit)}
                        >
                          <span className="sp-search-tile" data-tone={hit.tile.tone}>
                            <Icon name={hit.tile.icon} />
                          </span>
                          <span className="sp-search-text">
                            <span className="sp-search-line">
                              <span className="sp-search-name">{hit.label}</span>
                              <span className="sp-search-word" data-tone={hit.tile.tone}>
                                {hit.word ?? KIND[group]}
                              </span>
                            </span>
                            {(hit.engine || hit.at || hit.detail) && (
                              <span className="sp-search-line sp-search-meta">
                                {hit.engine && <EngineMark engine={hit.engine} size={16} named />}
                                {hit.at && <time dateTime={hit.at.iso}>{hit.at.text}</time>}
                                {hit.detail && <span className="sp-search-detail">{hit.detail}</span>}
                              </span>
                            )}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}
