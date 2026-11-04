/// <reference types="vitest/config" />
// The screens (P1 Task 19): `npm run build` writes web/dist, which `spectio serve` serves at `/`.
// `npm run build:demo` (mode "demo") writes web/dist-demo, the public read-only demo: relative
// asset paths, so it works under any sub-path (spectio.pages.dev/demo/).
// No inline script in the build: the server's CSP allows scripts from its own origin only.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === "demo" ? "./" : "/",
  build: { outDir: mode === "demo" ? "dist-demo" : "dist", emptyOutDir: true, assetsInlineLimit: 0 },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test-setup.ts"], css: { include: [/runs\.css/] } },
}));
