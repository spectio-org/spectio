import { Link } from "@tanstack/react-router";
import type { ServerVersion } from "../api";

/** The 0.0.1 sections, with the icons and section colours of LiteSidebar and MLiteTabbar (G1). */
export const NAV = [
  { to: "/", label: "Home", section: "home", icon: "M4 13h7V4H4z M13 20h7v-9h-7z M13 4h7v5h-7z M4 20h7v-5H4z" },
  { to: "/runs", label: "Runs", section: "runs", icon: "M5 4l14 8-14 8z" },
  { to: "/launch", label: "Launch", section: "launch", icon: "M12 3v12 M7 8l5-5 5 5 M5 21h14" },
] as const;

export function Icon({ path, size = 24 }: { path: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
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
            activeOptions={{ exact: true }}
            className="sp-nav-item"
            data-section={item.section}
          >
            <Icon path={item.icon} />
            <span className={open ? undefined : "sp-sr"}>{item.label}</span>
          </Link>
        ))}
      </div>
      <div className="sp-sidebar-foot">
        <span className="sp-status" data-down={!!down || undefined}>
          <span className="sp-dot" aria-hidden="true" />
          <span className={open ? undefined : "sp-sr"}>
            {server ? `Spectio ${server.version} · online` : down ? "Server not reached" : "Connecting…"}
          </span>
        </span>
        <span className={open ? "sp-foot-text" : "sp-sr"} role="status">
          {server
            ? `${server.executor.toUpperCase()} · server on ${server.node} · your account ${server.account}`
            : down}
        </span>
      </div>
    </nav>
  );
}
