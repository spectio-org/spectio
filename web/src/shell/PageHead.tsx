import type { ReactNode } from "react";
import { Icon } from "../icons";
import { PhoneTitle, usePhone } from "./layout";
import { NAV } from "./Sidebar";

/** The page head of ui-spec §7 (UX-PAR-03): a 48 px icon tile in the section's colour, the h1, a
 * one-line description and the primary action on the right. With `phoneBar`, the phone shows the
 * title in the top bar's second row instead (MLiteRuns, MLiteLaunch; UX-PAR-08), with the
 * subtitle too when it is "title-and-sub"; the tab bar is the action there. */
export function PageHead({
  section,
  title,
  sub,
  action,
  phoneBar,
}: {
  section: "home" | "runs" | "launch";
  title: ReactNode;
  sub?: ReactNode;
  action?: ReactNode;
  phoneBar?: "title" | "title-and-sub";
}) {
  const phone = usePhone();
  const item = NAV.find((n) => n.section === section)!;
  if (phone && phoneBar) {
    const both = phoneBar === "title-and-sub";
    return (
      <>
        <PhoneTitle title={title} sub={both ? sub : undefined} />
        {!both && sub && <p className="sp-sub sp-page-sub">{sub}</p>}
      </>
    );
  }
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
