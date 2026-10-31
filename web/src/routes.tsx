import {
  type RouterHistory,
  createRootRoute,
  createRoute,
  createHashHistory,
  createRouter,
  useNavigate,
  useParams,
  useRouterState,
} from "@tanstack/react-router";
import { HomePage } from "./home/HomePage";
import { LaunchPage } from "./launch/LaunchPage";
import { NotFound, RunDetailPage, runSearch } from "./runs/RunDetailPage";
import { RunsPage, runsSearch } from "./runs/RunsPage";
import { AppShell } from "./shell/AppShell";

// The four routes of 0.0.1 (mvp-0.0.1 §1) in the Paper shell (G4): home, the runs list and the
// run detail (P1 Task 20), and the launch form (Task 19).

function LaunchRoute() {
  const navigate = useNavigate();
  return <LaunchPage onLaunched={(id) => navigate({ to: "/runs/$id", params: { id } })} />;
}

function RunRoute() {
  const { id } = useParams({ from: "/runs/$id" });
  // A malformed id (/runs/%E0) reaches the page as it is; the page shows its not-found state.
  return <RunDetailPage key={id} id={id} />;
}

function NotFoundRoute() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return <NotFound run={pathname.startsWith("/runs/")} />;
}

const root = createRootRoute({ component: AppShell, notFoundComponent: NotFoundRoute });
const routes = [
  createRoute({ getParentRoute: () => root, path: "/", component: HomePage }),
  createRoute({ getParentRoute: () => root, path: "/runs", component: RunsPage, validateSearch: runsSearch }),
  createRoute({ getParentRoute: () => root, path: "/launch", component: LaunchRoute }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id", component: RunRoute, validateSearch: runSearch }),
];

const routeTree = root.addChildren(routes);

/** The app's router; tests pass a memory history. The public demo is static files under a
 * sub-path, whose host answers unknown paths with the docs' 404: it routes by the hash. */
export const createAppRouter = (history?: RouterHistory) => createRouter({ routeTree, history });
export const router = createAppRouter(import.meta.env.MODE === "demo" ? createHashHistory() : undefined);

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
