// The app's data grid (ui-spec §4.13, FU-P3-101): AG Grid Community, in its own lazy chunk. Only
// the modules the tables use are registered. The theme takes the app's tokens, so it follows light
// and dark; it leaves out AG Grid's icon set, whose icons are data: images that the CSP's
// `img-src 'self'` refuses, and the two sort arrows are inline SVG instead. Cells are text: no
// column renders HTML from the data.
import {
  ClientSideRowModelModule,
  ModuleRegistry,
  RenderApiModule,
  RowAutoHeightModule,
  RowStyleModule,
  TextFilterModule,
  themeQuartz,
} from "ag-grid-community";
import { AgGridReact, type AgGridReactProps } from "ag-grid-react";

ModuleRegistry.registerModules([ClientSideRowModelModule, TextFilterModule, RowAutoHeightModule, RowStyleModule, RenderApiModule]);

const v = (token: string) => `var(--sp-${token})`;
const theme = themeQuartz.withoutPart("iconSet").withParams({
  fontFamily: "inherit",
  fontSize: 14,
  backgroundColor: v("surface-raised"),
  foregroundColor: v("text-primary"),
  headerBackgroundColor: v("surface-subtle"),
  headerTextColor: v("text-secondary"),
  headerFontWeight: 600,
  borderColor: v("line-divider"),
  accentColor: v("line-focus"),
  inputBorder: { color: v("line-input") },
  inputBackgroundColor: v("surface-page"),
  wrapperBorderRadius: 12,
  // a grid sized to its rows has no empty band under them (150 px by default, for the overlay)
  autoHeightMinBodyHeight: 0,
});

const arrow = (d: string) =>
  `<svg class="sp-grid-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICONS = { sortAscending: arrow("M8 13V3M4 7l4-4 4 4"), sortDescending: arrow("M8 3v10M4 9l4 4 4-4") };

type Props<T> = AgGridReactProps<T> & { label: string };

/** AG Grid with the app's theme and icons, its grid element named `label` (`setGridAriaProperty`);
 * DOM order follows the screen order (`ensureDomOrder`) for screen readers. */
export default function DataGrid<T>({ label, ...props }: Props<T>) {
  return (
    <div className="sp-grid">
      <AgGridReact<T>
        theme={theme}
        icons={ICONS}
        suppressColumnVirtualisation
        ensureDomOrder
        suppressMovableColumns
        onGridReady={(e) => e.api.setGridAriaProperty("label", label)}
        {...props}
      />
    </div>
  );
}
