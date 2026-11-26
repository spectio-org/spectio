import { Button, NativeSelect, Skeleton } from "@mantine/core";
import { Link } from "@tanstack/react-router";
import { type Resolved, label, summary } from "../environments/fields";
import { executorLabel } from "../runs/stateWord";
import { useServer } from "../server";

// The Profile row of Launch's "Where it runs" (#408; ui-spec §4.8.1 "At Launch"): one native
// select of the execution profiles the pipeline runs with, the chosen one's compute and
// resources under it. Profiles are made on the Profiles page.

interface Props {
  /** The profiles on a usable compute, in the list's order. */
  offered: Resolved[];
  /** The lists were read. */
  loaded: boolean;
  failed: boolean;
  chosen: Resolved | null;
  /** The catalog entry's name when its list of profiles limits the choice. */
  fromEntry: string | null;
  onChoose: (name: string) => void;
  onRetry: () => void;
  /** A `422` on the profile. */
  error?: string;
}

export function ProfileRow({ offered, loaded, failed, chosen, fromEntry, onChoose, onRetry, error }: Props) {
  const server = useServer();
  if (failed) {
    return (
      <div className="launch-env-state">
        <p className="sp-alert">Profiles could not be read</p>
        <Button variant="default" onClick={onRetry}>Retry</Button>
        <p className="sp-muted">The server's default profile will be used</p>
      </div>
    );
  }
  if (!loaded) {
    return (
      <div className="launch-env-state" aria-busy="true">
        <p className="sp-muted">Loading profiles…</p>
        <Skeleton height={44} />
      </div>
    );
  }
  const line = (r: Resolved) => summary(r, server?.node ?? "the server", server?.executor ?? "slurm", true);
  return (
    <div className="launch-env">
      {offered.length === 0 ? (
        <p className="sp-note">
          No profile can be used yet. <Link to="/profiles">See Profiles</Link>
        </p>
      ) : (
        <NativeSelect
          label="Profile"
          inputWrapperOrder={["label", "input", "description", "error"]}
          data={offered.map((r) => ({ value: r.name, label: `${label(r)} · ${r.compute}` }))}
          value={chosen?.name ?? ""}
          onChange={(e) => onChoose(e.currentTarget.value)}
          description={chosen && `Compute ${chosen.compute}, ${executorLabel(chosen.executor)} · ${line(chosen)}`}
          error={error}
        />
      )}
      {fromEntry && <p className="sp-muted">{`The profiles of the catalog entry ${fromEntry}`}</p>}
      <p>
        <Link to="/profiles">Manage profiles</Link>
      </p>
    </div>
  );
}
