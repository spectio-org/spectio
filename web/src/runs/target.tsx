import type { RunTarget } from "../api";
import { CopyButton } from "./CopyMenu";
import { plural } from "./stateWord";

// The target of a run (ui-spec §4.15; api §5.10): one Nextflow module or one Snakemake rule. The
// run header and the runs list write it the same way; null is the whole pipeline.

const FLAG = { target: "", until: " (--until)", allowed_rules: " (--allowed-rules)" };

/** "module nf-core/fastqc 0.0.0-6d1763b", "rule qc_report (--until)": the version is always written. */
export function targetText(t: RunTarget): string {
  if (t.kind === "module") {
    return `module ${t.name} ${t.version ?? "(no version)"}${t.source === "local" ? " · local" : ""}`;
  }
  const more = t.more > 0 ? ` + ${plural(t.more, "more target", "more targets")}` : "";
  return `${t.kind} ${t.name}${more}${FLAG[t.flag ?? "target"]}`;
}

const SCOPES = {
  pipeline: { label: "Pipeline", cells: [false, false, false] },
  module: { label: "Module", cells: [true] },
  rule: { label: "Rule", cells: [false, true] },
  file: { label: "File", cells: [false, true] },
};

/** The runs list's Scope badge (ui-spec §4.15): a whole pipeline, or the one module, rule or file
 * the run was limited to. The cells repeat what the colour says: three for a pipeline, one lit for
 * a single step. */
export function Scope({ target }: { target: RunTarget | null | undefined }) {
  const kind = target?.kind ?? "pipeline";
  const { label, cells } = SCOPES[kind];
  return (
    <span className="sp-scope" data-scope={kind}>
      <span className="sp-scope-cells" aria-hidden="true">
        {cells.map((on, i) => (
          <i key={i} data-on={on || undefined} />
        ))}
      </span>
      {label}
    </span>
  );
}

/** The runs list's "What ran" (ui-spec §4.15): a rule run names its rule after the pipeline, and a
 * changed checksum shows without opening the run. */
export function TargetTail({ target }: { target: RunTarget | null | undefined }) {
  if (!target) return null;
  const more = target.more > 0 ? ` + ${target.more}` : "";
  return (
    <>
      {target.kind !== "module" && (
        <span className="sp-target-to">
          <span aria-hidden="true">→ </span>
          <span className="sp-sr">target </span>
          {target.name}
          {more}
        </span>
      )}
      {target.checksum_changed && <span className="sp-chip sp-chip-warn">checksum changed</span>}
    </>
  );
}

/** The header's target (ui-spec §4.15): a badge of its parts (kind, name, version, a registry
 * module's checksum), then a changed checksum as a warning with what it means. */
export function TargetLine({ target }: { target: RunTarget }) {
  const registry = target.kind === "module" && target.source === "registry";
  const kind = target.kind === "module" ? "Module" : target.kind === "rule" ? "Rule" : "File";
  return (
    <span className="sp-lines sp-target">
      <span className="sp-target-badge" aria-label={`Target: ${targetText(target)}`} role="group">
        <span className="sp-target-kind" data-scope={target.kind}>
          {kind}
        </span>
        <span className="sp-mono">{target.name}</span>
        {target.kind === "module" && <span className="sp-mono">{target.version ?? "no version"}</span>}
        {target.source === "local" && <span>local</span>}
        {target.more > 0 && <span>+ {plural(target.more, "more target", "more targets")}</span>}
        {target.flag && target.flag !== "target" && <span className="sp-mono">{FLAG[target.flag].trim()}</span>}
        {registry &&
          (target.hash ? (
            <span className="sp-copy-line">
              <span className="sp-mono sp-muted">checksum {target.hash.slice(0, 8)}…</span>
              <CopyButton text={target.hash} label="Copy" name="Copy the module checksum" />
            </span>
          ) : (
            <span className="sp-muted">checksum: after install</span>
          ))}
      </span>
      {registry && target.checksum_changed && (
        <span role="status" className="sp-target-warn">
          <strong>Same version, different content</strong>
          <span>
            This version's checksum differs from an earlier run of {target.name} {target.version}: the registry served
            other files, so results may not match.
          </span>
        </span>
      )}
    </span>
  );
}
