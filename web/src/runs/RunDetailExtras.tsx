import { Button, Modal } from "@mantine/core";
import { type ReactNode, useEffect, useState } from "react";
import { ApiError, type RunConfigFile, type RunDetail, getConfigFile } from "../api";
import { runEnvName } from "../environments/fields";
import { Icon } from "../icons";
import { memWords, resourceWords, timeWords } from "../launch/RunExtras";
import { usePhone } from "../shell/layout";
import { copyText } from "./CopyMenu";

// Run detail's Default resources and Extra config file facts (FU-P3-110d; ui-spec §4.6 "Run detail
// facts" and the drawn layout of FU-P3-110c; api §5.7; board LiteRunDetail): no row for a run whose
// launch set neither. The kept file is read (GET /runs/{id}/config-file) only when View is
// pressed, so "changed since the launch" and "gone" are said in its sheet, never on the fact
// (UX-P3FU110C-02).

const kib = (n: number) => (n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KiB`);

/** The two facts, after the environment's. */
export function extrasFacts(run: RunDetail): [string, ReactNode][] {
  const found: [string, ReactNode][] = [];
  if (run.default_resources) found.push(["Default resources", <ResourcesFact run={run} />]);
  if (run.config_file) found.push(["Extra config file", <ConfigFileFact id={run.id} kept={run.config_file} />]);
  return found;
}

function Damaged({ what }: { what: string }) {
  return (
    <span className="sp-lines">
      <span>Not readable</span>
      <span className="sp-muted">{what}</span>
    </span>
  );
}

/** "8 CPUs · 64 GiB · 12 h per task", a key left out worded from a `slurm` environment's value,
 * then what the values replaced; the values alone when the environment's record is not readable. */
function ResourcesFact({ run }: { run: RunDetail }) {
  const r = run.default_resources!;
  if (r.state !== "recorded") return <Damaged what="The run's record of them is damaged; the run itself is not affected." />;
  const env = run.environment;
  const slurm = env?.state === "recorded" && env.executor === "slurm" ? env.slurm : null;
  const name = env ? runEnvName(env) : "";
  const set = resourceWords(r);
  const left = slurm
    ? [
        r.mem_mib == null && `memory: ${slurm.mem_mib ? `${memWords(slurm.mem_mib)} from ${name}` : "none set, the pipeline's default"}`,
        r.time_min == null && `time: ${slurm.time_min ? `${timeWords(slurm.time_min)} from ${name}` : "none set, the pipeline's default"}`,
      ]
    : [];
  const replaced = slurm
    ? [r.time_min != null && slurm.time_min && timeWords(slurm.time_min), r.mem_mib != null && slurm.mem_mib && memWords(slurm.mem_mib)].filter(Boolean)
    : [];
  const sub = [
    `Set at Launch${replaced.length ? `, in place of ${name}'s ${replaced.join(" and ")}` : ""}`,
    `${run.workflow.engine === "snakemake" ? "rules" : "processes"} that set their own keep them`,
  ].join(" · ");
  return (
    <span className="sp-lines">
      <span>{[set && `${set} per task`, ...left].filter(Boolean).join(" · ")}</span>
      <span className="sp-muted">{sub}</span>
    </span>
  );
}

/** The path, what the run keeps of it, View and Copy SHA-256, and the `includes` warning. */
function ConfigFileFact({ id, kept }: { id: string; kept: RunConfigFile }) {
  const [viewing, setViewing] = useState(false);
  const [said, setSaid] = useState<string | null>(null);
  useEffect(() => {
    if (!said) return;
    const timer = setTimeout(() => setSaid(null), 4000);
    return () => clearTimeout(timer);
  }, [said]);
  if (kept.state !== "recorded" || !kept.path || !kept.kept_as || !kept.sha256) {
    return <Damaged what="The run's record of it is damaged" />;
  }
  const { path, kept_as: name, sha256 } = kept;
  const size = kib(kept.size ?? 0);
  const copy = () =>
    copyText(sha256)
      .then(() => setSaid(`Copied the SHA-256 of ${name}`))
      .catch(() => setSaid(`Could not copy the SHA-256 of ${name}: the browser gave no clipboard`));
  return (
    <span className="sp-lines">
      <span className="sp-mono">{path}</span>
      <span className="sp-muted">
        kept as <span className="sp-mono">{name}</span> · {size} · SHA-256 <span className="sp-mono">{sha256.slice(0, 12)}</span>…
      </span>
      <span className="sp-extra-buttons">
        <Button variant="default" size="xs" aria-haspopup="dialog" onClick={() => setViewing(true)}>
          View {name}
        </Button>
        <Button variant="default" size="xs" aria-label={`Copy SHA-256 of ${name}`} onClick={copy}>
          Copy SHA-256
        </Button>
      </span>
      <span role="status" className="sp-muted">
        {said}
      </span>
      {kept.includes && <IncludesWarning />}
      <KeptFileSheet id={id} name={name} path={path} size={size} sha256={sha256} includes={!!kept.includes} opened={viewing} onClose={() => setViewing(false)} />
    </span>
  );
}

function IncludesWarning() {
  return (
    <span className="sp-extra-warn">
      <Icon name="alert" />
      <span>It loads other files with includeConfig; those are not kept with the run.</span>
    </span>
  );
}

type Read = { state: "reading" } | { state: "read"; text: string; changed: boolean } | { state: "gone" } | { state: "failed" };

/** The kept text in a sheet (aria-modal; Close and Escape return focus to View); the text is
 * dropped when it closes, as it may hold credentials (SEC-P3FU110D-01). */
function KeptFileSheet(props: { id: string; name: string; path: string; size: string; sha256: string; includes: boolean; opened: boolean; onClose: () => void }) {
  const { id, name, path, size, sha256, includes, opened, onClose } = props;
  const phone = usePhone();
  const [read, setRead] = useState<Read>({ state: "reading" });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    setRead({ state: "reading" });
    if (!opened) return;
    const controller = new AbortController();
    getConfigFile(id, controller.signal)
      .then((got) => setRead({ state: "read", text: got.text, changed: got.sha256 !== null && got.sha256 !== sha256 }))
      .catch((e: Error) => controller.signal.aborted || setRead({ state: e instanceof ApiError && e.status === 404 ? "gone" : "failed" }));
    return () => controller.abort();
  }, [opened, attempt, id, sha256]);
  return (
    <Modal opened={opened} onClose={onClose} title={name} size="lg" fullScreen={phone} closeButtonProps={{ "aria-label": "Close" }}>
      <p className="sp-muted sp-mono">{`${path} · ${size}`}</p>
      {includes && <IncludesWarning />}
      {read.state === "reading" && <p role="status">Reading the kept copy…</p>}
      {read.state === "gone" && <p role="alert">{`The kept copy of ${name} is not in the run directory any more.`}</p>}
      {read.state === "failed" && (
        <p className="sp-copy-line">
          <span role="alert">The run directory did not answer; try again.</span>
          <Button variant="default" size="xs" onClick={() => setAttempt((n) => n + 1)}>
            Retry
          </Button>
        </p>
      )}
      {read.state === "read" && (
        <>
          {read.changed && (
            <p role="status" className="sp-extra-warn">
              Changed since the launch: the kept copy's SHA-256 is not the one recorded. The preview shows the file as it is now.
            </p>
          )}
          <pre className="sp-extra-text" tabIndex={0} aria-label={`Contents of ${name}`}>
            {read.text}
          </pre>
        </>
      )}
    </Modal>
  );
}
