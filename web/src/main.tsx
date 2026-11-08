import "@mantine/core/styles.css";
import "./app.css";
import { MantineProvider } from "@mantine/core";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { router } from "./routes";
import { providerProps } from "./shell/theme";

async function start() {
  // The public demo (`npm run build:demo`): the API answered from a recording, and a banner.
  const demo = import.meta.env.MODE === "demo" ? await import("./demo") : null;
  demo?.startDemo();
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <MantineProvider {...providerProps}>
        {demo && <demo.DemoBanner />}
        <RouterProvider router={router} />
      </MantineProvider>
    </StrictMode>,
  );
}
void start();
