import type { ReactNode } from "react";
import { Icon } from "../icons";
import { NAV } from "./Sidebar";

/** The page head of ui-spec §7 (UX-PAR-03): a 48 px icon tile in the section's colour, the h1, a
 * one-line description and the primary action on the right. */
export function PageHead({
  section,
  title,
  sub,
  action,
}: {
  section: "home" | "runs" | "launch";
  title: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
}) {
  const item = NAV.find((n) => n.section === section)!;
  return (
    <header className="sp-head">
      <div className="sp-head-main">
        <span className="sp-head-tile" data-section={section}>
          <Icon path={item.icon} size={22} />
        </span>
        <div>
          <h1 className="sp-page-title">{title}</h1>
          {sub && <p className="sp-sub sp-page-sub">{sub}</p>}
        </div>
      </div>
      {action}
    </header>
  );
}
