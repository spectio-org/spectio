import { Link } from "@tanstack/react-router";
import { Icon } from "../icons";
import { NAV, marked, useMarkedItem } from "./Sidebar";

/** The phone's bottom tab bar (MLiteTabbar, G1): a floating paper bar, icon over name, on an
 * opaque backdrop that also covers the bottom inset (ui-spec §4.11). */
export function TabBar() {
  const mark = useMarkedItem();
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
            {...marked(item.to, mark)}
          >
            <Icon name={item.icon} size="nav" />
            <span lang="en">{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
