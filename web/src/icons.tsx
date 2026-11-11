// The light line icons of the lite boards (24 × 24 paths, round caps), in one place, drawn only
// through `Icon` (or `iconSvg`) at four sizes and one stroke (ui-audit D, UI-02); the lint test in
// icons.test.tsx rejects a path or a stroke anywhere else.

export const ICONS = {
  // shell (LiteSidebar, LiteTopbar)
  home: "M4 13h7V4H4z M13 20h7v-9h-7z M13 4h7v5h-7z M4 20h7v-5H4z",
  runs: "M5 4l14 8-14 8z",
  launch: "M12 3v12 M7 8l5-5 5 5 M5 21h14",
  chevronDown: "M6 9l6 6 6-6",
  chevronRight: "M9 6l6 6-6 6",
  chevronLeft: "M15 6l-6 6 6 6",
  arrowRight: "M5 12h14 M13 6l6 6-6 6",
  check: "M5 12l5 5 9-10",
  checkCheck: "M18 6L7 17l-5-5 M22 10l-7.5 7.5L13 16",
  cross: "M6 6l12 12 M18 6L6 18",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z M20 20l-4-4",
  bell: "M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8 M10 20a2 2 0 0 0 4 0",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z M12 1v2 M12 21v2 M4.2 4.2l1.4 1.4 M18.4 18.4l1.4 1.4 M1 12h2 M21 12h2 M4.2 19.8l1.4-1.4 M18.4 5.6l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z",
  person: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M4 21a8 8 0 0 1 16 0",
  fold: "M4 5h16v14H4z M9 5v14 M16 10l-2 2 2 2",
  unfold: "M4 5h16v14H4z M9 5v14 M14 10l2 2-2 2",
  // run states (ui-spec §3.1): clock, play, flag, pause, slash; done and failed reuse check and cross
  clock: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M12 7v5l3 2",
  play: "M7 5l12 7-12 7z",
  flag: "M5 21V4 M5 4h11l-2 4 2 4H5",
  pause: "M8 5v14 M16 5v14",
  slash: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z M6 18L18 6",
  // table headers (AG Grid): sort arrows and the unsorted pair
  sortUp: "M12 19.5v-15 M6 10.5l6-6 6 6",
  sortDown: "M12 4.5v15 M6 13.5l6 6 6-6",
  sortBoth: "M7.5 9l4.5-4.5 4.5 4.5 M7.5 15l4.5 4.5 4.5-4.5",
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
  dna: "M7 3c0 6 10 6 10 12s-10 6-10 6 M17 3c0 6-10 6-10 12s10 6 10 6 M9 7h6 M9 17h6",
  scissors: "M6 9a3 3 0 1 0 0-.01 M6 18a3 3 0 1 0 0-.01 M8.5 7.5L20 18 M8.5 16.5L20 6",
  skip: "M5 5l8 7-8 7z M13 5l6 7-6 7",
  chart: "M4 20h16 M7 16v-5 M12 16V7 M17 16v-8",
  reload: "M20 11a8 8 0 1 0-2.3 5.7 M20 4v7h-7",
  // Launch (LiteLaunch): the preview card and the schema groups the board draws
  fileCode: "M6 3h9l4 4v14H6z M14 3v5h5 M10 12l-2 2 2 2 M14 12l2 2-2 2",
  signpost: "M12 3v18 M5 6h11l3 3-3 3H5z",
  filter: "M4 5h16l-6 7v6l-4 2v-8z",
  tag: "M3 12V4h8l10 10-8 8z M7.5 7.5h.01",
  shield: "M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6z M9 12l2 2 4-4",
  building: "M4 21V7l8-4 8 4v14 M9 21v-5h6v5 M8 10h.01 M12 10h.01 M16 10h.01",
  externalLink: "M14 4h6v6 M20 4l-9 9 M18 14v6H4V6h6",
  table: "M4 5h16v14H4z M4 10h16 M4 15h16 M10 5v14",
  braces: "M9 4c-2 0-2 2-2 4s-1 4-3 4c2 0 3 2 3 4s0 4 2 4 M15 4c2 0 2 2 2 4s1 4 3 4c-2 0-3 2-3 4s0 4-2 4",
  image: "M4 5h16v14H4z M4 16l5-5 4 4 3-3 4 4 M15.5 9h.01",
  pin: "M12 17v5 M9 4h6 M10 4v6l-3 4v3h10v-3l-3-4V4",
  more: "M5 12h1 M11.5 12h1 M18 12h1",
  trash: "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13 M10 11v5 M14 11v5",
} as const;

export type IconName = keyof typeof ICONS;

/** The four icon sizes (ui-audit D): inline with text and in buttons and menus 16, top bar, sidebar
 * and tab bar 20, a page head's tile 24. */
export const ICON_PX = { inline: 16, button: 16, nav: 20, tile: 24 } as const;
export type IconSize = keyof typeof ICON_PX;
const STROKE = 1.75;

/** A line icon. Decorative (`aria-hidden`) unless `label` names it, which makes it an image. */
export function Icon({ name, size = "inline", label }: { name: IconName; size?: IconSize; label?: string }) {
  const px = ICON_PX[size];
  const a11y = label ? { role: "img", "aria-label": label } : { "aria-hidden": true };
  return (
    <svg
      className="sp-icon"
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={STROKE}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...a11y}
    >
      <path d={ICONS[name]} />
    </svg>
  );
}

/** The same icon as markup, for a host that takes HTML strings only (AG Grid's `icons`). */
export function iconSvg(name: IconName, size: IconSize = "inline", className = "sp-icon"): string {
  const px = ICON_PX[size];
  return `<svg class="${className}" width="${px}" height="${px}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${STROKE}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${ICONS[name]}"/></svg>`;
}

// nf-core groups name a Font Awesome icon (`fa_icon`); Spectio draws a few of them as its own line
// icons and every other one as the neutral sliders (UX-PAR-30). No icon font is loaded.
const GROUP_ICONS: Record<string, IconName> = {
  folder: "folder",
  "folder-open": "folder",
  "file-import": "file",
  dna: "dna",
  cut: "scissors",
  scissors: "scissors",
  "fast-forward": "skip",
  cog: "sliders",
  cogs: "sliders",
  wrench: "sliders",
  microchip: "server",
  server: "server",
  database: "server",
  terminal: "terminal",
  "chart-bar": "chart",
  filter: "filter",
  tag: "tag",
  tags: "tag",
  shield: "shield",
  "shield-alt": "shield",
  "user-shield": "shield",
  university: "building",
  building: "building",
  institution: "building",
  "map-signs": "signpost",
  "align-center": "signpost",
  download: "download",
  "file-download": "download",
  question: "info",
  "question-circle": "info",
  info: "info",
  "info-circle": "info",
  "exclamation-triangle": "alert",
  bug: "alert",
};

/** The line icon of a schema group's `fa_icon` ("fas fa-folder-open"), or the neutral one. */
export function groupIcon(faIcon: string | null): IconName {
  const name = faIcon?.match(/fa-([a-z-]+)\s*$/)?.[1];
  return (name && Object.hasOwn(GROUP_ICONS, name) && GROUP_ICONS[name]) || "sliders"; // SEC-P3PARB-02
}
