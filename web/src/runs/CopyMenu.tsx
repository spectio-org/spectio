import { Button } from "@mantine/core";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ICONS, Icon } from "../icons";

// The run header's Copy menu (LiteRunActions B; ui-spec §4.4 run tools): native buttons in a
// role="menu", arrow keys move, Escape closes and returns focus to Copy, and a polite status says
// what was copied, for 4 s. The board's "Command" item waits for the API to serve the engine's
// command line (P1 Task 32).

export interface CopyItem {
  label: string;
  /** "the run ID": the status reads "Copied the run ID". */
  what: string;
  text: string;
}

/** Copies `text` to the clipboard; rejects when there is none. */
export const copyText = (text: string): Promise<void> =>
  navigator.clipboard?.writeText(text) ?? Promise.reject(new Error("no clipboard"));

export function CopyMenu({ items, fullWidth = false }: { items: CopyItem[]; fullWidth?: boolean }) {
  const [open, setOpen] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  const entries = () => [...(menu.current?.querySelectorAll<HTMLButtonElement>("[role=menuitem]") ?? [])];
  useEffect(() => {
    if (open) entries()[0]?.focus();
  }, [open]);
  useEffect(() => {
    if (!said) return;
    const timer = setTimeout(() => setSaid(null), 4000);
    return () => clearTimeout(timer);
  }, [said]);

  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  const pick = (item: CopyItem) => {
    close();
    copyText(item.text)
      .then(() => setSaid(`Copied ${item.what}`))
      .catch(() => setSaid(`Could not copy ${item.what}: the browser gave no clipboard`));
  };
  const onKey = (event: KeyboardEvent) => {
    const all = entries();
    const at = all.indexOf(document.activeElement as HTMLButtonElement);
    const move = { ArrowDown: at + 1, ArrowUp: at - 1, Home: 0, End: all.length - 1 }[event.key];
    if (move !== undefined) {
      event.preventDefault();
      all[(move + all.length) % all.length]?.focus();
    } else if (event.key === "Escape") {
      event.preventDefault();
      close();
    } else if (event.key === "Tab") {
      setOpen(false);
    }
  };

  return (
    <span className="sp-copy" data-full={fullWidth || undefined}>
      <Button
        ref={button}
        variant="default"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? "copy-menu" : undefined}
        id="copy-button"
        rightSection={<Icon path={ICONS.chevronDown} size={14} stroke={2} />}
        onClick={() => setOpen(!open)}
        fullWidth={fullWidth}
      >
        Copy
      </Button>
      {open && (
        <div
          id="copy-menu"
          ref={menu}
          role="menu"
          aria-labelledby="copy-button"
          className="sp-menu"
          onKeyDown={onKey}
          onBlur={(e) => menu.current?.contains(e.relatedTarget as Node) || e.relatedTarget === button.current || setOpen(false)}
        >
          {items.map((item) => (
            <button key={item.label} type="button" role="menuitem" tabIndex={-1} onClick={() => pick(item)}>
              {item.label}
            </button>
          ))}
        </div>
      )}
      <span role="status" className="sp-copy-status">
        {said}
      </span>
    </span>
  );
}

/** One Copy button for `text`; a status line beside it says it was copied, or why not. */
export function CopyButton({ text, label, name }: { text: string; label: string; name: string }) {
  const [said, setSaid] = useState<string | null>(null);
  const copy = () =>
    copyText(text)
      .then(() => setSaid("Copied"))
      .catch(() => setSaid("Could not copy: select the text instead"));
  return (
    <span className="sp-actions">
      <Button variant="light" size="xs" aria-label={name} onClick={copy}>
        {label}
      </Button>
      <span role="status" className="sp-muted">
        {said}
      </span>
    </span>
  );
}
