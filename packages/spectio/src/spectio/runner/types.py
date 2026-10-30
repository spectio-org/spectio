"""What the runner hands to the server; the runner never imports the server (architecture §6)."""

from collections import Counter
from dataclasses import dataclass

from spectio_sdk.events import SpoolEvent


@dataclass(frozen=True)
class SpoolBatch:
    """One read of a launch's spool; the caller stores all three in one transaction.

    `cursor` maps a file name to the bytes read from it, or to `REFUSED` for a file skipped and
    already counted. `drops` counts what this read dropped, by reason (api §14.1).
    """

    events: list[SpoolEvent]
    cursor: dict[str, int]
    drops: Counter[str]


REFUSED = -1  # a cursor offset: the file is never read, and its drop is counted
