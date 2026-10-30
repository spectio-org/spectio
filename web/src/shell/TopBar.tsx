import { useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { Link, useRouterState } from "@tanstack/react-router";
import type { ServerVersion } from "../api";
import { Icon } from "./Sidebar";

type To = "/" | "/runs" | "/launch";
interface Crumb {
  label: string;
  to?: To;
}

const SECTIONS: Record<string, { label: string; to: To }> = {
  runs: { label: "Runs", to: "/runs" },
  launch: { label: "Launch", to: "/launch" },
};

/** The router decodes the path but leaves %25, %5C and malformed sequences such as %E0 as they are. */
function label(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

/** Home > section > item, from the path; every crumb but the last is a link. */
export function crumbsFor(pathname: string): Crumb[] {
  const crumbs: Crumb[] = [{ label: "Home", to: "/" }];
  for (const segment of pathname.split("/").filter(Boolean)) {
    crumbs.push(SECTIONS[segment] ?? { label: label(segment) });
  }
  return crumbs.map((crumb, i) => (i === crumbs.length - 1 ? { label: crumb.label } : crumb));
}

function Breadcrumbs() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const crumbs = crumbsFor(pathname);
  return (
    <nav aria-label="Breadcrumb" className="sp-crumbs">
      <ol>
        {crumbs.map((crumb, i) => (
          <li key={i}>
            {i > 0 && <Icon path="M9 6l6 6-6 6" size={14} />}
            {crumb.to ? (
              <Link to={crumb.to}>{crumb.label}</Link>
            ) : (
              <span aria-current="page">{crumb.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

function Mark({ width }: { width: number }) {
  return (
    <svg width={width} height={width / 2} viewBox="0 0 200 100" aria-hidden="true" className="sp-mark">
      <path fill="#5A4FCF" d="M86.09 94.24L4.17 94.24A96 96 0 0 1 28.17 36.31Z" />
      <path fill="#8B5CF6" d="M94.24 86.09L36.31 28.17A96 96 0 0 1 94.24 4.17Z" />
      <path fill="#EC5F87" d="M105.76 86.09L105.76 4.17A96 96 0 0 1 163.69 28.17Z" />
      <path fill="#F9A947" d="M113.91 94.24L171.83 36.31A96 96 0 0 1 195.83 94.24Z" />
    </svg>
  );
}

const SEARCH = "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4";
const BELL = "M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8 M10 20a2 2 0 0 0 4 0";
const MOON = "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z";
const SUN = "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 1v2 M12 21v2 M4.2 4.2l1.4 1.4 M18.4 18.4l1.4 1.4 M1 12h2 M21 12h2 M4.2 19.8l1.4-1.4 M18.4 5.6l1.4-1.4";
const PERSON = "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0";

/** A native switch: the label stays "Dark theme", `aria-checked` says whether it is on. */
function ThemeSwitch() {
  const { setColorScheme } = useMantineColorScheme();
  const dark = useComputedColorScheme("light") === "dark";
  return (
    <button
      type="button"
      className="sp-key"
      role="switch"
      aria-checked={dark}
      aria-label="Dark theme"
      onClick={() => setColorScheme(dark ? "light" : "dark")}
    >
      <Icon path={dark ? SUN : MOON} size={19} />
    </button>
  );
}

/** 0.0.1 has no search, notifications or accounts: disabled placeholders with their names (G1). */
function Placeholder({ name, path, className = "sp-key" }: { name: string; path: string; className?: string }) {
  return (
    <button type="button" className={className} disabled aria-label={`${name} (not in 0.0.1)`}>
      <span className="sp-key-face">
        <Icon path={path} size={19} />
      </span>
    </button>
  );
}

interface Props {
  phone: boolean;
  server: ServerVersion | null;
  down: string | null;
}

/** The floating top bar of the Paper shell (LiteTopbar), or its compact phone form (MLiteTopbar). */
export function TopBar({ phone, server, down }: Props) {
  if (phone) {
    const node = server ? `Server on ${server.node}, online` : down ? "Server not reached" : "Connecting";
    return (
      <header className="sp-mtopbar">
        <Link to="/" className="sp-home" aria-label="Spectio, home">
          <Mark width={34} />
          <span className="sp-word">Spectio</span>
        </Link>
        <span className="sp-grow" />
        <span className="sp-node" role="img" aria-label={node} data-down={!!down || undefined}>
          <span className="sp-dot" aria-hidden="true" />
          <span aria-hidden="true">{server?.node ?? (down ? "offline" : "…")}</span>
        </span>
        <Placeholder name="Search" path={SEARCH} className="sp-key sp-narrow-hide" />
        <Placeholder name="Notifications" path={BELL} className="sp-key sp-narrow-hide" />
        <ThemeSwitch />
        <Placeholder name="Account" path={PERSON} className="sp-key sp-avatar" />
      </header>
    );
  }
  return (
    <header className="sp-topbar">
      <Link to="/" className="sp-home" aria-label="Spectio, home">
        <Mark width={44} />
        <span className="sp-word">Spectio</span>
      </Link>
      <span className="sp-rule" aria-hidden="true" />
      <Breadcrumbs />
      <button type="button" className="sp-search" disabled aria-label="Search (not in 0.0.1)">
        <Icon path={SEARCH} size={16} />
        <span className="sp-search-text">Search (not in 0.0.1)</span>
        <kbd>⌘K</kbd>
      </button>
      <Placeholder name="Notifications" path={BELL} />
      <ThemeSwitch />
      <Placeholder name="Account" path={PERSON} className="sp-key sp-avatar" />
    </header>
  );
}
