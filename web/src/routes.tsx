import { Stack, Text, Title } from "@mantine/core";
import {
  Link,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  useNavigate,
  useParams,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { type ServerVersion, getVersion } from "./api";
import { LaunchPage } from "./launch/LaunchPage";
import { ServerContext } from "./server";

// The four routes of 0.0.1 (mvp-0.0.1 §1) in a thin shell that G4 replaces with the Paper shell:
// a top bar with the server's node, links on the side, a tab bar on the phone.
// Home, the runs list and the run detail come with P1 Task 20.

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/runs", label: "Runs" },
  { to: "/launch", label: "Launch" },
] as const;

function Links() {
  return LINKS.map((link) => (
    <Link key={link.to} to={link.to} activeOptions={{ exact: true }} className="nav-link">
      {link.label}
    </Link>
  ));
}

function Shell() {
  const [server, setServer] = useState<ServerVersion | null>(null);
  const [down, setDown] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    getVersion(controller.signal)
      .then(setServer)
      .catch((e: Error) => controller.signal.aborted || setDown(e.message));
    return () => controller.abort();
  }, []);
  return (
    <ServerContext.Provider value={server}>
      <header className="topbar">
        <Text fw={700} size="lg">
          Spectio
        </Text>
        <Text size="sm" c="dimmed" role="status">
          {server
            ? `Spectio ${server.version} · server on ${server.node}`
            : down
              ? `Server not reached: ${down}`
              : "Connecting…"}
        </Text>
      </header>
      <div className="layout">
        <nav className="sidebar" aria-label="Main">
          <Links />
        </nav>
        <main className="content">
          <Outlet />
        </main>
      </div>
      <nav className="tabbar" aria-label="Tabs">
        <Links />
      </nav>
    </ServerContext.Provider>
  );
}

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

const root = createRootRoute({ component: Shell });
const routes = [
  createRoute({ getParentRoute: () => root, path: "/", component: () => <Later title="Home" /> }),
  createRoute({ getParentRoute: () => root, path: "/runs", component: () => <Later title="Runs" /> }),
  createRoute({ getParentRoute: () => root, path: "/launch", component: LaunchRoute }),
  createRoute({ getParentRoute: () => root, path: "/runs/$id", component: RunRoute }),
];

export const router = createRouter({ routeTree: root.addChildren(routes) });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
