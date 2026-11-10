import { Button, Drawer, Modal } from "@mantine/core";
import { type ReactNode, useState } from "react";
import { ApiError, type Run, deleteRuns } from "../api";
import { useServer } from "../server";
import { usePhone } from "../shell/layout";
import { runName } from "./RunState";
import { plural, runWord } from "./stateWord";

// Delete… and its sheet (ui-spec §4.3 note of 2026-11-10, FU-P3-115b): the runs list's bulk bar
// and Run detail's header share it. aria-modal, Cancel focused first, focus back on Delete… when
// it closes; the API's 409 keeps it open with each refused run named and why.

const SHOWN = 20;

/** Why nothing was deleted: the API's detail, and each run its `errors[]` names. */
function refused(e: Error, runs: Run[]): ReactNode {
  if (!(e instanceof ApiError) || e.status !== 409 || !e.errors.length) return `Nothing was deleted: ${e.message}`;
  const name = (id: string) => {
    const found = runs.find((r) => r.id === id);
    return found ? runName(found) : id;
  };
  return (
    <>
      Nothing was deleted. {e.message}
      <ul>
        {e.errors.map((x) => (
          <li key={x.field}>
            {name(x.field)}: {x.message}
          </li>
        ))}
      </ul>
    </>
  );
}

/** `why`, when set, refuses Delete… (aria-disabled) and says why beside it. `onDeleted` gets the
 * lines to say: "n runs deleted", then each directory the server could not remove. */
export function DeleteRuns({ runs, why, onDeleted }: { runs: Run[]; why: string | null; onDeleted: (said: string[]) => void }) {
  const phone = usePhone();
  const server = useServer();
  const [asking, setAsking] = useState(false);
  const [dirs, setDirs] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ReactNode>(null);
  const root = server?.runs_root ?? "<runs root>";
  const title = `Delete ${plural(runs.length, "run", "runs")}?`;

  const close = () => {
    setAsking(false);
    setDirs(false);
    setError(null);
  };
  const confirm = () => {
    setSending(true);
    setError(null);
    deleteRuns(
      runs.map((r) => r.id),
      dirs,
    )
      .then(({ deleted, directories }) => {
        close();
        const kept = directories.filter((d) => d.result === "failed").map((d) => `${root}/${d.id} could not be removed`);
        onDeleted([`${plural(deleted.length, "run", "runs")} deleted`, ...kept]);
      })
      .catch((e: Error) => setError(refused(e, runs)))
      .finally(() => setSending(false));
  };

  const body = (
    <>
      <ul className="sp-delete-list">
        {runs.slice(0, SHOWN).map((r) => (
          <li key={r.id}>
            {runName(r)} · {runWord(r.state)}
          </li>
        ))}
      </ul>
      {runs.length > SHOWN && <p className="sp-muted">and {runs.length - SHOWN} more</p>}
      <p>Spectio forgets these runs: they leave the list, the counts and Home. Their files stay where they are.</p>
      <label className="sp-check">
        <input type="checkbox" checked={dirs} onChange={(e) => setDirs(e.currentTarget.checked)} aria-describedby="delete-dirs-hint" />
        Also delete their run directories
      </label>
      <p id="delete-dirs-hint" className="sp-note">
        Removes {root}/&lt;run ID&gt; of each run: its work directory, logs and the results inside it. Results written outside the run
        directory are kept. This cannot be undone.
      </p>
      {error && (
        <div role="alert" className="sp-alert">
          {error}
        </div>
      )}
      <div className="sp-actions" data-stack={phone || undefined}>
        <Button variant="default" data-autofocus onClick={close} fullWidth={phone}>
          Cancel
        </Button>
        <Button color="red" onClick={confirm} loading={sending} fullWidth={phone}>
          Delete
        </Button>
      </div>
    </>
  );
  return (
    <>
      <Button
        variant="default"
        color="red"
        onClick={() => why || setAsking(true)}
        aria-disabled={why ? true : undefined}
        data-disabled={why ? true : undefined}
        aria-describedby={why ? "delete-why" : undefined}
      >
        Delete…
      </Button>
      {why && (
        <span id="delete-why" className="sp-muted">
          {why}
        </span>
      )}
      {phone ? (
        <Drawer
          opened={asking}
          onClose={close}
          position="bottom"
          title={title}
          returnFocus
          classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}
        >
          {body}
        </Drawer>
      ) : (
        <Modal opened={asking} onClose={close} title={title} returnFocus centered>
          {body}
        </Modal>
      )}
    </>
  );
}
