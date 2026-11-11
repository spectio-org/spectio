// The Launch form's Workflow map (issue #160; ui-spec §4.14): the pipeline's graph before any
// run, from GET /workflows:graph. Explore it, search it, open a step to see its source,
// condition and the parameters it reads.
import { useEffect, useState } from "react";
import type { ApiError } from "../../api";
import { usePhone } from "../../shell/layout";
import { Code } from "./Code";
import { GraphView, Links, Panel, kindIcon, kindWord } from "./GraphView";
import { type ViewNode, collapse } from "./model";
import { type GraphSettings, settingsOf } from "./settings";
import { type GraphDocument, getWorkflowGraph } from "./types";

export function LaunchMap({ location, revision, name }: { location: string; revision: string | null; name: string }) {
  const phone = usePhone();
  const [doc, setDoc] = useState<GraphDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [settings, setSettings] = useState<GraphSettings>(() => settingsOf({}, phone));
  const [open, setOpen] = useState<ViewNode | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setDoc(null);
    setError(null);
    getWorkflowGraph(location, revision, controller.signal)
      .then(setDoc)
      .catch((e: ApiError) => controller.signal.aborted || setError(e.message));
    return () => controller.abort();
  }, [location, revision]);
  if (error) return <p role="alert">The map could not be drawn: {error}</p>;
  if (!doc) return <p className="sp-muted">Reading the pipeline's steps…</p>;
  if (doc.nodes.length === 0) return <p className="sp-empty">No step was found in the pipeline's code.</p>;
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const members = open ? open.members.map((m) => byId.get(m)).filter((m) => !!m) : [];
  return (
    <>
      <GraphView
        doc={doc}
        title={name}
        settings={settings}
        onSettings={(p) => setSettings((s) => ({ ...s, ...p }))}
        onOpen={setOpen}
        source={{ location, revision }}
        side={
          <Panel id={open?.id ?? null} opened={open !== null} onClose={() => setOpen(null)} title={open ? `${open.label} (${kindWord(open.kind)})` : ""} icon={kindIcon(open?.kind ?? "process")}>
            {open && (
              <section className="sp-sheet" aria-label={open.label}>
                <Links view={collapse(doc, settings.level, undefined, settings.fold)} id={open.id} />
                <ul className="sp-gsheet-list" aria-label={`Steps of ${open.label}`}>
                  {members.map((m) => (
                    <li key={m.id}>
                      <span className="sp-mono">{m.id}</span>
                      {m.source && <span className="sp-muted">{`${m.source.file}${m.source.line ? `:${m.source.line}` : ""}`}</span>}
                      {m.condition && (
                        <span>
                          when <code>{m.condition}</code>
                        </span>
                      )}
                      {m.params.length > 0 && <span className="sp-muted">reads {m.params.join(", ")}</span>}
                    </li>
                  ))}
                </ul>
                {members.length === 1 && (
                  <>
                    <h3 className="sp-sheet-h">Code</h3>
                    <Code name={members[0].id} code={members[0].code} where={{ location, revision }} />
                  </>
                )}
              </section>
            )}
          </Panel>
        }
        notes={
          doc.producer === "stages-only" ? (
            <p className="sp-gnote">The links between steps are not known before the run: steps are grouped by stage, without arrows.</p>
          ) : doc.producer === "bioflow-insight" ? (
            <p className="sp-gnote">Read from the pipeline's code by BioFlow-Insight; the run may take fewer paths.</p>
          ) : null
        }
      />
    </>
  );
}
