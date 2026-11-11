// A step's code (issue #160): BioFlow-Insight's copy on the Launch map, else the definition the
// server finds by name in the pipeline's files (GET /workflows:source). Shown as text only, with
// line numbers, in the node sheet and in the map's right-click card.
import { useEffect, useState } from "react";
import { Icon } from "../../icons";
import { copyText } from "../CopyMenu";
import { type SourceBlock, getSource } from "./types";

export interface CodeSource {
  location: string;
  revision: string | null;
  /** Read for a run: the pipeline's code today, which the run may not have used. */
  fromRun?: boolean;
}

export function Code({ name, code, where }: { name: string; code?: string | null; where?: CodeSource | null }) {
  const [block, setBlock] = useState<SourceBlock | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setBlock(null);
    setError(null);
    if (code || !where) return;
    const controller = new AbortController();
    getSource(where.location, where.revision, name, controller.signal).then(setBlock, (e: Error) => controller.signal.aborted || setError(e.message));
    return () => controller.abort();
  }, [name, code, where?.location, where?.revision]);
  if (code) return <Lines text={code} first={1} label={`Code of ${name}`} name={name} />;
  if (!where) return <p className="sp-muted">The code is not available here.</p>;
  if (error) return <p className="sp-muted">The code was not found: {error}</p>;
  if (!block) return <p className="sp-muted">Reading the code…</p>;
  return (
    <>
      <p className="sp-muted">
        <span className="sp-mono">
          {block.file}:{block.line}
        </span>
        {block.truncated && " (cut after 300 lines)"}
        {where.fromRun && " · the pipeline's current code, which may differ from what this run used"}
      </p>
      <Lines text={block.code} first={block.line} label={`Code of ${name}`} name={name} />
    </>
  );
}

function Lines({ text, first, label, name }: { text: string; first: number; label: string; name: string }) {
  const lines = text.split("\n");
  const [said, setSaid] = useState<string | null>(null);
  return (
    <div className="sp-gcode-wrap">
      <button
        type="button"
        className="sp-gcode-copy"
        aria-label={`Copy the code of ${name}`}
        onClick={() => copyText(text).then(() => setSaid("Copied"), () => setSaid("Could not copy: select the text instead"))}
      >
        <Icon path={COPY} size={13} stroke={1.9} /> Copy
      </button>
      <span role="status" className="sp-gcode-said">
        {said}
      </span>
      <pre className="sp-gcode" aria-label={label} tabIndex={0}>
        {lines.map((l, i) => (
          <span key={i} className="sp-gcode-line">
            <span className="sp-gcode-n" aria-hidden="true">
              {first + i}
            </span>
            {l || " "}
            {"\n"}
          </span>
        ))}
      </pre>
    </div>
  );
}

const COPY = "M9 9h11v11H9z M5 15H4V4h11v1";
