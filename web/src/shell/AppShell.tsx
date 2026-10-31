import "./shell.css";
import { useMediaQuery } from "@mantine/hooks";
import { Outlet } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { type ServerVersion, getVersion } from "../api";
import { ServerContext } from "../server";
import { CrumbContext } from "./crumb";
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
  useEffect(() => {
    const controller = new AbortController();
    getVersion(controller.signal)
      .then(setServer)
      .catch((e: Error) => controller.signal.aborted || setDown(e.message));
    return () => controller.abort();
  }, []);

  const phone = useMediaQuery(PHONE, false, NOW) ?? false;
  const tablet = useMediaQuery(TABLET, false, NOW) ?? false;
  // The reader's own fold wins over the breakpoint's default.
  const [chosen, setChosen] = useState<boolean | null>(null);
  const open = chosen ?? !tablet;
  const [crumb, setCrumb] = useState<string | null>(null);
  const [titleRow, setTitleRow] = useState<HTMLElement | null>(null);

  return (
    <ServerContext.Provider value={server}>
      <CrumbContext.Provider value={setCrumb}>
        <LayoutContext.Provider value={{ phone, titleRow: phone ? titleRow : null }}>
          <div className="sp-shell" data-layout={phone ? "phone" : tablet ? "tablet" : "desktop"}>
            <TopBar phone={phone} server={server} down={down} crumb={crumb} titleRow={setTitleRow} />
            <div className="sp-body">
              {!phone && <Sidebar open={open} onFold={() => setChosen(!open)} server={server} down={down} />}
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
