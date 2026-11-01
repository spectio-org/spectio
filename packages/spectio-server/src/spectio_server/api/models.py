"""The response models of the read routes (P1 Tasks 18 and 20; api §5, §7; follow-up FU-P3-21).

They type the OpenAPI document that `web/src/api.ts` is written from. The routes still build plain
dictionaries; FastAPI checks each one against its model. The state enums repeat those of
`store.schema`, and `test_openapi.py` checks that they agree.
"""

from typing import Literal

from pydantic import BaseModel, JsonValue

RunState = Literal[
    "queued",
    "running",
    "pausing",
    "paused",
    "awaiting_review",
    "cancelling",
    "succeeded",
    "failed",
    "cancelled",
]
TaskState = Literal[
    "pending",
    "submitted",
    "running",
    "succeeded",
    "failed",
    "cached",
    "stored",
    "aborted",
    "not_scheduled",
]
StageState = Literal["not_started", "running", "awaiting_review", "completed", "failed", "skipped"]
RunOrigin = Literal["ui", "api", "wes", "cli-observed", "cli-adopted"]


class WorkflowRef(BaseModel):
    engine: str | None
    engine_version: str | None
    location: str
    name: str | None
    version: str | None


class Head(BaseModel):
    """The last launch's head; `session` is null for a run started from a terminal."""

    session: str | None
    node: str
    alive: bool
    exit_code: int | None


class TaskSummary(BaseModel):
    done: int
    total: int
    failed: int
    cached: int


class RunSummary(BaseModel):
    tasks: TaskSummary
    last_failure: dict[str, JsonValue] | None
    stage_mode: Literal["declared", "detected", "quarters"]  # api §7 (P1 Task 27)


class Run(BaseModel):
    id: str
    name: str | None
    state: RunState
    origin: RunOrigin | None
    created_at: str
    started_at: str | None
    ended_at: str | None
    workflow: WorkflowRef
    profiles: list[str]
    failure: dict[str, JsonValue] | None
    head: Head | None
    task_counts: dict[str, int]
    summary: RunSummary


class Scheduler(BaseModel):
    """What the scheduler said of a failed job (P1 Task 29): its state and reason, from `sacct`
    or the engine's own message, and requested and used memory and time, from `sacct` or the
    trace. `accounting` says whether `sacct` answered, is being asked, or is unavailable (off,
    not on SLURM, no job ID, or no answer)."""

    state: str | None
    reason: str | None
    state_source: Literal["sacct", "engine_message"] | None
    req_mem_bytes: int | None
    max_rss_bytes: int | None
    time_limit_s: int | None
    elapsed_s: int | None
    usage_source: Literal["sacct", "trace"] | None
    accounting: Literal["available", "pending", "unavailable"]


class Failure(BaseModel):
    """A job that failed on its last attempt (P1 Task 29); `log_tail` is the last 20 lines of
    its log, escape sequences removed, or null when it could not be read."""

    task_id: str
    attempt_n: int
    process: str
    tag: str | None
    exit_code: int | None
    message: str | None
    native_id: str | None
    scheduler: Scheduler
    log_tail: str | None


class RunDetail(Run):
    params: dict[str, JsonValue]
    stages_note: str | None  # why declared stages were not applied (P1 Task 27)
    failures: list[Failure]  # the first 10 (P1 Task 29)
    failures_total: int


class RunList(BaseModel):
    items: list[Run]
    next: str | None


class SummaryGroup(BaseModel):
    key: str
    count: int


class Summary(BaseModel):
    groups: list[SummaryGroup]


class ServerVersion(BaseModel):
    version: str
    node: str
    runs_root: str
    account: str
    executor: str


class Process(BaseModel):
    process: str
    stage_id: str | None
    counts: dict[str, int]
    retries: int


class ProcessList(BaseModel):
    items: list[Process]


class Stage(BaseModel):
    id: str
    position: int
    name: str | None
    source: Literal["declared", "detected"]
    state: StageState
    task_counts: dict[str, int]


class StageList(BaseModel):
    items: list[Stage]


class Resources(BaseModel):
    """Requested (`cpus`, `memory_bytes`, `time_s`) and measured values of the task's last
    attempt; `source` names where the measures come from (P1 Task 29). Unknown: null."""

    cpus: int | None
    memory_bytes: int | None
    time_s: float | None
    realtime_s: float | None
    cpu_percent: float | None
    peak_rss_bytes: int | None
    source: Literal["trace", "benchmark", "sacct"] | None


class Task(BaseModel):
    id: str
    process: str
    tag: str | None
    name: str | None
    state: TaskState
    stage_id: str | None
    attempt_n: int | None  # the last attempt's number, for its files (P1 Tasks 28, 29)
    resources: Resources


class TaskList(BaseModel):
    items: list[Task]
    next: str | None


FileKind = Literal[
    "script",
    "wrapper",
    "stdout",
    "stderr",
    "job_log",
    "exit",
    "marker",
    "trace",
    "rule_log",
    "slurm_log",
]
FileState = Literal["present", "not_yet", "absent", "deleted_after_success", "cleaned"]


class TaskFile(BaseModel):
    """One file of an attempt (P1 Task 28): `size` and `mtime` (ISO 8601) only when `present`."""

    name: str
    kind: FileKind
    size: int | None
    mtime: str | None
    state: FileState
    note: str | None


class TaskFiles(BaseModel):
    task_id: str
    attempt: int
    work_dir: str | None  # Nextflow: the task's work directory; Snakemake: the launch directory
    native_id: str | None  # the executor's job ID (SLURM), when known
    files: list[TaskFile]
