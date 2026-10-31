// Spectio's palette "Dawn (light)" and its dark twin, as Mantine colours and `--sp-*` CSS variables.
// The values are those of design/tokens/spectio-tokens.css (v0.2, 2026-10-25), which the G1 boards
// in design/ui-canvas draw with. The shell's CSS reads the role tokens (surfaces, lines, text,
// accent, sections), never a raw hex, so the dark scheme is one set of variables.
import {
  type CSSVariablesResolver,
  type MantineColorsTuple,
  createTheme,
  localStorageColorSchemeManager,
} from "@mantine/core";

const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const;

/** The brand and support scales, 50 → 900 (emblem order: indigo, violet, coral, amber). */
export const SCALES = {
  indigo: ["#F2F1FB", "#E5E3F7", "#C7C3EF", "#A39CE4", "#7E76DA", "#5A4FCF", "#4E45B3", "#423B97", "#343078", "#272458"],
  violet: ["#F6F2FE", "#ECE5FE", "#D8C8FC", "#BEA4FA", "#A580F8", "#8B5CF6", "#7750D4", "#6344B2", "#4D368B", "#372864"],
  coral: ["#FDF2F5", "#FCE5EC", "#F9C9D6", "#F4A5BC", "#F082A1", "#EC5F87", "#C95277", "#A54666", "#7E3854", "#562941"],
  amber: ["#FFF8F0", "#FEF1E2", "#FDE2C0", "#FCCF98", "#FABC6F", "#F9A947", "#D49141", "#AE783B", "#845C34", "#5A412C"],
  sky: ["#EEF6FA", "#DCEDF6", "#B9DBEC", "#8FC3DF", "#5FA8CF", "#3B8FBF", "#2F7FA8", "#276A8C", "#1F536D", "#173D50"],
  /** Neutrals tinted with indigo; ink-0 (#F7F7FB) sits before ink-50. */
  ink: ["#EEEFF5", "#DFE1EA", "#C4C7D4", "#9A9EB0", "#6E7287", "#4D5065", "#33364A", "#22253A", "#171A2E", "#0F1020"],
} satisfies Record<string, MantineColorsTuple>;

const scaleVars = Object.fromEntries([
  ["--sp-ink-0", "#F7F7FB"],
  ...Object.entries(SCALES).flatMap(([name, shades]) =>
    shades.map((hex, i) => [`--sp-${name}-${STEPS[i]}`, hex]),
  ),
]);

const v = (token: string) => `var(--sp-${token})`;

/** Run-state colours, rail · fg (text) · bg (tint), light then dark (spectio-tokens.css "Run
 * states"); the screens read them through a tone, never a raw hex (UX-PAR-05). */
const states = (rows: Record<string, [string, string, string]>) =>
  Object.fromEntries(
    Object.entries(rows).flatMap(([s, [rail, fg, bg]]) => [
      [`state-${s}`, rail],
      [`state-${s}-fg`, fg],
      [`state-${s}-bg`, bg],
    ]),
  );
const STATES_LIGHT = states({
  queued: ["#6E7287", "#33364A", "#F1F2F6"],
  running: ["#3B82F6", "#1D5FC9", "#EAF2FE"],
  review: ["#D9890B", "#8F5806", "#FDF3E2"],
  paused: ["#8B5CF6", "#6344B2", "#F1ECFE"],
  succeeded: ["#1F9D63", "#157A4B", "#E8F6EF"],
  failed: ["#DC3B3B", "#B02A2A", "#FCEBEB"],
  cancelled: ["#4D5065", "#33364A", "#EEEFF5"],
  cached: ["#8A8F98", "#4F5462", "#F1F2F4"],
});
const STATES_DARK = states({
  queued: ["#9A9EB0", "#C4C7D4", "#22253A"],
  running: ["#5B9BF8", "#9CC2FB", "#1A2747"],
  review: ["#E9A23B", "#F5C779", "#33270F"],
  paused: ["#A580F8", "#C8B2FB", "#261E45"],
  succeeded: ["#34B27A", "#7FD3AA", "#14302A"],
  failed: ["#EE5A5A", "#F59A9A", "#3A1A1F"],
  cancelled: ["#6E7287", "#9A9EB0", "#1C1F33"],
  cached: ["#8E92A8", "#B5B8C6", "#22253A"],
});

// Role tokens, light then dark (spectio-tokens.css, ":root" and ":root[data-theme=dark]").
const LIGHT = {
  "surface-page": "#FFFFFF",
  "surface-subtle": v("ink-0"),
  "surface-sunken": v("ink-50"),
  "surface-raised": "#FFFFFF",
  "surface-bar": "rgba(255,255,255,0.94)",
  "surface-code": v("ink-900"),
  // The code surface is dark in both schemes, so its text and level tints are fixed: the dark
  // scheme's failed and review fg. Engine marks sit on white in both (ui-spec §4.3).
  "code-text": v("ink-50"),
  "code-failed": "#F59A9A",
  "code-review": "#F5C779",
  "code-ok": "#7FD3AA",
  "code-progress": "#9CC2FB",
  "surface-mark": "#FFFFFF",
  "line-hairline": "rgba(15,16,32,.11)",
  "line-divider": v("ink-50"),
  "line-border": v("ink-100"),
  "line-input": v("ink-200"),
  "line-focus": v("violet-600"),
  "text-primary": v("ink-900"),
  "text-secondary": v("ink-600"),
  "text-muted": v("ink-500"),
  "text-faint": v("ink-400"),
  "text-link": v("violet-700"),
  accent: v("violet-600"),
  "accent-subtle": v("violet-50"),
  "ok-fg": "#157A4B",
  "ok-bg": "#E8F6EF",
  "ok-rail": "#1F9D63",
  "down-fg": "#B02A2A",
  "down-bg": "#FCEBEB",
  "section-home": v("indigo-500"),
  "section-home-bg": v("indigo-50"),
  "section-runs": v("violet-600"),
  "section-runs-bg": v("violet-50"),
  "section-launch": v("coral-500"),
  "section-launch-bg": v("coral-50"),
  shadow:
    "0 0 0 1px rgba(15,16,32,0.11), 0 1px 2px rgba(15,16,32,0.05), 0 10px 28px -18px rgba(15,16,32,0.18)",
};

const DARK: typeof LIGHT = {
  "surface-page": v("ink-900"),
  "surface-subtle": v("ink-800"),
  "surface-sunken": "#0B0C18",
  "surface-raised": "#1D2036",
  "surface-bar": "rgba(29,32,54,0.94)",
  "surface-code": "#0B0C18",
  "code-text": v("ink-50"),
  "code-failed": "#F59A9A",
  "code-review": "#F5C779",
  "code-ok": "#7FD3AA",
  "code-progress": "#9CC2FB",
  "surface-mark": "#FFFFFF",
  "line-hairline": "rgba(236,237,245,.12)",
  "line-divider": v("ink-700"),
  "line-border": v("ink-600"),
  "line-input": v("ink-500"),
  "line-focus": v("violet-400"),
  "text-primary": "#ECEDF5",
  "text-secondary": v("ink-200"),
  "text-muted": v("ink-300"),
  "text-faint": "#8E92A8",
  "text-link": v("violet-300"),
  accent: v("violet-400"),
  "accent-subtle": "#261E45",
  "ok-fg": "#7FD3AA",
  "ok-bg": "#14302A",
  "ok-rail": "#34B27A",
  "down-fg": "#F59A9A",
  "down-bg": "#3A1A1F",
  "section-home": v("indigo-400"),
  "section-home-bg": "rgba(126,118,218,.16)",
  "section-runs": v("violet-400"),
  "section-runs-bg": "rgba(165,128,248,.16)",
  "section-launch": v("coral-400"),
  "section-launch-bg": "rgba(240,130,161,.14)",
  shadow: "0 0 0 1px rgba(236,237,245,.12), 0 10px 28px -18px rgba(0,0,0,.6)",
};

const roles = (tokens: typeof LIGHT, stateTokens: Record<string, string>) => ({
  ...Object.fromEntries(Object.entries({ ...tokens, ...stateTokens }).map(([k, value]) => [`--sp-${k}`, value])),
  // Mantine's own surfaces follow the same roles, so its inputs and buttons match the shell.
  "--mantine-color-body": v("surface-page"),
  "--mantine-color-text": v("text-primary"),
  "--mantine-color-dimmed": v("text-muted"),
  "--mantine-color-default-border": v("line-border"),
  "--mantine-color-anchor": v("text-link"),
});

export const cssVariablesResolver: CSSVariablesResolver = () => ({
  variables: {
    ...scaleVars,
    "--sp-font-display": "'Outfit', system-ui, sans-serif",
    "--sp-font-body": "'Inter', system-ui, sans-serif",
    "--sp-font-mono": "'JetBrains Mono', ui-monospace, monospace",
  },
  light: roles(LIGHT, STATES_LIGHT),
  dark: roles(DARK, STATES_DARK),
});

export const theme = createTheme({
  colors: {
    ...SCALES,
    // Mantine's dark scheme reads `dark`: 0 is text, 4 borders, 6 inputs, 7 the page.
    dark: ["#ECEDF5", "#C4C7D4", "#9A9EB0", "#8E92A8", "#33364A", "#2A2D45", "#1D2036", "#0F1020", "#0B0C18", "#07080F"],
  },
  primaryColor: "violet",
  primaryShade: { light: 6, dark: 4 },
  fontFamily: "var(--sp-font-body)",
  fontFamilyMonospace: "var(--sp-font-mono)",
  headings: { fontFamily: "var(--sp-font-display)", fontWeight: "600" },
  defaultRadius: "md",
});

/** The scheme is kept in localStorage; Mantine's manager wraps each read and write in try/catch. */
export const THEME_KEY = "spectio-color-scheme";

/** What `MantineProvider` takes, for the app and its tests. Until the reader picks a scheme, it
 * follows the system's (`auto`). */
export const providerProps = {
  theme,
  cssVariablesResolver,
  colorSchemeManager: localStorageColorSchemeManager({ key: THEME_KEY }),
  defaultColorScheme: "auto",
} as const;
