/// <reference types="vitest/config" />
// The screens (P1 Task 19): `npm run build` writes web/dist, which `spectio serve` serves at `/`.
// No inline script in the build: the server's CSP allows scripts from its own origin only.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true, assetsInlineLimit: 0 },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test-setup.ts"], css: { include: [/runs\.css/] } },
});
