// The details of a step or a link on the graph (issue #160; ui-spec §4.14), docked beside the map
// rather than over it (Thomas, 2026-11-11); a full-screen sheet on a phone.
import { Drawer } from "@mantine/core";
import { type ReactNode, useEffect, useRef } from "react";
import { Icon } from "../../icons";
import { usePhone } from "../../shell/layout";
import { GICONS } from "./GraphView";

/** The details of a step or a link: docked beside the map, so the map stays in view and usable
 * (Escape or × closes it, and focus goes back to where it was); a sheet on a phone. */
export function Panel({ id, opened, title, icon, onClose, children }: { id: string | null; opened: boolean; title: string; icon: string; onClose: () => void; children: ReactNode }) {
  const phone = usePhone();
  const ref = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    if (!opened || phone) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    ref.current?.querySelector<HTMLElement>("h2")?.focus({ preventScroll: true });
    const typing = (t: EventTarget | null) => t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement || (t instanceof HTMLElement && t.isContentEditable);
    const key = (e: KeyboardEvent) => e.key === "Escape" && !e.defaultPrevented && !typing(e.target) && close.current();
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      // back to the opener, unless the user already moved on (clicked another step)
      const at = document.activeElement;
      const lost = !at || at === document.body || !!ref.current?.contains(at);
      if (lost && opener?.isConnected) opener.focus({ preventScroll: true });
    };
  }, [opened, phone, id]);
  if (phone)
    return (
      <Drawer opened={opened} onClose={onClose} position="right" size="100%" title={title} returnFocus closeButtonProps={{ "aria-label": "Close" }} classNames={{ title: "sp-sheet-title" }}>
        {children}
      </Drawer>
    );
  if (!opened) return null;
  return (
    <aside className="sp-ginspect" aria-label={title} ref={ref}>
      <header>
        <h2 tabIndex={-1}>
          <Icon path={icon} size={16} stroke={1.8} />
          {title}
        </h2>
        <button type="button" className="sp-gicon" onClick={onClose} aria-label="Close">
          <Icon path={GICONS.close} size={16} stroke={2} />
        </button>
      </header>
      {children}
    </aside>
  );
}

