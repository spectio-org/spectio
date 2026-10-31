// The light line icons of the lite boards (24 × 24 paths, round caps), in one place. A board's
// section icon is drawn at 1.6 stroke in a 26–30 px tile; the shell's at 1.8.

export const ICONS = {
  // shell (LiteSidebar, LiteTopbar)
  home: "M4 13h7V4H4z M13 20h7v-9h-7z M13 4h7v5h-7z M4 20h7v-5H4z",
  runs: "M5 4l14 8-14 8z",
  launch: "M12 3v12 M7 8l5-5 5 5 M5 21h14",
  chevronDown: "M6 9l6 6 6-6",
  chevronRight: "M9 6l6 6-6 6",
  arrowRight: "M5 12h14 M13 6l6 6-6 6",
  check: "M5 12l5 5 9-10",
  cross: "M6 6l12 12 M18 6L6 18",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4",
  // sections (LiteHome, LiteRunDetail, LiteRunFailed)
  info: "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 11v5 M12 8h.01",
  layers: "M12 3l9 5-9 5-9-5z M3 13l9 5 9-5",
  terminal: "M4 5h16v14H4z M7 9l3 3-3 3 M12 15h5",
  file: "M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7",
  sliders: "M4 6h10 M18 6h2 M16 4v4 M4 12h4 M12 12h8 M10 10v4 M4 18h12 M18 16v4",
  folder: "M3 7h6l2 2h10v10H3z",
  alert: "M12 4l9 16H3z M12 10v4 M12 17h.01",
  list: "M9 6h11 M9 12h11 M9 18h11 M4.5 6h.01 M4.5 12h.01 M4.5 18h.01",
  power: "M12 3v8 M6.3 7.3a8 8 0 1 0 11.4 0",
  pulse: "M3 12h4l3-7 4 14 3-7h4",
  history: "M3 12a9 9 0 1 0 3-6.7 M3 4v5h5 M12 8v4l3 2",
  route: "M5 6a2 2 0 1 0 0 .01 M19 18a2 2 0 1 0 0 .01 M7 6h6a4 4 0 0 1 0 8h-2a4 4 0 0 0 0 8h6",
  server: "M4 5h16v5H4z M4 14h16v5H4z M8 7.5h.01 M8 16.5h.01",
  copy: "M9 9h11v11H9z M5 15H4V4h11v1",
  download: "M12 4v11 M7 10l5 5 5-5 M5 20h14",
  reload: "M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7",
} as const;

export function Icon({ path, size = 24, stroke = 1.8 }: { path: string; size?: number; stroke?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}
