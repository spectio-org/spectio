import { Button } from "@mantine/core";
import { useEffect, useState } from "react";

// What the run header's More actions menu can copy (LiteRunActions B; ui-spec §4.4 run tools,
// §12.4 Copy): each item copies its text, and a polite status says what was copied, for 4 s.

export interface CopyItem {
  label: string;
  /** "the run ID": the status reads "Copied the run ID". */
  what: string;
  text: string;
}

/** Copies `text` to the clipboard; rejects when there is none. */
export const copyText = (text: string): Promise<void> =>
  navigator.clipboard?.writeText(text) ?? Promise.reject(new Error("no clipboard"));

/** The status line of the Copy items and the copy that sets it: "Copied the run ID", or why not. */
export function useCopyStatus(): [string | null, (item: CopyItem) => void] {
  const [said, setSaid] = useState<string | null>(null);
  useEffect(() => {
    if (!said) return;
    const timer = setTimeout(() => setSaid(null), 4000);
    return () => clearTimeout(timer);
  }, [said]);
  const copy = (item: CopyItem) =>
    copyText(item.text)
      .then(() => setSaid(`Copied ${item.what}`))
      .catch(() => setSaid(`Could not copy ${item.what}: the browser gave no clipboard`));
  return [said, copy];
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
