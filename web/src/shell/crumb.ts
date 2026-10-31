import { createContext, useContext, useEffect } from "react";

/** Sets the last breadcrumb of the page (a run's name from the API); null: the default. */
export const CrumbContext = createContext<(label: string | null) => void>(() => {});

/** The page's own last crumb while it is shown. A URL's text is never a label (SEC-P3G4-02). */
export function usePageCrumb(label: string | null) {
  const set = useContext(CrumbContext);
  useEffect(() => {
    set(label);
    return () => set(null);
  }, [label, set]);
}
