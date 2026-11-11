// The graph demo (issue #160): the real Spectio screens against the in-page demo server, opened on
// the live run's Graph tab. Built into one HTML file by `node scripts/demo.mjs`.
import "@mantine/core/styles.css";
import "../app.css";
import { MantineProvider } from "@mantine/core";
import { RouterProvider, createMemoryHistory } from "@tanstack/react-router";
import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { createAppRouter } from "../routes";
import { providerProps } from "../shell/theme";
import { DONE, LIVE, SMK, install, isPaused, reset, setPaused } from "./server";
import "./demo.css";

install();
const router = createAppRouter(createMemoryHistory({ initialEntries: [`/runs/${LIVE}?tab=graph&level=process&overlay=state`] }));

const RUNS = [
  { id: LIVE, label: "Live run (Nextflow)" },
  { id: DONE, label: "Previous run" },
  { id: SMK, label: "Failed run (Snakemake)" },
];

function DemoBar() {
  const [open, setOpen] = useState(() => window.innerWidth > 700); // folded on a phone
  const [paused, setP] = useState(isPaused());
  const go = (id: string) => router.navigate({ to: "/runs/$id", params: { id }, search: { tab: "graph" } as never });
  if (!open)
    return (
      <button type="button" className="demo-fab" onClick={() => setOpen(true)} aria-label="Open the demo controls">
        Demo
      </button>
    );
  return (
    <section className="demo-bar" aria-label="Demo controls">
      <header>
        <strong>Workflow graph demo</strong>
        <button type="button" className="demo-x" onClick={() => setOpen(false)} aria-label="Hide the demo controls">
          ×
        </button>
      </header>
      <p>Spectio's real screens, with a simulated server in this page. The live run advances 15 s of pipeline time per second.</p>
      <div className="demo-row" role="group" aria-label="Open a run's graph">
        {RUNS.map((r) => (
          <button key={r.id} type="button" onClick={() => go(r.id)}>
            {r.label}
          </button>
        ))}
      </div>
      <div className="demo-row" role="group" aria-label="Simulation">
        <button type="button" aria-pressed={paused} onClick={() => (setPaused(!paused), setP(!paused))}>
          {paused ? "Resume the run" : "Pause the run"}
        </button>
        <button type="button" onClick={() => (reset(), setP(false), go(LIVE))}>
          Restart the run
        </button>
      </div>
      <details>
        <summary>Things to try</summary>
        <ul>
          <li>Level: Stage, Subworkflow, Process, Jobs (one box per task).</li>
          <li>Layout: Layered, Left to right, Metro, Compact.</li>
          <li>Search: <code>state:running</code>, <code>param:genome</code>, <code>kind:process</code>, <code>STAR</code>.</li>
          <li>Overlay: Duration, CPU, Memory, Failures, Critical path.</li>
          <li>Click a step: parameters, live outputs, its jobs, upstream and downstream.</li>
          <li>Compare with the previous run (it skipped RSeQC).</li>
          <li>Replay and the List view, the keyboard-friendly table.</li>
        </ul>
      </details>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
      <DemoBar />
    </MantineProvider>
  </StrictMode>,
);
