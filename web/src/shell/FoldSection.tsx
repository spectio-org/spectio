import { type ReactNode, useState } from "react";
import { ICONS, Icon } from "../icons";

// A titled section that folds (ui-spec §4.4 "Open sections", UX-318; UX-PAR-02), as on the lite
// boards: the h2 holds a native button (aria-expanded, aria-controls) with a light line icon in a
// tile, the title, a one-line summary shown only while folded, and a chevron that turns. Which
// sections are open is remembered per screen in the browser's storage, a convenience only.

const key = (screen: string, id: string) => `spectio-open:${screen}:${id}`;

function remembered(screen: string, id: string): boolean | null {
  try {
    const value = window.localStorage.getItem(key(screen, id));
    return value === null ? null : value === "1";
  } catch {
    return null;
  }
}

function remember(screen: string, id: string, open: boolean) {
  try {
    window.localStorage.setItem(key(screen, id), open ? "1" : "0");
  } catch {
    // storage blocked: the choice lasts for this page only
  }
}

interface Props {
  id: string;
  /** The screen whose choices this section shares: "home", "run". */
  screen: string;
  icon: string;
  title: string;
  /** Shown while folded: "8 stages · 4 running", "4 set at launch". */
  summary?: ReactNode;
  defaultOpen?: boolean;
  /** A card ("sp-card") or a plain section. */
  card?: boolean;
  children: ReactNode;
}

export function FoldSection({ id, screen, icon, title, summary, defaultOpen = true, card = false, children }: Props) {
  const [open, setOpen] = useState(() => remembered(screen, id) ?? defaultOpen);
  const toggle = () => {
    setOpen(!open);
    remember(screen, id, !open);
  };
  return (
    <section className={card ? "sp-foldsec sp-card" : "sp-foldsec"} aria-labelledby={`${id}-title`} data-open={open}>
      <h2 className="sp-fold-head">
        <button type="button" className="sp-fold-btn" aria-expanded={open} aria-controls={`${id}-body`} onClick={toggle}>
          <span className="sp-fold-tile">
            <Icon path={icon} size={17} stroke={1.6} />
          </span>
          <span id={`${id}-title`} className="sp-fold-title">
            {title}
          </span>
          <span className="sp-grow" />
          {!open && summary && <span className="sp-fold-sum">{summary}</span>}
          <span className="sp-fold-chev">
            <Icon path={ICONS.chevronDown} size={16} stroke={2} />
          </span>
        </button>
      </h2>
      <div id={`${id}-body`} className="sp-fold-body" hidden={!open}>
        {open && children}
      </div>
    </section>
  );
}
