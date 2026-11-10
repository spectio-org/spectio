"""A run's target: one Nextflow module or one Snakemake rule (api-and-data-model.md §5.9).

`None` is the whole pipeline. The same model is what the launch stores, what the bridges report
in `onFlowCreate` / `workflow_started` (§14.1), and what `runs.target` holds (§7).
"""

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, ValidationError

# Launch grammars (§5.9): a registry module, its pinned version, and a Snakemake rule.
REGISTRY_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}/[a-z0-9][a-z0-9_.-]{0,127}")
VERSION = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+-]{0,63}")
RULE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
HASH = re.compile(r"[0-9a-f]{32,64}")

MAX_TARGET_CHARS = 4096

Text = Annotated[str, Field(min_length=1, max_length=MAX_TARGET_CHARS)]


class RunTarget(BaseModel):
    """`runs.target`: what a run was limited to. Grammars are enforced at launch; a target a
    bridge reports is only bounded (it describes a run that already happened)."""

    model_config = ConfigDict(
        extra="ignore", frozen=True, strict=True, json_schema_serialization_defaults_required=True
    )

    kind: Literal["module", "rule", "file"]
    name: Text
    version: Text | None = None
    hash: Text | None = None
    source: Literal["registry", "local"] | None = None
    path: Text | None = None
    flag: Literal["target", "until", "allowed_rules"] | None = None
    more: Annotated[StrictInt, Field(ge=0, le=1_000_000)] = 0
    checksum_changed: StrictBool | None = None

    @property
    def label(self) -> str:
        """`nf-core/fastqc@1.0` or `qc_report`: how the screens and notes name it."""
        return f"{self.name}@{self.version}" if self.version else self.name


def reported(value: Any) -> RunTarget | None:
    """The target a bridge reported, or None when it is absent or does not fit: a bad target
    never drops the event that carries it."""
    if value is None:
        return None
    try:
        return RunTarget.model_validate(value)
    except ValidationError:
        return None


def stages_note(target: RunTarget) -> str:
    """The run detail's note for a target run, which has no stages (§5.9)."""
    if target.kind == "module":
        return "This run targets one module"
    return f"This run targets rule {target.name}"
