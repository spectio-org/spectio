import { Link } from "@tanstack/react-router";
import { Icon } from "../icons";
import { NAV } from "./Sidebar";

/** The phone's bottom tab bar (MLiteTabbar, G1): a floating paper bar, icon over name, on an
 * opaque backdrop that also covers the bottom inset (ui-spec §4.11). */
export function TabBar() {
  return (
    <div className="sp-tabbar">
      <nav aria-label="Main" data-shell="tabbar">
        {NAV.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            activeOptions={{ exact: item.exact }}
            className="sp-tab"
            data-section={item.section}
          >
            <Icon path={item.icon} size={22} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
