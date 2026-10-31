"""A stage definition, and the stage of a process or rule (checking-scenarios §12.1 and §12.3).

A declared stage's `match` holds globs; a detected one's holds the names it was built from. Both
match with `fnmatchcase` on the fully qualified Nextflow name (`*` also crosses `:`) or the
Snakemake rule name. A name matched by two stages is an overlap, which §12.3 refuses.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from typing import Literal

Source = Literal["declared", "detected"]
MAX_STAGES = 8  # the gauge holds 1 to 8 sectors (ui-spec §3.2)


@dataclass(frozen=True)
class StageDef:
    id: str
    name: str
    source: Source
    description: str | None
    match: tuple[str, ...]


class Overlap(ValueError):
    """`name` is matched by more than one stage."""

    def __init__(self, name: str, ids: tuple[str, ...]) -> None:
        super().__init__(f"{name} is matched by the stages {', '.join(ids)}")
        self.name, self.ids = name, ids


def assign(stages: Sequence[StageDef], name: str) -> str | None:
    """The ID of the one stage whose `match` matches `name`, or None; raises Overlap."""
    hits = tuple(s.id for s in stages if any(fnmatchcase(name, glob) for glob in s.match))
    if len(hits) > 1:
        raise Overlap(name, hits)
    return hits[0] if hits else None
