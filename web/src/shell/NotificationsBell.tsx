import { Modal } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { type NotificationKind, type Notifications, listNotifications, markNotificationsRead } from "../api";
import { Icon } from "../icons";
import { useFrames } from "../live";
import { when } from "../runs/stateWord";

// Notifications in 0.0.1 (FU-P3-113; ui-spec top bar note): items the server derives from the runs
// (api §5.9). The count refreshes on each run change of the event stream. The panel is Mantine's
// Modal (aria-modal, focus trapped, Escape closes, focus back to the bell): at the top right on the
// desktop, a full-screen sheet on the phone.

const BELL = "M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8 M10 20a2 2 0 0 0 4 0";
const WHAT: Record<NotificationKind, string> = {
  run_succeeded: "succeeded",
  run_failed: "failed",
  run_cancelled: "was cancelled",
  gate_waiting: "is waiting at a gate",
};

export function NotificationsBell({ phone, className = "sp-key" }: { phone: boolean; className?: string }) {
  const [found, setFound] = useState<Notifications | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [markError, setMarkError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  // Mark all as read goes once nothing is unread: focus moves to the panel's heading (FU-P3-116)
  const heading = useRef<HTMLSpanElement>(null);
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
  const items = found?.items ?? [];
  return (
    <>
      <button
        type="button"
        className={`${className} sp-bell`}
        aria-label={found ? `Notifications, ${unread} unread` : "Notifications"}
        onClick={() => setOpen(true)}
      >
        <span className="sp-key-face">
          <Icon path={BELL} size={19} />
        </span>
        {unread > 0 && (
          <span className="sp-bell-count" aria-hidden="true">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>
      <Modal
        opened={open}
        onClose={() => setOpen(false)}
        title={
          <span ref={heading} tabIndex={-1}>
            Notifications
          </span>
        }
        returnFocus
        fullScreen={phone}
        size="sm"
        classNames={phone ? undefined : { inner: "sp-notif-inner" }}
      >
        {error && (
          <p className="sp-search-error">
            Notifications could not be loaded: {error}{" "}
            <button type="button" className="sp-link-button" onClick={load}>
              Retry
            </button>
          </p>
        )}
        {markError && (
          <p className="sp-search-error">
            Could not mark as read: {markError}{" "}
            <button type="button" className="sp-link-button" onClick={markRead}>
              Retry
            </button>
          </p>
        )}
        {found && items.length === 0 && <p className="sp-notif-empty">No notifications yet</p>}
        {items.length > 0 && (
          <>
            {unread > 0 && (
              <button type="button" className="sp-link-button" onClick={markRead}>
                Mark all as read
              </button>
            )}
            <ul className="sp-notif-list">
              {items.map((item) => (
                <li key={item.id}>
                  <Link
                    to="/runs/$id"
                    params={{ id: item.run_id }}
                    className="sp-notif-item"
                    aria-label={`${item.run_name ?? item.run_id} ${WHAT[item.kind]}, ${when(item.at)}${item.read ? "" : ", unread"}`}
                    onClick={() => setOpen(false)}
                  >
                    <span className="sp-notif-what">
                      {item.run_name ?? item.run_id} {WHAT[item.kind]}
                    </span>
                    <span className="sp-notif-when">
                      <time dateTime={item.at}>{when(item.at)}</time>
                      {!item.read && <span className="sp-notif-new">Unread</span>}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </Modal>
    </>
  );
}
