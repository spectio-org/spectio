"""The spool event contract of driven runs: api-and-data-model.md §14.1.

`SpoolEvent` is the envelope of one spool line (no extra key). `parse_data` returns the
allow-listed model of its type: keys outside the allow-list are dropped, so `script`, `env`,
`commandLine` and the like are never kept (P1 Assumption 3).
"""

import math
import re
from datetime import UTC, datetime
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    field_validator,
    model_validator,
)

MAX_LINE_BYTES = 65536  # one line, without its "\n"
ROTATE_BYTES = 33554432  # the writer opens the next file before passing it
MAX_FILE_BYTES = 67108864  # the reader ignores anything past it in one file

MAX_MESSAGE_CHARS = 4096  # error texts are cut here

_ULID = "[0-7][0-9A-HJKMNP-TV-Z]{25}"  # Crockford base32, 128 bits
_RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?(Z|[+-]\d{2}:\d{2})")
_INT64_MAX = 2**63 - 1

Int64 = Annotated[StrictInt, Field(ge=0, le=_INT64_MAX)]
PositiveInt64 = Annotated[StrictInt, Field(ge=1, le=_INT64_MAX)]
SignedInt64 = Annotated[StrictInt, Field(ge=-_INT64_MAX - 1, le=_INT64_MAX)]  # exit codes


def _check_json(value: JsonValue) -> None:
    """Refuse what a JSON parser lets through but no consumer should see."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int) and not -_INT64_MAX - 1 <= value <= _INT64_MAX:
        raise ValueError("integer outside the 64-bit range")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("NaN or infinity")
    if isinstance(value, str) and "\x00" in value:
        raise ValueError("NUL in a string")
    if isinstance(value, list):
        for item in value:
            _check_json(item)
    if isinstance(value, dict):
        for key, item in value.items():
            _check_json(key)
            _check_json(item)


class UnknownEventType(ValueError):
    """The event's type has no allow-list: the line is dropped and counted."""


class SpoolEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    v: Annotated[StrictInt, Field(ge=1, le=1)]  # Literal[1] would accept true
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    run: Annotated[str, Field(pattern=rf"^run_{_ULID}$")]
    launch: PositiveInt64
    producer: Annotated[
        str, Field(pattern=r"^(nf-spectio|snakemake-logger-spectio)/[0-9A-Za-z.+-]{1,32}$")
    ]
    seq: PositiveInt64
    time: AwareDatetime
    type: Annotated[str, Field(pattern=r"^(nextflow|snakemake)\.[A-Za-z_]{1,64}$")]
    data: dict[str, JsonValue]

    @field_validator("time", mode="before")
    @classmethod
    def _time_is_rfc3339(cls, value: object) -> object:
        if not isinstance(value, str) or not _RFC3339.fullmatch(value):
            raise ValueError("time must be an RFC 3339 string with a time zone")
        return value

    @field_validator("time")
    @classmethod
    def _time_in_range(cls, value: datetime) -> datetime:
        try:
            year = value.astimezone(UTC).year
        except OverflowError:
            year = 0
        if not 1970 <= year <= 9999:
            raise ValueError("time outside 1970-9999 UTC")
        return value

    @field_validator("data")
    @classmethod
    def _data_is_plain_json(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        _check_json(value)
        return value

    @model_validator(mode="after")
    def _producer_matches_engine(self) -> Self:
        engine = "nextflow" if self.producer.startswith("nf-spectio/") else "snakemake"
        if not self.type.startswith(engine + "."):
            raise ValueError(f"producer {self.producer} cannot send {self.type}")
        return self


class _Data(BaseModel):
    # strict: "7" or true is not an integer; the envelope already refused NaN and NUL.
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True, allow_inf_nan=False)


# Greedy: a command that quotes the marker text itself is still hidden whole (hiding more is safe).
_QUOTED_COMMAND = re.compile(
    r"(?s)Command '.*' (returned non-zero exit status \d+|died with <[^>]*>)"
)


def _hide_command(msg: str | None) -> str | None:
    """Replace the command an error text quotes; fail closed when the quote is not closed."""
    if msg is None:
        return None
    # Cut first: the pattern's cost stays bounded, and a quote the cut leaves open fails closed.
    msg = _QUOTED_COMMAND.sub(r"Command «hidden» \1", msg[:MAX_MESSAGE_CHARS])
    if "Command '" in msg:
        msg = msg.split("\n", 1)[0]
        if "Command '" in msg:
            msg = msg.split("Command '", 1)[0] + "Command «hidden»"
    return msg


# --- Nextflow (nf-spectio) -----------------------------------------------------------------

TraceValue = str | SignedInt64 | float | None


class NextflowTrace(_Data):
    """The trace record, without `script` and `env`."""

    model_config = ConfigDict(
        extra="ignore", frozen=True, strict=True, allow_inf_nan=False, populate_by_name=True
    )

    task_id: TraceValue = None
    hash: TraceValue = None
    native_id: TraceValue = None
    process: TraceValue = None
    tag: TraceValue = None
    name: TraceValue = None
    status: TraceValue = None
    exit: TraceValue = None
    module: TraceValue = None
    container: TraceValue = None
    cpus: TraceValue = None
    time: TraceValue = None
    disk: TraceValue = None
    memory: TraceValue = None
    attempt: TraceValue = None
    submit: TraceValue = None
    start: TraceValue = None
    complete: TraceValue = None
    duration: TraceValue = None
    realtime: TraceValue = None
    queue: TraceValue = None
    pct_cpu: TraceValue = Field(None, alias="%cpu")
    pct_mem: TraceValue = Field(None, alias="%mem")
    rss: TraceValue = None
    vmem: TraceValue = None
    peak_rss: TraceValue = None
    peak_vmem: TraceValue = None
    rchar: TraceValue = None
    wchar: TraceValue = None
    syscr: TraceValue = None
    syscw: TraceValue = None
    read_bytes: TraceValue = None
    write_bytes: TraceValue = None
    vol_ctxt: TraceValue = None
    inv_ctxt: TraceValue = None
    workdir: TraceValue = None
    scratch: TraceValue = None
    error_action: TraceValue = None
    cpu_model: TraceValue = None
    accelerator: TraceValue = None
    accelerator_type: TraceValue = None


class NextflowEvent(_Data):
    runName: str | None = None
    sessionId: str | None = None


class NextflowFlowCreate(NextflowEvent):
    nextflow: str | None = None
    resume: bool | None = None
    workDir: str | None = None


class NextflowFlowComplete(NextflowEvent):
    success: bool | None = None
    exitStatus: SignedInt64 | None = None
    errorMessage: str | None = None

    @field_validator("errorMessage")
    @classmethod
    def _cap(cls, value: str | None) -> str | None:
        return None if value is None else value[:MAX_MESSAGE_CHARS]


class NextflowProcess(NextflowEvent):
    process: str | None = None
    processId: Int64 | None = None


class NextflowTask(NextflowEvent):
    taskId: str | None = None
    hash: str | None = None
    name: str | None = None
    process: str | None = None
    tag: str | None = None
    attempt: Int64 | None = None
    status: str | None = None
    exitStatus: SignedInt64 | None = None
    errorAction: str | None = None
    cached: bool | None = None
    workDir: str | None = None
    trace: NextflowTrace | None = None


class NextflowFilePublish(NextflowEvent):
    source: str | None = None
    target: str | None = None
    labels: list[str] | None = None


# --- Snakemake (snakemake-logger-plugin-spectio) -------------------------------------------


class SnakemakeLog(_Data):
    level: str | None = None


class SnakemakeWorkflowStarted(_Data):
    workflow_id: str | None = None
    snakemake_version: str | None = None
    rundir: str | None = None
    host: str | None = None
    user: str | None = None


class SnakemakeRunInfo(_Data):
    stats: dict[str, Int64] = {}


class SnakemakeResourcesInfo(_Data):
    cores: Int64 | None = None


class SnakemakeRulegraph(_Data):
    rulegraph: dict[str, JsonValue] = {}


class SnakemakeJobInfo(_Data):
    jobid: Int64
    rule_name: str
    wildcards: dict[str, str] = {}
    input: list[str] = []
    output: list[str] = []
    log: list[str] = []
    benchmark: str | None = None
    reason: str | None = None
    is_checkpoint: bool | None = None
    is_handover: bool | None = None
    local: bool | None = None
    priority: SignedInt64 | None = None
    threads: Int64 | None = None
    resources: dict[str, JsonValue] = {}


class SnakemakeJobStarted(_Data):
    jobs: list[Int64]


class SnakemakeJobFinished(_Data):
    job_id: Int64


class SnakemakeJobError(_Data):
    jobid: Int64
    rule_name: str | None = None
    input: list[str] = []
    output: list[str] = []
    log: list[str] = []


class SnakemakeShellcmd(_Data):
    """Kept as a record; its content (the job's command) is not."""


class SnakemakeProgress(_Data):
    done: Int64
    total: Int64


class SnakemakeError(_Data):
    """`msg` is kept with the quoted command hidden: it can carry `export` values."""

    exception: str | None = None
    msg: str | None = None

    @field_validator("msg")
    @classmethod
    def _hide(cls, value: str | None) -> str | None:
        return _hide_command(value)


_TASK_HOOKS = ("onTaskPending", "onTaskSubmit", "onTaskStart", "onTaskComplete", "onTaskCached")

DATA_MODELS: dict[str, type[_Data]] = {
    "nextflow.onFlowCreate": NextflowFlowCreate,
    "nextflow.onFlowBegin": NextflowEvent,
    "nextflow.onFlowComplete": NextflowFlowComplete,
    "nextflow.onFlowError": NextflowTask,
    "nextflow.onProcessCreate": NextflowProcess,
    "nextflow.onProcessTerminate": NextflowProcess,
    **{f"nextflow.{hook}": NextflowTask for hook in _TASK_HOOKS},
    "nextflow.onFilePublish": NextflowFilePublish,
    "snakemake.log": SnakemakeLog,
    "snakemake.workflow_started": SnakemakeWorkflowStarted,
    "snakemake.run_info": SnakemakeRunInfo,
    "snakemake.resources_info": SnakemakeResourcesInfo,
    "snakemake.rulegraph": SnakemakeRulegraph,
    "snakemake.job_info": SnakemakeJobInfo,
    "snakemake.job_started": SnakemakeJobStarted,
    "snakemake.job_finished": SnakemakeJobFinished,
    "snakemake.job_error": SnakemakeJobError,
    "snakemake.shellcmd": SnakemakeShellcmd,
    "snakemake.progress": SnakemakeProgress,
    "snakemake.error": SnakemakeError,
}


def parse_data(event: SpoolEvent) -> BaseModel:
    """Return the allow-listed model of the event's data; raise `UnknownEventType`."""
    model = DATA_MODELS.get(event.type)
    if model is None:
        raise UnknownEventType(event.type)
    return model.model_validate(event.data)
