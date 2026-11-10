import { useComputedColorScheme, useMantineColorScheme } from "@mantine/core";
import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import type { ServerVersion } from "../api";
import { ICONS, Icon } from "../icons";
import type { PageCrumb } from "./crumb";
import { NotificationsBell } from "./NotificationsBell";
import { SearchDialog } from "./SearchDialog";

type To = "/" | "/runs" | "/launch" | "/environments" | "/catalog";
interface Crumb {
  label: string;
  to?: To;
}

const SECTIONS: Record<string, { label: string; to: To }> = {
  runs: { label: "Runs", to: "/runs" },
  launch: { label: "Launch", to: "/launch" },
  environments: { label: "Environments", to: "/environments" },
};

/** The Catalog pages are Launch's, without a `NAV` item (ui-spec §4.7.1): Home › Launch › Catalog. */
const CATALOG: Crumb[] = [SECTIONS.launch, { label: "Catalog", to: "/catalog" }];

const RUN_PAGES: Record<string, string> = { report: "Report", results: "Results", workdir: "Work directory" };

/** Home > section > item, from the path; every crumb but the last is a link. The URL's own text
 * is never shown (SEC-P3G4-02): an item reads `item`, the page's label (a run's name from the
 * API), else "Run" under /runs, else "Not found"; a run's report viewer ends with "Report", its
 * results browser with "Results", a work directory with "Work directory", and a file page below
 * either with `file`, the name `stat` answered (never the URL's `path`), "File" until then: the run
 * is named once (FU-P3-104, CR-P3FU104-01). */
export function crumbsFor(pathname: string, item: string | null = null, file: string | null = null): Crumb[] {
  const crumbs: Crumb[] = [{ label: "Home", to: "/" }];
  let previous = "";
  for (const segment of pathname.split("/").filter(Boolean)) {
    if (crumbs.length === 1 && segment === "catalog") {
      crumbs.push(...CATALOG);
      continue;
    }
    const tool =
      crumbs[1]?.to !== "/runs"
        ? undefined
        : crumbs.length === 3 && Object.hasOwn(RUN_PAGES, segment)
          ? RUN_PAGES[segment]
          : crumbs.length === 4 && segment === "file"
            ? (file ?? "File")
            : undefined;
    crumbs.push((crumbs.length === 1 ? SECTIONS[segment] : undefined) ?? { label: tool ?? item ?? (previous === "runs" ? "Run" : "Not found") });
    previous = segment;
  }
  return crumbs.map((crumb, i) => (i === crumbs.length - 1 ? { label: crumb.label } : crumb));
}

function Breadcrumbs({ crumb }: { crumb: PageCrumb }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const crumbs = crumbsFor(pathname, crumb.item, crumb.file);
  return (
    <nav aria-label="Breadcrumb" className="sp-crumbs">
      <ol>
        {crumbs.map((crumb, i) => (
          <li key={i}>
            {i > 0 && <Icon path={ICONS.chevronRight} size={14} />}
            {crumb.to ? (
              // exact: a section crumb above the page is never "current" (UX-PAR-06)
              <Link to={crumb.to} activeOptions={{ exact: true }}>
                {crumb.label}
              </Link>
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

const SEARCH = ICONS.search;
const MOON = "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z";
const SUN = "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 1v2 M12 21v2 M4.2 4.2l1.4 1.4 M18.4 18.4l1.4 1.4 M1 12h2 M21 12h2 M4.2 19.8l1.4-1.4 M18.4 5.6l1.4-1.4";
export const PERSON = "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0";

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

/** The avatar: a link to the Profile page (ui-spec §4.10.1, FU-P3-112). */
function Avatar() {
  return (
    <Link to="/profile" className="sp-key sp-avatar" aria-label="Profile">
      <span className="sp-key-face">
        <Icon path={PERSON} size={19} />
      </span>
    </Link>
  );
}

interface Props {
  phone: boolean;
  server: ServerVersion | null;
  down: string | null;
  crumb: PageCrumb;
  /** Receives the phone's title row, where a page puts its h1 (UX-PAR-08). */
  titleRow: (row: HTMLElement | null) => void;
}

/** The floating top bar of the Paper shell (LiteTopbar), or its compact phone form (MLiteTopbar). */
export function TopBar({ phone, server, down, crumb, titleRow }: Props) {
  const [searching, setSearching] = useState(false);
  // ⌘K / Ctrl+K opens the search from anywhere (FU-P3-89)
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearching(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const dialog = <SearchDialog opened={searching} onClose={() => setSearching(false)} phone={phone} />;
  if (phone) {
    const node = server ? `Server on ${server.node}, online` : down ? "Server not reached" : "Connecting";
    return (
      <header className="sp-mtopbar">
        <div className="sp-mtopbar-row">
          <Link to="/" className="sp-home" aria-label="Spectio, home">
            <Mark width={34} />
            <span className="sp-word">Spectio</span>
          </Link>
          <span className="sp-grow" />
          <span className="sp-node" role="img" aria-label={node} data-down={!!down || undefined}>
            <span className="sp-dot" aria-hidden="true" />
            <span aria-hidden="true">{server?.node ?? (down ? "offline" : "…")}</span>
          </span>
          <button type="button" className="sp-key" aria-label="Search runs, pipelines and pages" onClick={() => setSearching(true)}>
            <span className="sp-key-face">
              <Icon path={SEARCH} size={19} />
            </span>
          </button>
          <NotificationsBell phone className="sp-key sp-narrow-hide" />
          <ThemeSwitch />
          <Avatar />
        </div>
        {/* The page's title row (PhoneTitle); hidden while empty, as on Home (MLiteHome). */}
        <div className="sp-mtitle" ref={titleRow} />
        {dialog}
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
      <Breadcrumbs crumb={crumb} />
      <button type="button" className="sp-search" aria-label="Search runs, pipelines and pages" aria-keyshortcuts="Meta+K Control+K" onClick={() => setSearching(true)}>
        <Icon path={SEARCH} size={16} />
        <span className="sp-search-text">Search</span>
        <kbd aria-hidden="true">⌘K</kbd>
      </button>
      <NotificationsBell phone={false} />
      <ThemeSwitch />
      <Avatar />
      {dialog}
    </header>
  );
}
