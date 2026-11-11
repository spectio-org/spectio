import { TextInput } from "@mantine/core";
import type { ReactNode } from "react";
import { ICONS, Icon } from "../icons";

/** The toolbar of ui-spec §12.6 (UI-03): one 36 px row under the page head, the search taking the
 * free width at the left, then the filters, then the caption and the actions at the right. It
 * wraps below 768 px. A named group, not an ARIA toolbar: its controls keep their own Tab stops. */
export function Toolbar({ label, search, filters, caption, actions }: { label: string; search?: ReactNode; filters?: ReactNode; caption?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="sp-toolbar" role="group" aria-label={label}>
      {search && <div className="sp-toolbar-search">{search}</div>}
      {filters}
      {(caption || actions) && (
        <div className="sp-toolbar-end">
          {caption && <span className="sp-toolbar-caption">{caption}</span>}
          {actions}
        </div>
      )}
    </div>
  );
}

/** The toolbar's search box: a labelled `type="search"` input with the search icon. */
export function ToolbarSearch({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <TextInput
      type="search"
      size="sm"
      aria-label={label}
      placeholder={placeholder ?? label}
      value={value}
      onChange={(e) => onChange(e.currentTarget.value)}
      leftSection={<Icon path={ICONS.search} size={16} stroke={1.75} />}
    />
  );
}
