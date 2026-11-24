// The runner-channel demo (spikes/runner-channel): builds demo.html and its assets into
// dist-demo, which the spike server serves from ui/ under the runner's root. The base is
// relative, so the build works wherever the spike serves it from; the decoder worker is a
// module, as the product's vite.config.ts sets.
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist-demo",
    emptyOutDir: true,
    assetsInlineLimit: 0,
    rollupOptions: { input: fileURLToPath(new URL("demo.html", import.meta.url)) },
  },
  worker: { format: "es" },
});
