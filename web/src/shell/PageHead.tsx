import { ActionIcon, Menu } from "@mantine/core";
import type { ReactElement, ReactNode } from "react";
import { Icon, type IconName } from "../icons";
import { PhoneTitle, usePhone } from "./layout";
import { NAV } from "./Sidebar";

/** One entry of the "More actions" menu. A destructive one is drawn last, after a divider. */
export interface MoreAction {
  label: string;
  onClick: () => void;
  icon?: IconName;
  destructive?: boolean;
}

interface Props {
  section: (typeof NAV)[number]["section"];
  title: ReactNode;
  sub?: ReactNode;
  /** The tile's icon when it is not the section's (Profile). */
  icon?: IconName;
  /** The one filled button of the view, at the far right (ui-spec §12.4): one element, never a list. */
  primary?: ReactElement;
  /** Default buttons before it, two at most; more go to `more`. */
  secondary?: [ReactElement] | [ReactElement, ReactElement];
  /** The rest, in a "…" menu named "More actions". */
  more?: MoreAction[];
  /** The phone (ui-spec §4.11, §12.5): the title and subtitle in the top bar's title row (default),
   * the title only there and the subtitle in the page ("title"), or the head kept in the page,
   * as Home keeps its greeting ("page"). */
  phoneTitle?: "title-and-sub" | "title" | "page";
  /** The phone: the primary in the bar pinned above the tab bar (default), or not at all when the
   * page has its own pinned bar (Launch) or the tab bar is the action (Runs). */
  phonePrimary?: "bar" | "none";
}

function MoreMenu({ items }: { items: MoreAction[] }) {
  const plain = items.filter((i) => !i.destructive);
  const danger = items.filter((i) => i.destructive);
  const item = (a: MoreAction) => (
    <Menu.Item
      key={a.label}
      onClick={a.onClick}
      data-destructive={a.destructive || undefined}
      className={a.destructive ? "sp-menu-danger" : undefined}
      leftSection={a.icon && <Icon name={a.icon} />}
    >
      {a.label}
    </Menu.Item>
  );
  return (
    <Menu position="bottom-end" withinPortal>
      <Menu.Target>
        <ActionIcon variant="default" size="lg" aria-label="More actions">
          <Icon name="more" />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        {plain.map(item)}
        {plain.length > 0 && danger.length > 0 && <Menu.Divider />}
        {danger.map(item)}
      </Menu.Dropdown>
    </Menu>
  );
}

/** The page head of ui-spec §12.5 (UI-03): the 48 px tile in the section's colour, the h1 with a
 * one-line subtitle, then the actions at the right: secondaries, "More actions", the primary. */
export function PageHead({ section, title, sub, icon, primary, secondary, more, phoneTitle = "title-and-sub", phonePrimary = "bar" }: Props) {
  const phone = usePhone();
  const subLine = sub && <p className="sp-sub sp-page-sub">{sub}</p>;
  const bar = phone && phonePrimary === "bar" && primary && <div className="sp-head-bar">{primary}</div>;
  // On the phone the secondaries and "More actions" stay in the page; only the primary moves to the bar.
  const actions = (secondary || more?.length || (!phone && primary)) && (
    <div className="sp-head-actions">
      {secondary}
      {more && more.length > 0 && <MoreMenu items={more} />}
      {!phone && primary}
    </div>
  );
  if (phone && phoneTitle !== "page") {
    const both = phoneTitle === "title-and-sub";
    return (
      <>
        <PhoneTitle title={title} sub={both ? sub : undefined} />
        {!both && subLine}
        {actions}
        {bar}
      </>
    );
  }
  return (
    <>
      <header className="sp-head">
        <div className="sp-head-main">
          <span className="sp-head-tile" data-section={section} aria-hidden="true">
            <Icon name={icon ?? NAV.find((n) => n.section === section)!.icon} size="tile" />
          </span>
          <div className="sp-head-text">
            <h1 className="sp-page-title" tabIndex={-1}>
              {title}
            </h1>
            {subLine}
          </div>
        </div>
        {actions}
      </header>
      {bar}
    </>
  );
}
