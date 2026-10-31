"""The `stages[]` of `spectio.yml`, and which file applies to a run (P1 Task 27).

The 0.0.1 shape of checking-scenarios §12.1 and the §12.7 note of 2026-10-28: a file holds
`workflow` and `stages[]` only (display only: no gate, watch or `important`), and every other key
is refused. A stage's `match` holds `fnmatchcase` globs on the fully qualified process name
(Nextflow) or the rule name (Snakemake). Parsing YAML is the server's: this module takes the
loaded value, so the SDK needs no YAML library.
"""

import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Engine = Literal["nextflow", "snakemake"]
Text = Annotated[str, Field(min_length=1, max_length=200)]
Glob = Annotated[str, Field(min_length=1, max_length=1024)]
# Never `detected:<n>`, the IDs of detected stages (api §7 `run_stages.stage_id`).
StageId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WorkflowKey(_Strict):
    name: Text
    engine: Engine
    version: Annotated[str, Field(max_length=100)] | None = None  # a range: ">=3.27.0 <4"


class StageDecl(_Strict):
    id: StageId
    name: Text
    match: Annotated[list[Glob], Field(min_length=1, max_length=200)]
    description: Annotated[str, Field(max_length=2000)] | None = None


class SpectioFile(_Strict):
    workflow: WorkflowKey | None = (
        None  # a lab overlay needs it; the workflow's own file may omit it
    )
    stages: Annotated[list[StageDecl], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        ids = [s.id for s in self.stages]
        if len(set(ids)) != len(ids):
            raise ValueError("two stages have the same id")
        return self


_BOUND = re.compile(r"(>=|<=|==|!=|>|<|=)?\s*v?(\d+(?:\.\d+)*)")


def _version(text: str) -> tuple[int, ...]:
    """The leading numbers of a version, `3.27.0` → (3, 27, 0); `v2.5.1` and `3.27.0dev` too."""
    found = re.match(r"v?(\d+(?:\.\d+)*)", text.strip())
    if found is None:
        raise ValueError(f"not a version: {text[:40]!r}")
    return tuple(int(n) for n in found.group(1).split("."))


def _cmp(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    width = max(len(a), len(b))
    a, b = a + (0,) * (width - len(a)), b + (0,) * (width - len(b))
    return (a > b) - (a < b)


def version_in_range(version: str, spec: str) -> bool:
    """Whether `version` meets every bound of `spec` (`">=3.27.0 <4"`, commas allowed); a bound
    with no operator means `==`. Raises ValueError on a spec or a version it cannot read."""
    bounds = [b for b in re.split(r"[\s,]+", spec.strip()) if b]
    have = _version(version)
    ok = {
        ">=": lambda c: c >= 0,
        "<=": lambda c: c <= 0,
        ">": lambda c: c > 0,
        "<": lambda c: c < 0,
        "!=": lambda c: c != 0,
    }
    for bound in bounds:
        found = _BOUND.fullmatch(bound)
        if found is None:
            raise ValueError(f"not a version bound: {bound[:40]!r}")
        op, want = found.group(1) or "==", _version(found.group(2))
        if not ok.get(op, lambda c: c == 0)(_cmp(have, want)):
            return False
    return True


def applies(found: SpectioFile, engine: str, name: str | None, version: str | None) -> bool:
    """Whether a lab overlay is for this run (checking-scenarios §12.7 note): the engine, and the
    name (Nextflow: `manifest.name`; Snakemake: the last part of `workflow.name` is the pipeline
    directory's name); the version range only on Nextflow, and only when the run's version is
    known. A range that cannot be read does not match."""
    key = found.workflow
    if key is None or key.engine != engine or name is None:
        return False
    if engine == "snakemake":
        return key.name.rsplit("/", 1)[-1] == name
    if key.name != name:
        return False
    if key.version is None or version is None:
        return True
    try:
        return version_in_range(version, key.version)
    except ValueError:
        return False
