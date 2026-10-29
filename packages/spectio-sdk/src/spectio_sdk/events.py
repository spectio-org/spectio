"""The spool event contract of driven runs: api-and-data-model.md §14.1.

`SpoolEvent` is the envelope of one spool line (no extra key). `parse_data` returns the
allow-listed model of its type: keys outside the allow-list are dropped, so `script`, `env`,
`commandLine` and the like are never kept (P1 Assumption 3).
"""

from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictInt,
    model_validator,
)

MAX_LINE_BYTES = 65536  # one line, without its "\n"
ROTATE_BYTES = 33554432  # the writer opens the next file before passing it
MAX_FILE_BYTES = 67108864  # the reader ignores anything past it in one file

_ULID = "[0-7][0-9A-HJKMNP-TV-Z]{25}"  # Crockford base32, 128 bits


class UnknownEventType(ValueError):
    """The event's type has no allow-list: the line is dropped and counted."""


class SpoolEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    v: Annotated[StrictInt, Field(ge=1, le=1)]  # Literal[1] would accept true
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    run: Annotated[str, Field(pattern=rf"^run_{_ULID}$")]
    launch: Annotated[StrictInt, Field(ge=1)]
    producer: Annotated[
        str, Field(pattern=r"^(nf-spectio|snakemake-logger-spectio)/[0-9A-Za-z.+-]{1,32}$")
    ]
    seq: Annotated[StrictInt, Field(ge=1)]
    time: AwareDatetime
    type: Annotated[str, Field(pattern=r"^(nextflow|snakemake)\.[A-Za-z_]{1,64}$")]
    data: dict[str, JsonValue]

    @model_validator(mode="after")
    def _producer_matches_engine(self) -> Self:
        engine = "nextflow" if self.producer.startswith("nf-spectio/") else "snakemake"
        if not self.type.startswith(engine + "."):
            raise ValueError(f"producer {self.producer} cannot send {self.type}")
        return self


class _Data(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


# --- Nextflow (nf-spectio) -----------------------------------------------------------------

TraceValue = str | int | float | None


class NextflowTrace(_Data):
    """The trace record, without `script` and `env`."""

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

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
    exitStatus: int | None = None
    errorMessage: str | None = None


class NextflowProcess(NextflowEvent):
    process: str | None = None
    processId: int | None = None


class NextflowTask(NextflowEvent):
    taskId: str | None = None
    hash: str | None = None
    name: str | None = None
    process: str | None = None
    tag: str | None = None
    attempt: int | None = None
    status: str | None = None
    exitStatus: int | None = None
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
    stats: dict[str, int] = {}


class SnakemakeResourcesInfo(_Data):
    cores: int | None = None


class SnakemakeRulegraph(_Data):
    rulegraph: dict[str, JsonValue] = {}


class SnakemakeJobInfo(_Data):
    jobid: int
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
    priority: int | None = None
    threads: int | None = None
    resources: dict[str, JsonValue] = {}


class SnakemakeJobStarted(_Data):
    jobs: list[int]


class SnakemakeJobFinished(_Data):
    job_id: int


class SnakemakeJobError(_Data):
    jobid: int
    rule_name: str | None = None
    input: list[str] = []
    output: list[str] = []
    log: list[str] = []


class SnakemakeShellcmd(_Data):
    """Kept as a record; its content (the job's command) is not."""


class SnakemakeProgress(_Data):
    done: int
    total: int


class SnakemakeError(_Data):
    exception: str | None = None
    msg: str | None = None


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
