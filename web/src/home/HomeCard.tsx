import { type ReactNode, useState } from "react";
import type { IconName } from "../icons";
import { CardHead } from "../shell/CardHead";
import { remember, remembered } from "../shell/FoldSection";

interface Props {
  id: string;
  icon: IconName;
  title: string;
  meta?: ReactNode;
  /** The section link ("All runs →"), in the head at the right. */
  actions?: ReactNode;
  children: ReactNode;
}

/** A Home card (ui-spec §12.7, UI-07): the shared CardHead and a body that folds; the choice is
 * remembered for Home as FoldSection does. */
export function HomeCard({ id, icon, title, meta, actions, children }: Props) {
  const [open, setOpen] = useState(() => remembered("home", id) ?? true);
  const toggle = () => {
    setOpen(!open);
    remember("home", id, !open);
  };
  return (
    <section className="sp-card sp-home-card" aria-labelledby={`${id}-title`}>
      <CardHead id={id} icon={icon} title={title} meta={meta} actions={actions} open={open} onToggle={toggle} />
      <div id={`${id}-body`} className="sp-home-card-body" hidden={!open}>
        {open && children}
      </div>
    </section>
  );
}
