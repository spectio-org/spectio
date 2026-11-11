import { Modal } from "@mantine/core";
import { useNavigate } from "@tanstack/react-router";
import { type KeyboardEvent, useEffect, useId, useState } from "react";
import { ApiError, getRun, listCatalog, listRuns } from "../api";
import { RUN_ID } from "../runs/RunDetailPage";

// Search in 0.0.1 (FU-P3-89; ui-spec §2 top bar note): no GET /search yet (api §5 is later), so
// the dialog asks what the API already serves: runs by name prefix (GET /runs?q=), one run by its
// exact ID (GET /runs/{id}), the catalog's pipelines (GET /catalog), and the app's pages by name.
// Results are native buttons under headings; the arrow keys move between the input and them.
// The short ID the UI shows (the last 6 characters of the run ID, `shortId`) finds its run among
// the 200 newest, in any case (FU-P3-116): the API has no ID-suffix match until GET /search.

type Group = "Runs" | "Pipelines" | "Pages";
type Go = ReturnType<typeof useNavigate>;
interface Hit {
  key: string;
  group: Group;
  label: string;
  detail: string | null;
  open: (navigate: Go) => void;
}

const GROUPS: Group[] = ["Runs", "Pipelines", "Pages"];
const KIND: Record<Group, string> = { Runs: "Run", Pipelines: "Pipeline", Pages: "Page" };
const page = (label: string, to: "/" | "/runs" | "/launch" | "/catalog" | "/environments" | "/profile"): Hit => ({
  key: to,
  group: "Pages",
  label,
  detail: null,
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

const runHit = (r: { id: string; name: string | null }): Hit => ({
  key: r.id,
  group: "Runs",
  label: r.name ?? r.id,
  detail: r.name ? r.id : null,
  open: (navigate) => navigate({ to: "/runs/$id", params: { id: r.id } }),
});

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
      hits.push({ key: p.name, group: "Pipelines", label: p.label ?? p.name, detail: p.location, open: (n) => n({ to: "/catalog/$name", params: { name: p.name } }) });
    }
  }
  hits.push(...PAGES.filter((p) => p.label.toLowerCase().includes(needle)));
  const failed = [runs, exact, bySuffix, catalog].find((r) => r.status === "rejected");
  return { hits, error: failed ? `Search failed: ${(failed.reason as Error).message}` : null };
}

/** The search dialog: full screen on the phone; Mantine's Modal is aria-modal, traps focus, closes
 * on Escape and returns focus to its opener. */
export function SearchDialog({ opened, onClose, phone }: { opened: boolean; onClose: () => void; phone: boolean }) {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<{ hits: Hit[]; error: string | null } | null>(null);
  const listId = useId();

  useEffect(() => {
    const text = q.trim();
    setFound(null);
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
  return (
    <Modal opened={opened} onClose={close} title="Search" returnFocus fullScreen={phone} size="lg">
      <div className="sp-search-dialog" onKeyDown={move}>
        <input
          type="search"
          className="sp-search-input"
          aria-label="Search runs, pipelines and pages"
          placeholder="Run name or ID, pipeline, page"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && hits[0] && open(hits[0])}
          aria-controls={listId}
          data-autofocus
        />
        <p role="status" aria-live="polite" className="sp-search-count">
          {count}
        </p>
        {found?.error && <p className="sp-search-error">{found.error}</p>}
        <div id={listId}>
          {GROUPS.map((group) => {
            const mine = hits.filter((h) => h.group === group);
            if (mine.length === 0) return null;
            return (
              <section key={group} aria-labelledby={`${listId}-${group}`}>
                <h3 id={`${listId}-${group}`} className="sp-search-group">
                  {group}
                </h3>
                <ul className="sp-search-hits">
                  {mine.map((hit) => (
                    <li key={hit.key}>
                      <button
                        type="button"
                        className="sp-search-hit"
                        aria-label={`${KIND[group]} ${hit.label}${hit.detail ? `, ${hit.detail}` : ""}`}
                        onClick={() => open(hit)}
                      >
                        <span>{hit.label}</span>
                        {hit.detail && <span className="sp-search-detail">{hit.detail}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </Modal>
  );
}
