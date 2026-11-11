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
import { useMemo } from "react";
import type { WorkRoot } from "./api";
import { CatalogEntryPage, CatalogPage } from "./catalog/CatalogPage";
import { EnvironmentPage, EnvironmentsPage, envListSearch } from "./environments/EnvironmentsPage";
import { HomePage } from "./home/HomePage";
import { LaunchPage } from "./launch/LaunchPage";
import { ProfilePage } from "./profile/ProfilePage";
import { useRecentRuns } from "./launch/TryPipelines";
import { FilePreview } from "./runs/FilePreview";
import { ReportViewer, reportSearch } from "./runs/ReportViewer";
import { ResultsBrowser, resultsSearch } from "./runs/ResultsBrowser";
import { NotFound, RUN_ID, RunDetailPage, runSearch } from "./runs/RunDetailPage";
import { RunsPage, runsSearch } from "./runs/RunsPage";
import { AppShell } from "./shell/AppShell";

// The four routes of 0.0.1 (mvp-0.0.1 §1) in the Paper shell (G4): home, the runs list and the
// run detail (P1 Task 20), and the launch form (Task 19); and the report viewer (Task 31) and the
// results browser (Task 32), and the preview of one results file (FU-P3-85c); the same two on a
// Nextflow attempt's work directory (FU-P3-85e), which need `task` and `attempt`; and the
// Environments list and form (FU-P3-86f); the Catalog list and form (FU-P3-87d); Profile (FU-P3-112).

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
  const search = reportSearch(useSearch({ from: "/runs/$id/report" }));
  return <ReportViewer key={id} id={id} {...search} />;
}

function ResultsRoute() {
  const { id } = useParams({ from: "/runs/$id/results" });
  const search = resultsSearch(useSearch({ from: "/runs/$id/results" }));
  return <ResultsBrowser key={id} id={id} search={search} />;
}

function FileRoute() {
  const { id } = useParams({ from: "/runs/$id/results/file" });
  const search = resultsSearch(useSearch({ from: "/runs/$id/results/file" }));
  return <FilePreview key={`${id}:${search.path ?? ""}`} id={id} search={search} />;
}

/** The work directory of a page's `task` and `attempt`, one object while they stay the same (the
 * viewers' reads depend on it); null without both. */
function useWork({ task, attempt }: { task?: string; attempt?: number }): WorkRoot | null {
  return useMemo(() => (task && attempt ? { task, attempt } : null), [task, attempt]);
}

function WorkdirRoute() {
  const { id } = useParams({ from: "/runs/$id/workdir" });
  const search = resultsSearch(useSearch({ from: "/runs/$id/workdir" }));
  const work = useWork(search);
  if (!work) return <NotFound run={false} />;
  return <ResultsBrowser key={`${id}:${work.task}:${work.attempt}`} id={id} search={search} work={work} />;
}

function WorkdirFileRoute() {
  const { id } = useParams({ from: "/runs/$id/workdir/file" });
  const search = resultsSearch(useSearch({ from: "/runs/$id/workdir/file" }));
  const work = useWork(search);
  if (!work) return <NotFound run={false} />;
  return <FilePreview key={`${id}:${work.task}:${work.attempt}:${search.path ?? ""}`} id={id} search={search} work={work} />;
}

/** `/environments/new?from=<name>`: the form, prefilled from that environment (Duplicate). */
export const envSearch = (search: Record<string, unknown>): { from?: string } =>
  typeof search.from === "string" && /^[a-z][a-z0-9-]{0,31}$/.test(search.from) ? { from: search.from } : {};

function NewEnvironmentRoute() {
  const { from } = envSearch(useSearch({ from: "/environments/new" }));
  return <EnvironmentPage key={from ?? ""} name={null} from={from} />;
}

function EnvironmentRoute() {
  const { name } = useParams({ from: "/environments/$name" });
  return <EnvironmentPage key={name} name={name} />;
}

function CatalogEntryRoute() {
  const { name } = useParams({ from: "/catalog/$name" });
  return <CatalogEntryPage key={name} name={name} />;
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
  createRoute({ getParentRoute: () => root, path: "/runs/$id/workdir", component: WorkdirRoute, validateSearch: resultsSearch }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id/workdir/file", component: WorkdirFileRoute, validateSearch: resultsSearch }),
  createRoute({ getParentRoute: () => root, path: "/environments", component: EnvironmentsPage, validateSearch: envListSearch }),
  createRoute({ getParentRoute: () => root, path: "/environments/new", component: NewEnvironmentRoute, validateSearch: envSearch }),
  createRoute({ getParentRoute: () => root, path: "/environments/$name", component: EnvironmentRoute }),
  createRoute({ getParentRoute: () => root, path: "/catalog", component: CatalogPage }),
  createRoute({ getParentRoute: () => root, path: "/catalog/new", component: () => <CatalogEntryPage name={null} /> }),
  createRoute({ getParentRoute: () => root, path: "/catalog/$name", component: CatalogEntryRoute }),
  createRoute({ getParentRoute: () => root, path: "/profile", component: ProfilePage }),
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
