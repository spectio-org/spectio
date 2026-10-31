import "@mantine/core/styles.css";
import "./app.css";
import { MantineProvider } from "@mantine/core";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { router } from "./routes";
import { providerProps } from "./shell/theme";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>
  </StrictMode>,
);
