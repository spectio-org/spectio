import { ActionIcon } from "@mantine/core";
import type { ReactNode } from "react";
import { Icon, type IconName } from "../icons";

interface Props {
  /** The card's id: the title is `<id>-title`, the body the toggle controls `<id>-body`. */
  id: string;
  icon: IconName;
  title: string;
  /** A meta line or summary in sm muted text: "5 runs", "8 stages · 4 running". */
  meta?: ReactNode;
  /** The card's actions or its section link ("All runs →"), at the right. */
  actions?: ReactNode;
  open: boolean;
  onToggle: () => void;
}

/** The 44 px head of a card (ui-spec §12.7, UI-03): a 28 px tile with a 16 px icon, the h3 title
 * and its meta line, the actions, then the fold chevron, a native button named by the title with
 * aria-expanded and aria-controls (§4.4 "Open sections"). The card keeps the open state. */
export function CardHead({ id, icon, title, meta, actions, open, onToggle }: Props) {
  return (
    <div className="sp-cardhead" data-open={open}>
      <span className="sp-cardhead-tile" aria-hidden="true">
        <Icon name={icon} />
      </span>
      <div className="sp-cardhead-text">
        <h3 id={`${id}-title`} className="sp-cardhead-title">
          {title}
        </h3>
        {meta && <p className="sp-cardhead-meta">{meta}</p>}
      </div>
      {actions && <div className="sp-cardhead-actions">{actions}</div>}
      <ActionIcon variant="subtle" size="lg" className="sp-cardhead-fold" aria-labelledby={`${id}-title`} aria-expanded={open} aria-controls={`${id}-body`} onClick={onToggle}>
        <Icon name="chevronDown" />
      </ActionIcon>
    </div>
  );
}
