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
 * lines to say: "n runs deleted", then each directory the server could not remove, and the IDs deleted.
 * With `opened` the caller owns the Delete… control (a menu item, UI-09): only the dialog renders,
 * and `onClose` is called when it closes. */
export function DeleteRuns({
  runs,
  why,
  onDeleted,
  opened,
  onClose,
}: {
  runs: Run[];
  why: string | null;
  onDeleted: (said: string[], ids: string[]) => void;
  opened?: boolean;
  onClose?: () => void;
}) {
  const phone = usePhone();
  const server = useServer();
  const [askingHere, setAsking] = useState(false);
  const owned = opened !== undefined;
  const asking = owned ? opened : askingHere;
  const [dirs, setDirs] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ReactNode>(null);
  // the server refused a run directory: the box is what to change (UX-P3FU115B-07)
  const [dirsRefused, setDirsRefused] = useState(false);
  const root = server?.runs_root ?? "<runs root>";
  const title = `Delete ${plural(runs.length, "run", "runs")}?`;
  const one = runs.length === 1; // one run: singular words (FU-P3-116)

  const close = () => {
    setAsking(false);
    onClose?.();
    setDirs(false);
    setError(null);
    setDirsRefused(false);
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
        onDeleted([`${plural(deleted.length, "run", "runs")} deleted`, ...kept], deleted);
      })
      .catch((e: Error) => {
        setError(refused(e, runs));
        setDirsRefused(e instanceof ApiError && e.slug === "directory-not-removable");
      })
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
      <p>
        {one
          ? "Spectio forgets this run: it leaves the list, the counts and Home. Its files stay where they are."
          : "Spectio forgets these runs: they leave the list, the counts and Home. Their files stay where they are."}
      </p>
      <label className="sp-check">
        <input
          type="checkbox"
          checked={dirs}
          onChange={(e) => {
            setDirs(e.currentTarget.checked);
            setDirsRefused(false);
          }}
          aria-invalid={dirsRefused || undefined}
          aria-describedby={dirsRefused ? "delete-dirs-hint delete-error" : "delete-dirs-hint"}
        />
        {one ? "Also delete its run directory" : "Also delete their run directories"}
      </label>
      <p id="delete-dirs-hint" className="sp-note">
        Removes {root}/&lt;run ID&gt; of {one ? "the run" : "each run"}: its work directory, logs and the results inside it. Results written
        outside the run directory are kept. This cannot be undone.
      </p>
      {error && (
        <div id="delete-error" role="alert" className="sp-alert">
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
      {!owned && (
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
      )}
      {!owned && why && (
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
          returnFocus={!owned}
          classNames={{ content: "sp-bottom-sheet", title: "sp-sheet-title" }}
        >
          {body}
        </Drawer>
      ) : (
        <Modal opened={asking} onClose={close} title={title} returnFocus={!owned} centered>
          {body}
        </Modal>
      )}
    </>
  );
}
