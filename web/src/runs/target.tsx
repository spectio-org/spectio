import type { RunTarget } from "../api";
import { CopyButton } from "./CopyMenu";
import { plural } from "./stateWord";

// The target of a run (ui-spec §4.15; api §5.9): one Nextflow module or one Snakemake rule. The
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

/** The header's target line: the text, a registry module's checksum, and a changed checksum. */
export function TargetLine({ target }: { target: RunTarget }) {
  const registry = target.kind === "module" && target.source === "registry";
  return (
    <span className="sp-lines sp-target">
      <span className="sp-copy-line">
        <span className="sp-mono">{targetText(target)}</span>
        {registry &&
          (target.hash ? (
            <>
              <span className="sp-mono sp-muted">checksum {target.hash.slice(0, 8)}…</span>
              <CopyButton text={target.hash} label="Copy" name="Copy the module checksum" />
            </>
          ) : (
            <span className="sp-muted">checksum: after install</span>
          ))}
      </span>
      {registry && target.checksum_changed && (
        <span role="status" className="sp-warn-line">
          This version's checksum differs from an earlier run of {target.name} {target.version}
        </span>
      )}
    </span>
  );
}
