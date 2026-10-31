import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useState } from "react";
import { type ServerVersion, runsSummary } from "../api";
import { ICONS, Icon } from "../icons";
import { useFrames } from "../live";
import { ACTIVE, executorLabel } from "../runs/stateWord";

/** The 0.0.1 sections, with the icons and section colours of LiteSidebar and MLiteTabbar (G1).
 * Home is active on `/` only; Runs and Launch also on the pages under them (UX-PAR-06). */
export const NAV = [
  { to: "/", label: "Home", section: "home", icon: ICONS.home, exact: true },
  { to: "/runs", label: "Runs", section: "runs", icon: ICONS.runs, exact: false },
  { to: "/launch", label: "Launch", section: "launch", icon: ICONS.launch, exact: false },
] as const;

/** The number of active runs, from `GET /runs:summary`, refreshed on stream frames (UX-PAR-07). */
function useActiveCount(): number {
  const [count, setCount] = useState(0);
  const load = useCallback(() => {
    runsSummary()
      .then((s) => setCount((s.groups ?? []).filter((g) => ACTIVE.includes(g.key)).reduce((n, g) => n + g.count, 0)))
      .catch(() => setCount(0));
  }, []);
  useEffect(load, [load]);
  useFrames(load);
  return count;
}

const FOLD = "M4 5h16v14H4z M9 5v14 M16 10l-2 2 2 2";
const UNFOLD = "M4 5h16v14H4z M9 5v14 M14 10l2 2-2 2";

interface Props {
  open: boolean;
  onFold: () => void;
  server: ServerVersion | null;
  down: string | null;
}

/** The foldable sidebar: "Workspace" eyebrow, the sections, server status in its foot. Folded,
 * it is the icon rail; labels stay in the accessibility tree, so no link loses its name. */
export function Sidebar({ open, onFold, server, down }: Props) {
  const active = useActiveCount();
  return (
    <nav className="sp-sidebar" data-open={open} aria-label="Main">
      <div className="sp-sidebar-head">
        {open && <span className="sp-eyebrow">Workspace</span>}
        <button
          type="button"
          className="sp-key sp-fold"
          aria-expanded={open}
          aria-controls="sp-nav-items"
          aria-label={open ? "Fold the sidebar" : "Unfold the sidebar"}
          onClick={onFold}
        >
          <Icon path={open ? FOLD : UNFOLD} size={19} />
        </button>
      </div>
      <div id="sp-nav-items" className="sp-nav-items">
        {NAV.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            activeOptions={{ exact: item.exact }}
            className="sp-nav-item"
            data-section={item.section}
          >
            <Icon path={item.icon} />
            <span className={open ? undefined : "sp-sr"}>{item.label}</span>
            {item.to === "/runs" && active > 0 && (
              <>
                <span className="sp-badge" aria-hidden="true">
                  {active}
                </span>
                <span className="sp-sr">, {active} active {active === 1 ? "run" : "runs"}</span>
              </>
            )}
          </Link>
        ))}
      </div>
      <div className="sp-sidebar-foot">
        <span className="sp-status" data-down={!!down || undefined}>
          {server ? <Icon path={ICONS.check} size={14} stroke={2.2} /> : <span className="sp-dot" aria-hidden="true" />}
          <span className={open ? undefined : "sp-sr"}>
            {server ? `Spectio ${server.version} · online` : down ? "Server not reached" : "Connecting…"}
          </span>
        </span>
        <span className={open ? "sp-foot-text" : "sp-sr"} role="status">
          {server
            ? `${executorLabel(server.executor)} · server on ${server.node} · your account ${server.account}`
            : down}
        </span>
      </div>
    </nav>
  );
}
