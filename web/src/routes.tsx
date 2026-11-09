import {
  type RouterHistory,
  createRootRoute,
  createRoute,
  createRouter,
  useNavigate,
  useParams,
  useRouterState,
  useSearch,
} from "@tanstack/react-router";
import { HomePage } from "./home/HomePage";
import { LaunchPage } from "./launch/LaunchPage";
import { useRecentRuns } from "./launch/TryPipelines";
import { FilePreview } from "./runs/FilePreview";
import { ReportViewer, reportSearch } from "./runs/ReportViewer";
import { ResultsBrowser, resultsSearch } from "./runs/ResultsBrowser";
import { NotFound, RUN_ID, RunDetailPage, runSearch } from "./runs/RunDetailPage";
import { RunsPage, runsSearch } from "./runs/RunsPage";
import { AppShell } from "./shell/AppShell";

// The four routes of 0.0.1 (mvp-0.0.1 §1) in the Paper shell (G4): home, the runs list and the
// run detail (P1 Task 20), and the launch form (Task 19); and the report viewer (Task 31) and the
// results browser (Task 32), and the preview of one results file (FU-P3-85c).

/** `/launch?location=<pipeline>`: Launch opens on that pipeline (Home's pipeline links);
 * `/launch?from=<run ID>`: Copy to a new launch, prefilled from that run. */
export function launchSearch(search: Record<string, unknown>): { location?: string; from?: string } {
  if (typeof search.from === "string" && RUN_ID.test(search.from)) return { from: search.from };
  return typeof search.location === "string" && search.location !== "" ? { location: search.location } : {};
}

function LaunchRoute() {
  const navigate = useNavigate();
  // the root route passes unknown keys through: the search is read through launchSearch again
  const { location, from } = launchSearch(useSearch({ from: "/launch" }));
  const recent = useRecentRuns();
  return (
    <LaunchPage
      key={from ?? ""}
      onLaunched={(id) => navigate({ to: "/runs/$id", params: { id } })}
      recent={recent}
      initialLocation={location}
      copyFrom={from}
      onClear={() => navigate({ to: "/launch", search: {} })}
    />
  );
}

function RunRoute() {
  const { id } = useParams({ from: "/runs/$id" });
  // A malformed id (/runs/%E0) reaches the page as it is; the page shows its not-found state.
  return <RunDetailPage key={id} id={id} />;
}

function ReportRoute() {
  const { id } = useParams({ from: "/runs/$id/report" });
  const { path } = reportSearch(useSearch({ from: "/runs/$id/report" }));
  return <ReportViewer key={id} id={id} path={path} />;
}

function ResultsRoute() {
  const { id } = useParams({ from: "/runs/$id/results" });
  const { path } = resultsSearch(useSearch({ from: "/runs/$id/results" }));
  return <ResultsBrowser key={id} id={id} path={path} />;
}

function FileRoute() {
  const { id } = useParams({ from: "/runs/$id/results/file" });
  const { path } = resultsSearch(useSearch({ from: "/runs/$id/results/file" }));
  return <FilePreview key={`${id}:${path ?? ""}`} id={id} path={path} />;
}

function NotFoundRoute() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return <NotFound run={pathname.startsWith("/runs/")} />;
}

const root = createRootRoute({ component: AppShell, notFoundComponent: NotFoundRoute });
const routes = [
  createRoute({ getParentRoute: () => root, path: "/", component: HomePage }),
  createRoute({ getParentRoute: () => root, path: "/runs", component: RunsPage, validateSearch: runsSearch }),
  createRoute({ getParentRoute: () => root, path: "/launch", component: LaunchRoute, validateSearch: launchSearch }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id", component: RunRoute, validateSearch: runSearch }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id/report", component: ReportRoute, validateSearch: reportSearch }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id/results", component: ResultsRoute, validateSearch: resultsSearch }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id/results/file", component: FileRoute, validateSearch: resultsSearch }),
];

const routeTree = root.addChildren(routes);

/** The app's router; tests pass a memory history. */
export const createAppRouter = (history?: RouterHistory) => createRouter({ routeTree, history });
export const router = createAppRouter();

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
