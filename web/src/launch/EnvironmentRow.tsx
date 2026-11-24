import { ActionIcon, Button, Drawer, Menu, Modal, NativeSelect, Skeleton } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { type EnvironmentItem, type EnvironmentList, makeDefault } from "../api";
import { DeleteAsk, problem } from "../environments/EnvironmentsPage";
import { EnvironmentForm } from "../environments/EnvironmentForm";
import { EMPTY, fromItem, label, summary } from "../environments/fields";
import { type IconName, Icon } from "../icons";
import { executorLabel } from "../runs/stateWord";
import { useServer } from "../server";
import { usePhone } from "../shell/layout";

// The Environment row of Launch's "Where it runs" (FU-P3-86g; ui-spec §4.8.1 "At Launch"; boards
// LiteLaunch, MLiteLaunch, LiteLaunchNewEnvironment): one usable environment is a text row, two to
// six are radios, more a native select; then New environment, which opens the shared form in a
// dialog (a full-height sheet on the phone). Each radio card carries its actions as a menu: Edit
// (the shared form, prefilled), Set as default and Delete (asked first, as on Environments).

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

/** One kind's icon and word, on the card's second line (ui-spec §4.8.1); decorative, the words say it. */
const KIND_ICONS: Record<string, IconName> = { slurm: "server", local: "terminal" };
const KIND_WORDS: Record<string, string> = { slurm: "SLURM", local: "Login node" };

type CardAction = (env: EnvironmentItem) => void;

/** A card's menu (FU-P3-86g): the trigger names its row; the items are the Environments page's
 * Edit, Make default and Delete, the destructive one last. */
function CardMenu({ env, onEdit, onDefault, onDelete }: { env: EnvironmentItem; onEdit: () => void; onDefault: () => void; onDelete: () => void }) {
  const phone = usePhone();
  return (
    <Menu position="bottom-end" withinPortal returnFocus middlewares={{ flip: true, shift: true }}>
      <Menu.Target>
        <ActionIcon variant="default" size={phone ? "xl" : "lg"} aria-label={`Actions for ${label(env)}`}>
          <Icon name="more" size="button" />
        </ActionIcon>
      </Menu.Target>
      <Menu.Dropdown>
        <Menu.Item onClick={onEdit} leftSection={<Icon name="sliders" size="button" />}>
          Edit
        </Menu.Item>
        {!env.default && (
          <Menu.Item onClick={onDefault} leftSection={<Icon name="check" size="button" />}>
            Set as default
          </Menu.Item>
        )}
        <Menu.Item className="sp-menu-danger" onClick={onDelete} disabled={env.default} leftSection={<Icon name="trash" size="button" />}>
          Delete
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

export function EnvironmentRow(props: Props) {
  const phone = usePhone();
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<EnvironmentItem | null>(null);
  const [asking, setAsking] = useState<EnvironmentItem | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const close = () => (setAdding(false), setEditing(null));
  const refresh = () => props.onRetry();
  const form = (
    <>
      {!editing && <p className="sp-muted">Saved under a name, then listed and chosen in Where it runs. Your launch form is kept.</p>}
      <EnvironmentForm
        key={editing ? editing.name : "new"}
        initial={editing ? fromItem(editing) : EMPTY}
        etag={editing?.etag ?? null}
        saveLabel="Save and choose it"
        onSaved={(item) => (close(), props.onCreated(item))}
        onCancel={close}
        onReload={refresh}
      />
    </>
  );
  const dialog = { opened: adding || !!editing, onClose: close, title: editing ? "Edit environment" : "New environment", returnFocus: true };
  const dialogs = phone ? (
    <Drawer {...dialog} position="bottom" size="100%" classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}>{form}</Drawer>
  ) : (
    <Modal {...dialog} size="lg" centered classNames={{ title: "sp-sheet-title" }}>{form}</Modal>
  );
  // One tree whatever the list's state: the dialog keeps its place, and its values, while the list
  // reloads or fails to (ui-spec §4.8.1 Reload, CR-P3FU86G-03).
  return (
    <>
      <Choice
        {...props}
        onAdd={() => (setActionError(null), setAdding(true))}
        onEdit={(e) => (setActionError(null), setEditing(e))}
        onDelete={(e) => (setActionError(null), setAsking(e))}
        onDefault={(e) =>
          makeDefault(e.name).then(() => (setActionError(null), refresh()), (err: Error) => setActionError(problem(err)))
        }
        actionError={actionError}
        onDismissError={() => setActionError(null)}
      />
      {dialogs}
      <DeleteAsk env={asking} onClose={() => setAsking(null)} onDeleted={() => (setAsking(null), refresh())} onReload={refresh} />
    </>
  );
}

function Choice({
  list,
  failed,
  chosen,
  onChoose,
  onRetry,
  error,
  onAdd,
  onEdit,
  onDelete,
  onDefault,
  actionError,
  onDismissError,
}: Props & {
  onAdd: () => void;
  onEdit: CardAction;
  onDelete: CardAction;
  onDefault: CardAction;
  actionError: string | null;
  onDismissError: () => void;
}) {
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
  const node = server?.node ?? "the server";
  const executor = server?.executor ?? "slurm";
  const line = (e: EnvironmentItem) => summary(e, node, executor);
  // The card's second line names the kind (SLURM, Login node) already: its details leave
  // "(the login node)" out, or the Login node card would say it twice.
  const details = (e: EnvironmentItem) => summary(e, node, executor, true);
  const named = (e: EnvironmentItem) => `${label(e)}, ${executorLabel(e.executor)}`;
  const offered = list.items.filter((e) => e.usable);
  const left = list.items.filter((e) => !e.usable);
  const file = FILE_LINES[list.file.state];
  const errorLine = error && <p id="env-choice-error" className="sp-alert">{error}</p>;
  // New environment waits while the file is not usable (§4.6): the + card and the button say so.
  const waits = file
    ? { "aria-disabled": true, "data-disabled": true, "aria-describedby": "env-file-line" as const }
    : {};
  // The cards carry New environment as their last card; the text row and the select keep a button.
  const cards = offered.length !== 1 && offered.length <= 6;
  let choice;
  if (offered.length === 1) {
    choice = <p>{`Environment: ${label(offered[0])} · ${line(offered[0])}`}</p>;
  } else if (cards) {
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
            <span className="launch-env-body">
              <span className="launch-env-top">
                <span className="launch-env-name">{label(e)}</span>
                <span className="launch-env-side">
                  {e.default && <span className="sp-chip" data-tone="succeeded">Default</span>}
                  <CardMenu env={e} onEdit={() => onEdit(e)} onDefault={() => onDefault(e)} onDelete={() => onDelete(e)} />
                </span>
              </span>
              <span id={`env-sum-${e.name}`} className="launch-env-sum">
                <Icon name={KIND_ICONS[e.executor] ?? "server"} /> {KIND_WORDS[e.executor] ?? e.executor} · {details(e)}
              </span>
            </span>
          </label>
        ))}
        {/* New environment as the last card of the grid (FU-P3-86g). */}
        <button type="button" className="launch-env-add" onClick={() => !file && onAdd()} {...waits}>
          + New environment
        </button>
      </fieldset>
    );
  } else {
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
      {actionError && (
        <div role="alert" className="sp-note sp-alert">
          {actionError} <Button variant="default" size="sm" onClick={() => (onDismissError(), onRetry())}>Reload</Button>
        </div>
      )}
      {left.length > 0 && <p className="sp-muted">{`Not offered: ${left.map((e) => `${e.name} (${e.unusable_reason})`).join("; ")}`}</p>}
      {/* The text row and the select keep the button; the cards' grid carries the + card instead. */}
      {!cards && (
        <Button variant="light" {...waits} onClick={() => !file && onAdd()} fullWidth={phone}>
          New environment
        </Button>
      )}
    </div>
  );
}
