// The one date formatter of every screen (ui-spec §12.8), and the cell that shows it.
export const two = (n: number) => String(n).padStart(2, "0");
export const isoDay = (d: Date) => `${d.getFullYear()}-${two(d.getMonth() + 1)}-${two(d.getDate())}`;

/** ui-spec §12.8: "just now", "12 min ago", "5 h ago", "3 days ago", then "2026-10-28 07:01"; "—"
 * for no date. */
export function ago(iso: string | null, now = new Date()): string {
  if (!iso) return "—";
  const at = new Date(iso);
  const minutes = Math.floor((now.getTime() - at.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 24 * 60) return `${Math.floor(minutes / 60)} h ago`;
  const days = Math.floor(minutes / (24 * 60));
  if (days < 7) return `${days} ${days === 1 ? "day" : "days"} ago`;
  return `${isoDay(at)} ${two(at.getHours())}:${two(at.getMinutes())}`;
}

/** A date in a cell: `ago`'s words, the exact time in `<time datetime>` and in its accessible
 * name when the words are not it already. */
export function Ago({ iso }: { iso: string | null }) {
  if (!iso) return <>—</>;
  const text = ago(iso);
  // ago() of a date a week back is that exact time already
  const exact = ago(iso, new Date(new Date(iso).getTime() + 7 * 86400000));
  return (
    <time dateTime={iso} aria-label={text === exact ? text : `${text}, ${exact}`}>
      {text}
    </time>
  );
}
