import { createContext, useContext, useEffect } from "react";

/** The page's crumbs from the API: `item` a run's name, `file` a file page's name from `stat`. */
export interface PageCrumb {
  item: string | null;
  file: string | null;
}
export const NO_CRUMB: PageCrumb = { item: null, file: null };

/** Sets the page's crumbs; NO_CRUMB: the defaults. */
export const CrumbContext = createContext<(crumb: PageCrumb) => void>(() => {});

/** The page's own crumbs while it is shown. A URL's text is never a label (SEC-P3G4-02). */
export function usePageCrumb(item: string | null, file: string | null = null) {
  const set = useContext(CrumbContext);
  useEffect(() => {
    set({ item, file });
    return () => set(NO_CRUMB);
  }, [item, file, set]);
}
