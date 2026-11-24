// The runner-channel demo (spikes/runner-channel): one page, one fake run `demo`, one section
// per file, each with Spectio's own viewer — and every byte on the page read from the login
// node by the runner, command by command, through the long-polled channel.
//
// The viewers live inside FilePreview, which picks the kind's viewer from the stat
// (web/src/runs/FilePreview.tsx); the low-level viewers themselves are not exported. A report
// is shown with ReportViewer, the component the run's report tab renders; a PDF has no viewer
// of its own, so the demo shows it in an iframe of its raw route.
//
// The routes the viewers navigate to (a file's back link, the report link) are registered on a
// small in-page router, so the real components work outside the app shell.
import "@mantine/core/styles.css";
import "../../app.css";
import { MantineProvider, SegmentedControl, Text, Title } from "@mantine/core";
import {
  Link,
  Outlet,
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  useSearch,
} from "@tanstack/react-router";
import { type ReactNode, StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { providerProps } from "../../shell/theme";
import { resultUrl } from "../../api";
import { FilePreview } from "../../runs/FilePreview";
import { ReportViewer } from "../../runs/ReportViewer";
import "./channel.css";

const RUN_ID = "demo";

type Section = { file: string; note: ReactNode; body: ReactNode };

/** One section per file, in the order of the task. Spectio keeps one WebGL viewer per page
 * (web/src/runs/imaging/viv.ts), so only the chosen section is mounted. */
const SECTIONS: Section[] = [
  {
    file: "table.csv",
    note: "A CSV, read as text (the tail, then one range at a time) and shown with Spectio's own table viewer.",
    body: <FilePreview id={RUN_ID} search={{ path: "table.csv" }} />,
  },
  {
    file: "multiqc_report.html",
    note: "The pipeline's report, served with the report sandbox the product server sets and shown with ReportViewer, the report tab's component.",
    body: <ReportViewer id={RUN_ID} path="multiqc_report.html" />,
  },
  {
    file: "document.pdf",
    note: (
      <>
        Spectio has no PDF viewer of its own: the product offers a PDF as a download. The demo shows it in an
        iframe of its raw route (no <code>as</code>); the spike server sends it inline, a demo-only difference
        marked in its code.
      </>
    ),
    body: <iframe className="channel-frame" title="document.pdf" src={resultUrl(RUN_ID, "document.pdf")} />,
  },
  {
    file: "gradient.png",
    note: "A PNG, served as an image (a signature-checked read for Sec-Fetch-Dest: image) and shown with the image viewer.",
    body: <FilePreview id={RUN_ID} search={{ path: "gradient.png" }} />,
  },
  {
    file: "multi-channel.ome.tif",
    note: (
      <>
        A three-channel OME-TIFF, read by one closed range per request (<code>as=tiff</code>, a 206 with
        Content-Range) and shown with the OME-TIFF viewer.
      </>
    ),
    body: <FilePreview id={RUN_ID} search={{ path: "multi-channel.ome.tif" }} />,
  },
  {
    file: "image.ome.zarr",
    note: (
      <>
        An OME-Zarr, its metadata and chunks read key by key (<code>as=zarr</code>) and shown with the
        OME-Zarr viewer.
      </>
    ),
    body: <FilePreview id={RUN_ID} search={{ path: "image.ome.zarr" }} />,
  },
];

/** The demo page: a file picker and the chosen file's section. */
function DemoPage() {
  const [file, setFile] = useState(SECTIONS[0].file);
  const section = SECTIONS.find((s) => s.file === file) ?? SECTIONS[0];
  return (
    <main className="channel-page">
      <header className="channel-head">
        <Title order={1}>Runner channel demo</Title>
        <Text className="channel-note">
          One fake run <code>{RUN_ID}</code>. Every byte on this page — the page itself included — was read
          from the login node by the runner, command by command, through the long-polled channel. Open{" "}
          <code>/login?token=…</code> first: the browser's routes take the login cookie, the runner keeps its
          Bearer header.
        </Text>
        <SegmentedControl
          aria-label="File"
          value={file}
          onChange={setFile}
          data={SECTIONS.map((s) => s.file)}
        />
      </header>

      <section className="channel-section" key={section.file}>
        <Title order={2}>{section.file}</Title>
        <Text className="channel-note">{section.note}</Text>
        {section.body}
      </section>
    </main>
  );
}

/** The run's results listing, the page a viewer's back link goes to: the demo's stand-in, with a
 * link per file. */
function DemoResults() {
  const files = [
    "table.csv",
    "multiqc_report.html",
    "document.pdf",
    "gradient.png",
    "multi-channel.ome.tif",
    "image.ome.zarr",
  ];
  return (
    <main className="channel-page">
      <Title order={2}>Results</Title>
      <ul className="channel-list">
        {files.map((file) => (
          <li key={file}>
            <Link to="/runs/$id/results/file" params={{ id: RUN_ID }} search={{ path: file }}>
              {file}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

/** The route a file's "open the report" step lands on: ReportViewer, its path from the search. */
function DemoReport() {
  const search = useSearch({ strict: false }) as { path?: string };
  return <ReportViewer id={RUN_ID} path={search.path ?? "multiqc_report.html"} />;
}

/** The route the results listing's file links land on: FilePreview, its path from the search. */
function DemoFile() {
  const search = useSearch({ strict: false }) as { path?: string };
  return <FilePreview id={RUN_ID} search={{ path: search.path }} />;
}

/** An unknown path: a way back, since the demo has no app shell. */
function DemoMissing() {
  return (
    <main className="channel-page">
      <Title order={2}>Not part of the demo</Title>
      <Link to="/">Back to the demo page</Link>
    </main>
  );
}

const rootRoute = createRootRoute({ component: () => <Outlet />, notFoundComponent: DemoMissing });
const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: "/", component: DemoPage });
const resultsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$id/results",
  component: DemoResults,
});
const reportRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$id/report",
  component: DemoReport,
});
const fileRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$id/results/file",
  component: DemoFile,
});
const routeTree = rootRoute.addChildren([indexRoute, resultsRoute, reportRoute, fileRoute]);
const router = createRouter({ routeTree, history: createMemoryHistory({ initialEntries: ["/"] }) });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MantineProvider {...providerProps}>
      <RouterProvider router={router} />
    </MantineProvider>
  </StrictMode>,
);
