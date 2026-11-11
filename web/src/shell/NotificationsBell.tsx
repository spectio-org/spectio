import { ActionIcon, Button, Drawer, Popover, SegmentedControl, Tooltip } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { type KeyboardEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import {
  type Notification,
  type NotificationKind,
  type Notifications,
  type RunState,
  listNotifications,
  markNotificationsRead,
} from "../api";
import { Icon } from "../icons";
import { useFrames } from "../live";
import { TONE_ICONS } from "../runs/RunState";
import { engineName, runWord, tone } from "../runs/stateWord";
import { EngineMark } from "./EngineMark";
import { EmptyState, ErrorPanel, SkeletonRows } from "./States";

// The notifications panel (ui-spec §12.13): items the server derives from the runs (api §5.9),
// refreshed on each run change of the event stream. A non-modal popover under the bell on the
// desktop and tablet, a modal bottom sheet on the phone; focus goes back to the bell on close.

// The run state each kind shows; its word, tone and icon are those of ui-spec §3.1.
const STATE: Record<NotificationKind, RunState> = {
  run_failed: "failed",
  run_succeeded: "succeeded",
  run_cancelled: "cancelled",
  gate_waiting: "awaiting_review",
};

const two = (n: number) => String(n).padStart(2, "0");
const isoDay = (d: Date) => `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`;

/** ui-spec §12.8: "just now", "12 min ago", "5 h ago", "3 days ago", then "2026-10-28 07:01". */
function ago(iso: string, now = new Date()): string {
  const at = new Date(iso);
  const minutes = Math.floor((now.getTime() - at.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)} h ago`;
  const days = Math.floor(minutes / (24 * 60));
  if (days < 7) return `${days} ${days === 1 ? "day" : "days"} ago`;
  return `${isoDay(at)} ${two(at.getHours())}:${two(at.getMinutes())}`;
}

/** The item's local day: Today, Yesterday, else its ISO date. */
function dayLabel(iso: string, now: Date): string {
  const at = new Date(iso);
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (isoDay(at) === isoDay(now)) return "Today";
  if (isoDay(at) === isoDay(yesterday)) return "Yesterday";
  return isoDay(at);
}

export function NotificationsBell({ phone, className = "sp-key" }: { phone: boolean; className?: string }) {
  const [found, setFound] = useState<Notifications | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [markError, setMarkError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("All");
  const [active, setActive] = useState(0);
  const bell = useRef<HTMLButtonElement>(null);
  // Mark all as read goes once nothing is unread: focus moves to the panel's heading (FU-P3-116)
  const heading = useRef<HTMLHeadingElement & HTMLSpanElement>(null);
  const rows = useRef<(HTMLAnchorElement | null)[]>([]);
  const titleId = useId();

  const load = useCallback(() => {
    listNotifications().then(
      (answer) => {
        setFound(answer);
        setError(null);
      },
      (e: Error) => setError(e.message),
    );
  }, []);
  useEffect(load, [load]);
  useFrames(load);

  // The popover's head mounts on each open: focus moves to its first control, the All / Unread segment
  const focusFirst = useCallback((el: HTMLDivElement | null) => {
    if (el) setTimeout(() => el.querySelector<HTMLInputElement>("input:checked")?.focus());
  }, []);

  const close = () => {
    setOpen(false);
    setTimeout(() => bell.current?.focus(), 20);
  };

  const markRead = () => {
    const newest = found?.items[0];
    if (!newest) return;
    markNotificationsRead(newest.at).then(
      (answer) => {
        setFound(answer);
        setMarkError(null);
        setTimeout(() => heading.current?.focus());
      },
      (e: Error) => setMarkError(e.message),
    );
  };

  const unread = found?.unread ?? 0;
  const now = new Date();
  const shown = (found?.items ?? []).filter((i) => filter === "All" || !i.read);
  const groups: { label: string; items: Notification[] }[] = [];
  for (const item of shown) {
    const label = dayLabel(item.at, now);
    if (groups.at(-1)?.label !== label) groups.push({ label, items: [] });
    groups.at(-1)!.items.push(item);
  }
  const current = Math.min(active, shown.length - 1);

  const rove = (event: KeyboardEvent) => {
    const last = shown.length - 1;
    const next = { ArrowDown: Math.min(current + 1, last), ArrowUp: Math.max(current - 1, 0), Home: 0, End: last }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    setActive(next);
    rows.current[next]?.focus();
  };

  const markAll =
    unread === 0 ? null : phone ? (
      <Button variant="subtle" h={44} leftSection={<Icon name="checkCheck" />} onClick={markRead}>
        Mark all as read
      </Button>
    ) : (
      <Tooltip label="Mark all as read" events={{ hover: true, focus: true, touch: false }}>
        <ActionIcon variant="subtle" color="gray" size="md" aria-label="Mark all as read" onClick={markRead}>
          <Icon name="checkCheck" />
        </ActionIcon>
      </Tooltip>
    );

  let index = -1;
  const body = (
    <>
      <div className="sp-notif-head" ref={phone ? undefined : focusFirst}>
        {!phone && (
          <h2 id={titleId} ref={heading} tabIndex={-1} className="sp-notif-title">
            Notifications
          </h2>
        )}
        <SegmentedControl
          size="xs"
          data={["All", "Unread"]}
          value={filter}
          onChange={(value) => {
            setFilter(value);
            setActive(0);
          }}
          aria-label="Show"
        />
        {markAll}
      </div>
      {error && <ErrorPanel onRetry={load}>Notifications could not be loaded: {error}</ErrorPanel>}
      {markError && (
        <div className="sp-notif-error" role="alert">
          <span>Could not mark as read: {markError}</span>
          <Button size="xs" variant="default" onClick={markRead}>
            Retry
          </Button>
        </div>
      )}
      <div className="sp-notif-body" onKeyDown={rove}>
        {!found && !error && <SkeletonRows rows={3} height={56} />}
        {found &&
          shown.length === 0 &&
          (filter === "All" ? (
            <EmptyState icon="bell">No notifications yet</EmptyState>
          ) : (
            <EmptyState
              icon="bell"
              action={
                <Button size="xs" variant="default" onClick={() => setFilter("All")}>
                  Show all
                </Button>
              }
            >
              No unread notifications
            </EmptyState>
          ))}
        {groups.map((group, g) => (
          <section key={group.label}>
            <h3 id={`${titleId}-${g}`} className="sp-notif-day">
              {group.label}
            </h3>
            <ul className="sp-notif-list" aria-labelledby={`${titleId}-${g}`}>
              {group.items.map((item) => {
                const i = ++index;
                const state = STATE[item.kind];
                const word = runWord(state);
                const t = tone(state);
                const name = item.run_name ?? item.run_id;
                const time = ago(item.at, now);
                const label = [name, word, item.engine && engineName(item.engine), time, !item.read && "unread"].filter(Boolean).join(", ");
                return (
                  <li key={item.id}>
                    <Link
                      ref={(el: HTMLAnchorElement | null) => {
                        rows.current[i] = el;
                      }}
                      to="/runs/$id"
                      params={{ id: item.run_id }}
                      className="sp-notif-row"
                      data-unread={item.read ? undefined : ""}
                      tabIndex={i === current ? 0 : -1}
                      aria-label={label}
                      onFocus={() => setActive(i)}
                      onClick={close}
                    >
                      <span className="sp-notif-tile" data-tone={t}>
                        <Icon name={TONE_ICONS[t]} />
                      </span>
                      <span className="sp-notif-text">
                        <span className="sp-notif-line">
                          <span className="sp-notif-name">{name}</span>
                          <span className="sp-notif-state" data-tone={t}>
                            {word}
                          </span>
                        </span>
                        <span className="sp-notif-line sp-notif-meta">
                          <EngineMark engine={item.engine} size={16} named />
                          <time dateTime={item.at}>{time}</time>
                        </span>
                      </span>
                      {!item.read && <span className="sp-notif-dot" />}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </div>
      <div className="sp-notif-foot">
        <Link to="/runs" className="sp-notif-all" onClick={close}>
          View all runs →
        </Link>
      </div>
    </>
  );

  const bellButton = (
    <button
      ref={bell}
      type="button"
      className={`${className} sp-bell`}
      aria-label={found ? `Notifications, ${unread} unread` : "Notifications"}
      onClick={() => (open ? close() : setOpen(true))}
    >
      <span className="sp-key-face">
        <Icon name="bell" size="nav" />
      </span>
      {unread > 0 && (
        <span className="sp-bell-count" aria-hidden="true">
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </button>
  );

  if (phone) {
    return (
      <>
        {bellButton}
        <Drawer
          opened={open}
          onClose={close}
          position="bottom"
          radius="md"
          title={
            <span ref={heading} tabIndex={-1}>
              Notifications
            </span>
          }
          classNames={{ content: "sp-notif-sheet", body: "sp-notif-panel", title: "sp-notif-title" }}
        >
          {body}
        </Drawer>
      </>
    );
  }
  return (
    <Popover
      opened={open}
      onChange={(next) => !next && close()}
      position="bottom-end"
      offset={8}
      width={380}
      radius="md"
      shadow="md"
    >
      <Popover.Target>{bellButton}</Popover.Target>
      <Popover.Dropdown className="sp-notif-panel sp-notif-popover" aria-labelledby={titleId}>
        {body}
      </Popover.Dropdown>
    </Popover>
  );
}
