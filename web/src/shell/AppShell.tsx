import "./shell.css";
import { useMediaQuery } from "@mantine/hooks";
import { Outlet } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { type ServerVersion, getVersion } from "../api";
import { useLiveStatus } from "../live";
import { ServerContext } from "../server";
import { CrumbContext, NO_CRUMB, type PageCrumb } from "./crumb";
import { LayoutContext } from "./layout";
import { Sidebar } from "./Sidebar";
import { TabBar } from "./TabBar";
import { TopBar } from "./TopBar";

// The breakpoints of ui-spec §4.11: phone < 768 px (tab bar), tablet 768–1199 px (sidebar folded
// to the rail by default), desktop ≥ 1200 px. Read at first render, so a phone never shows the
// sidebar for a frame.
export const PHONE = "(max-width: 767.98px)";
export const TABLET = "(max-width: 1199.98px)";
const NOW = { getInitialValueInEffect: false };

/** The Paper shell (ui-spec §7): top bar, foldable sidebar or phone tab bar, and the page. */
export function AppShell() {
  const [server, setServer] = useState<ServerVersion | null>(null);
  const [down, setDown] = useState<string | null>(null);
  // The status follows the live stream (FU-P3-79): while it reconnects the server is not
  // reached, and each reconnection reads GET /version again, as the server may have changed.
  const live = useLiveStatus();
  const [reads, setReads] = useState(0);
  const lost = useRef(false);
  useEffect(() => {
    if (live === "reconnecting") lost.current = true;
    else if (live === "live" && (lost.current || down)) {
      lost.current = false;
      setReads((n) => n + 1);
    }
    // `down` is read, not watched: a failed re-read while live must not trigger another one.
  }, [live]);
  useEffect(() => {
    const controller = new AbortController();
    getVersion(controller.signal)
      .then((v) => {
        setServer(v);
        setDown(null);
      })
      .catch((e: Error) => controller.signal.aborted || setDown(e.message));
    return () => controller.abort();
  }, [reads]);
  const reached = live === "reconnecting" || down ? null : server;
  const unreached = live === "reconnecting" ? "The live stream is reconnecting." : down;

  const phone = useMediaQuery(PHONE, false, NOW) ?? false;
  const tablet = useMediaQuery(TABLET, false, NOW) ?? false;
  // The reader's own fold wins over the breakpoint's default.
  const [chosen, setChosen] = useState<boolean | null>(null);
  const open = chosen ?? !tablet;
  const [crumb, setCrumb] = useState<PageCrumb>(NO_CRUMB);
  const [titleRow, setTitleRow] = useState<HTMLElement | null>(null);

  return (
    <ServerContext.Provider value={server}>
      <CrumbContext.Provider value={setCrumb}>
        <LayoutContext.Provider value={{ phone, titleRow: phone ? titleRow : null }}>
          <div className="sp-shell" data-layout={phone ? "phone" : tablet ? "tablet" : "desktop"}>
            <TopBar phone={phone} server={reached} down={unreached} crumb={crumb} titleRow={setTitleRow} />
            <div className="sp-body">
              {!phone && <Sidebar open={open} onFold={() => setChosen(!open)} server={reached} down={unreached} />}
              <main className="sp-main">
                <Outlet />
              </main>
            </div>
            {phone && <TabBar />}
          </div>
        </LayoutContext.Provider>
      </CrumbContext.Provider>
    </ServerContext.Provider>
  );
}
