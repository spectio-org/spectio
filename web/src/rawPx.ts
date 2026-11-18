// The raw-px lint of the CSS sweep (UI-19a to UI-19c, ui-spec §12.15), shared by
// shell/theme.test.ts and runs/tokens.test.ts so the two cannot drift (CR-P3UI19B-03).

/** A spacing, radius or font-size declaration, from its property to the end of its value. */
const DECLARATION = /(?:^|[;{\s])((?:font-size|font|gap|row-gap|column-gap|padding[a-z-]*|margin[a-z-]*|border-radius)\s*:[^;}]*)/g;
/** A raw px value other than a 1 px line. */
const RAW_PX = /(?<![\w.-])-?(?!1px)\d+(?:\.\d+)?px/;

/** The declarations of `css` that still write a raw px value once the first occurrence of each
 * allowed fragment is removed from them. */
export function rawPx(css: string, allowed: readonly string[] = []): string[] {
  return [...css.matchAll(DECLARATION)]
    .map((m) => m[1].trim())
    .filter((d) => RAW_PX.test(allowed.reduce((s, a) => s.replace(a, ""), d)));
}
