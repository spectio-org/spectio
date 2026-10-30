"""What the runner hands to the server; the runner never imports the server (architecture §6)."""

from collections import Counter
from dataclasses import dataclass

from spectio_sdk.events import SpoolEvent


@dataclass(frozen=True)
class SpoolBatch:
    """One read of a launch's spool; the caller stores all three in one transaction.

    `cursor` maps a spool file name to the bytes read from it, or to `REFUSED` for a file that
    is never read again and whose drop is counted. Keys that start with "#" are the reader's own:
    the hash of a name outside the grammar (`REFUSED`), and `EXCESS`. `drops` counts what this
    read dropped, by reason (api §14.1).
    """

    events: list[SpoolEvent]
    cursor: dict[str, int]
    drops: Counter[str]


REFUSED = -1  # a cursor offset: the file is never read, and its drop is counted
EXCESS = "#excess"  # a cursor key: the most names found with no slot, already counted


@dataclass(frozen=True)
class Failure:
    """Why a run failed: `runs.failure` (api §7). `class_` is a `failure_class` (api §7)."""

    class_: str
    message: str
    task_id: str | None = None


@dataclass(frozen=True)
class HeadReport:
    """What the runner saw of a launch's head process (schedulers §3.1.1, P1 Assumption 15).

    `state` is the head's own state as the launcher names it (`running` while it lives);
    `ended` is true once it has exited. `failure` is set when the launch could not start, or the
    head ended with no terminal engine event: the runner decides the class (`launch_error`,
    `engine_missing`, `engine_version`, `head_lost`, `engine_fault`).
    """

    state: str
    native_id: str | None
    node: str | None
    exit_code: int | None
    ended: bool
    failure: Failure | None
