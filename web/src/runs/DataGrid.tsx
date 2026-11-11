// The app's data grid (ui-spec §4.13, FU-P3-101): AG Grid Community, in its own lazy chunk
// (`LazyGrid.tsx` loads it). Only the modules the tables use are registered. The theme takes the
// app's tokens, so it follows light and dark; it leaves out AG Grid's icon set, whose icons are
// data: images that the CSP's `img-src 'self'` refuses, so every icon the grids show is inline
// SVG given through `icons` (an icon left out draws as a solid square, FU-P3-116). Cells are
// text: no column renders HTML from the data.
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
import { ICONS as LINE_ICONS } from "../icons";

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

const svg = (d: string, box = 16, width = 1.5) =>
  `<svg class="sp-grid-icon" viewBox="0 0 ${box} ${box}" width="14" height="14" aria-hidden="true"><path d="${d}" fill="none" stroke="currentColor" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const filter = svg(LINE_ICONS.filter, 24, 2);
/** Every icon the tables show: the sort arrows, the unsorted pair (`unSortIcon`), the filtered
 * column's funnel and the filter box's clear cross. The absolute sorts (`aasc`, `adesc`, hidden in
 * every sortable header) and the header menu are never shown. */
const ICONS = {
  sortAscending: svg("M8 13V3M4 7l4-4 4 4"),
  sortDescending: svg("M8 3v10M4 9l4 4 4-4"),
  sortUnSort: svg("M5 6l3-3 3 3M5 10l3 3 3-3"),
  filter,
  filterActive: filter,
  cancel: svg(LINE_ICONS.cross, 24, 2),
};

/** What a table passes; the theme, icons and `onGridReady` are the grid's own (SEC-P3FU101A-01). */
export type GridProps<T> = Omit<AgGridReactProps<T>, "theme" | "icons" | "onGridReady"> & { label: string };

/** AG Grid with the app's theme and icons, its grid element named `label` (`setGridAriaProperty`);
 * DOM order follows the screen order (`ensureDomOrder`) for screen readers. */
export default function DataGrid<T>({ label, ...props }: GridProps<T>) {
  return (
    <div className="sp-grid">
      <AgGridReact<T>
        suppressColumnVirtualisation
        ensureDomOrder
        suppressMovableColumns
        {...props}
        theme={theme}
        icons={ICONS}
        onGridReady={(e) => e.api.setGridAriaProperty("label", label)}
      />
    </div>
  );
}
