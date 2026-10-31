import { Stack, Text, Title } from "@mantine/core";
import {
  type RouterHistory,
  createRootRoute,
  createRoute,
  createRouter,
  useNavigate,
  useParams,
} from "@tanstack/react-router";
import { useEffect } from "react";
import { LaunchPage } from "./launch/LaunchPage";
import { AppShell } from "./shell/AppShell";

// The four routes of 0.0.1 (mvp-0.0.1 §1) in the Paper shell (G4).
// Home, the runs list and the run detail come with P1 Task 20.

function Later({ title }: { title: string }) {
  useEffect(() => {
    document.title = `${title} · Spectio`;
  }, [title]);
  return (
    <Stack gap="xs">
      <Title order={1}>{title}</Title>
      <Text c="dimmed">This screen comes with P1 Task 20.</Text>
    </Stack>
  );
}

function LaunchRoute() {
  const navigate = useNavigate();
  return <LaunchPage onLaunched={(id) => navigate({ to: "/runs/$id", params: { id } })} />;
}

function RunRoute() {
  const { id } = useParams({ from: "/runs/$id" });
  return <Later title={`Run ${id}`} />;
}

const root = createRootRoute({ component: AppShell });
const routes = [
  createRoute({ getParentRoute: () => root, path: "/", component: () => <Later title="Home" /> }),
  createRoute({ getParentRoute: () => root, path: "/runs", component: () => <Later title="Runs" /> }),
  createRoute({ getParentRoute: () => root, path: "/launch", component: LaunchRoute }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id", component: RunRoute }),
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
