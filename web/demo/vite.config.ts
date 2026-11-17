// The graph demo (issue #160): one HTML page with every script, style and image inline, so it opens
// from a file or as a Claude artifact. `node scripts/demo.mjs` builds it and inlines the script.
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  root: resolve(__dirname),
  plugins: [react()],
  base: "./",
  // the imaging decoder worker stays a separate file: the imaging viewer is not part of this demo
  worker: { format: "es" },
  build: {
    outDir: resolve(__dirname, "dist"),
    emptyOutDir: true,
    assetsInlineLimit: 100_000_000,
    cssCodeSplit: false,
    rollupOptions: { output: { inlineDynamicImports: true } },
  },
});
