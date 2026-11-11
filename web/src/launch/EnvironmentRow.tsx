import { Button, Drawer, Modal, NativeSelect, Skeleton } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import type { EnvironmentItem, EnvironmentList } from "../api";
import { EnvironmentForm } from "../environments/EnvironmentForm";
import { EMPTY, label, summary } from "../environments/fields";
import { executorLabel } from "../runs/stateWord";
import { useServer } from "../server";
import { usePhone } from "../shell/layout";

// The Environment row of Launch's "Where it runs" (FU-P3-86g; ui-spec §4.8.1 "At Launch"; boards
// LiteLaunch, MLiteLaunch, LiteLaunchNewEnvironment): one usable environment is a text row, two to
// six are radios, more a native select; then New environment, which opens the shared form in a
// dialog (a full-height sheet on the phone).

const FILE_LINES: Record<string, string> = {
  refused: "Your environments file has a mistake",
  invalid: "Your environments file has a mistake",
  unreachable: "Your environments file cannot be read right now",
};

interface Props {
  /** null while it loads. */
  list: EnvironmentList | null;
  failed: boolean;
  chosen: EnvironmentItem | null;
  onChoose: (name: string) => void;
  onRetry: () => void;
  /** A new environment saved in the dialog: list it again and choose it. */
  onCreated: (item: EnvironmentItem) => void;
  /** A `422` on `environment`. */
  error?: string;
}

export function EnvironmentRow(props: Props) {
  const phone = usePhone();
  const [adding, setAdding] = useState(false);
  const close = () => setAdding(false);
  const form = (
    <>
      <p className="sp-muted">Saved under a name, then listed and chosen in Where it runs. Your launch form is kept.</p>
      <EnvironmentForm
        initial={EMPTY}
        etag={null}
        saveLabel="Save and choose it"
        onSaved={(item) => (close(), props.onCreated(item))}
        onCancel={close}
        onReload={props.onRetry}
      />
    </>
  );
  const dialog = { opened: adding, onClose: close, title: "New environment", returnFocus: true };
  const dialogs = phone ? (
    <Drawer {...dialog} position="bottom" size="100%" classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}>{form}</Drawer>
  ) : (
    <Modal {...dialog} size="lg" centered classNames={{ title: "sp-sheet-title" }}>{form}</Modal>
  );
  // One tree whatever the list's state: the dialog keeps its place, and its values, while the list
  // reloads or fails to (ui-spec §4.8.1 Reload, CR-P3FU86G-03).
  return (
    <>
      <Choice {...props} onAdd={() => setAdding(true)} />
      {dialogs}
    </>
  );
}

function Choice({ list, failed, chosen, onChoose, onRetry, error, onAdd }: Props & { onAdd: () => void }) {
  const server = useServer();
  const phone = usePhone();
  if (failed) {
    return (
      <div className="launch-env-state">
        <p className="sp-alert">Environments could not be read</p>
        <Button variant="default" onClick={onRetry}>Retry</Button>
        <p className="sp-muted">The server's default environment will be used</p>
      </div>
    );
  }
  if (!list) {
    return (
      <div className="launch-env-state" aria-busy="true">
        <p className="sp-muted">Loading environments…</p>
        <Skeleton height={44} />
      </div>
    );
  }
  const line = (e: EnvironmentItem) => summary(e, server?.node ?? "the server", server?.executor ?? "slurm");
  const named = (e: EnvironmentItem) => `${label(e)}, ${executorLabel(e.executor)}`;
  const offered = list.items.filter((e) => e.usable);
  const left = list.items.filter((e) => !e.usable);
  const file = FILE_LINES[list.file.state];
  const errorLine = error && <p id="env-choice-error" className="sp-alert">{error}</p>;
  let choice;
  if (offered.length === 1) {
    choice = <p>{`Environment: ${label(offered[0])} · ${line(offered[0])}`}</p>;
  } else if (offered.length > 6) {
    choice = (
      <NativeSelect
        label="Environment"
        inputWrapperOrder={["label", "input", "description", "error"]}
        data={offered.map((e) => ({ value: e.name, label: named(e) }))}
        value={chosen?.name ?? ""}
        onChange={(e) => onChoose(e.currentTarget.value)}
        description={chosen && line(chosen)}
        error={error}
      />
    );
  } else {
    choice = (
      <fieldset className="launch-envs" aria-describedby={error ? "env-choice-error" : undefined}>
        <legend>Environment</legend>
        {offered.map((e) => (
          <label key={e.name} className="launch-env-option">
            <input
              type="radio"
              name="environment"
              value={e.name}
              checked={e.name === chosen?.name}
              onChange={() => onChoose(e.name)}
              aria-label={named(e)}
              aria-describedby={`env-sum-${e.name}`}
            />
            <span>
              <span className="launch-env-name">{label(e)}</span>
              <span className="sp-chip sp-env-badge">{executorLabel(e.executor)}</span>
              {e.default && <span className="sp-chip sp-env-badge" data-tone="succeeded">Default</span>}
              <span id={`env-sum-${e.name}`} className="launch-env-sum">{line(e)}</span>
            </span>
          </label>
        ))}
      </fieldset>
    );
  }
  return (
    <div className="launch-env">
      {file && (
        <p id="env-file-line" className="sp-note">
          {`${file}: only the built-ins are offered. `}
          <Link to="/environments">See Environments</Link>
        </p>
      )}
      {choice}
      {offered.length <= 6 && errorLine}
      {left.length > 0 && <p className="sp-muted">{`Not offered: ${left.map((e) => `${e.name} (${e.unusable_reason})`).join("; ")}`}</p>}
      <Button
        variant="light"
        onClick={() => !file && onAdd()}
        aria-disabled={file ? true : undefined}
        data-disabled={file ? true : undefined}
        aria-describedby={file ? "env-file-line" : undefined}
        fullWidth={phone}
      >
        New environment
      </Button>
    </div>
  );
}
