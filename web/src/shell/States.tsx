import { Button, Skeleton } from "@mantine/core";
import type { ReactNode } from "react";
import { Icon, type IconName } from "../icons";

// The shared states of ui-spec §11 and §12.12 (UI-03), for screens, cards and sheets alike.

/** Nothing to show: a 24 px icon, one sentence that says why, and the next step. */
export function EmptyState({ icon, children, action }: { icon: IconName; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="sp-emptystate">
      <span className="sp-emptystate-icon" aria-hidden="true">
        <Icon name={icon} size="tile" />
      </span>
      <p className="sp-emptystate-text">{children}</p>
      {action}
    </div>
  );
}

/** A read that failed: what failed, the request ID when the server gave one, and Retry. */
export function ErrorPanel({ children, onRetry, requestId }: { children: ReactNode; onRetry: () => void; requestId?: string }) {
  return (
    <div role="alert" className="sp-errorpanel">
      <p className="sp-errorpanel-text">{children}</p>
      {requestId && <p className="sp-errorpanel-id">Request ID: {requestId}</p>}
      <Button variant="default" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

/** Skeleton rows of the final layout (44 px, ui-spec §12.8); screen readers hear `label` once. */
export function SkeletonRows({ rows = 3, label = "Loading…", height = 44 }: { rows?: number; label?: string; height?: number }) {
  return (
    <div role="status" className="sp-skelrows">
      <span className="sp-sr">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height={height} radius="sm" aria-hidden="true" />
      ))}
    </div>
  );
}
