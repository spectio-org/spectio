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
    """The last launch's head; `session` is null for a run started from a terminal, whose head
    is `checked` only when its pointer's boot ID is the server's (architecture §13.8)."""

    session: str | None
    node: str
    alive: bool
    exit_code: int | None
    checked: bool


class TaskSummary(BaseModel):
    done: int
    total: int
    failed: int
    cached: int
    lower_bound: bool  # a checkpoint is open: the total may grow (P1 Task 34)


class RunSummary(BaseModel):
    tasks: TaskSummary
    last_failure: dict[str, JsonValue] | None
    stage_mode: Literal["declared", "detected", "quarters"]  # api §7 (P1 Task 27)
    open_checkpoints: list[str]  # Snakemake checkpoint rules with a job left (P1 Task 34)
    dag_updates: int  # the count of `snakemake.dag_updated`


class EnvironmentSlurm(BaseModel):
    partition: str | None
    account: str | None
    time_min: int | None
    mem_mib: int | None


class EnvironmentLocal(BaseModel):
    cpus: int | None
    mem_mib: int | None


class RunEnvironment(BaseModel):
    """The run's own environment, as resolved at launch (FU-P3-86a, api §5.4); its fields are
    null unless `state` is `recorded`."""

    name: str | None
    label: str | None
    executor: Literal["local", "slurm"] | None
    slurm: EnvironmentSlurm | None
    local: EnvironmentLocal | None
    state: Literal["recorded", "not_recorded", "not_readable"]


class EnvironmentProfiles(BaseModel):
    nextflow: str | None
    snakemake: str | None


class EnvironmentItem(BaseModel):
    """One environment of `GET /environments` (FU-P3-86d, api §5.4): a built-in or one of the
    file's; `usable: false` with its reason, such as a SLURM one on a local server."""

    name: str
    label: str | None
    executor: Literal["local", "slurm"]
    builtin: bool
    default: bool
    usable: bool
    unusable_reason: str | None
    slurm: EnvironmentSlurm | None
    local: EnvironmentLocal | None
    profiles: EnvironmentProfiles
    etag: str


class EnvironmentsFile(BaseModel):
    path: str
    state: Literal["missing", "ok", "refused", "invalid", "unreachable"]
    detail: str | None


class EnvironmentList(BaseModel):
    items: list[EnvironmentItem]
    default: str
    file: EnvironmentsFile


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
    environment: RunEnvironment | None  # null for a run started from a terminal
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
    its log, escape sequences removed, or null when it could not be read. `work_dir` is the
    directory the job files listing shows, for the failure summary's Copy (P1 Task 32)."""

    task_id: str
    attempt_n: int
    process: str
    tag: str | None
    exit_code: int | None
    message: str | None
    native_id: str | None
    scheduler: Scheduler
    log_tail: str | None
    work_dir: str | None


class Command(BaseModel):
    """The engine command as the head script runs it (P1 Task 30): `text` is `argv` quoted for a
    POSIX shell, and names the parameters file, never a value."""

    argv: list[str]
    text: str


class RunRef(BaseModel):
    id: str
    name: str | None
    state: RunState


ResumeReason = Literal[
    "running",
    "head_unverified",
    "resume_in_progress",
    "cli_observed",
    "not_failed_or_cancelled",
    "launch_dir_refused",
    "session_id_refused",
]


class ResumeAction(BaseModel):
    allowed: bool
    reason: ResumeReason | None


class Actions(BaseModel):
    resume: ResumeAction


class EngineSettings(BaseModel):
    """What the engine said of its temporary files (P1 Task 34): Nextflow's `cleanup`;
    Snakemake's `--notemp`, null in 0.0.1 (no event carries it)."""

    cleanup: bool | None
    notemp: bool | None


class RunDetail(Run):
    params: dict[str, JsonValue]
    stages_note: str | None  # why declared stages were not applied (P1 Task 27)
    failures: list[Failure]  # the first 10 (P1 Task 29)
    failures_total: int
    command: Command | None  # null for a run started from a terminal (P1 Task 30)
    parent_run_id: str | None
    resumed_as: list[RunRef]
    actions: Actions
    results_dir: str | None  # null when unknown, and for a run started from a terminal
    engine_settings: EngineSettings


class TemplateWorkflow(BaseModel):
    location: str
    revision: str | None
    engine: Literal["nextflow", "snakemake"]


class CodeLoading(BaseModel):
    """A value that loads code or configuration (dev-env §15.3 req. 16): `field` is a dotted
    path, `params.<name>`, `workflow.location`, or `engine.<option>` for an engine option of
    `spectio.toml`; `writable_by_others` when the path, or a directory above it, is."""

    field: str
    value: str
    writable_by_others: bool


class LaunchTemplate(BaseModel):
    """A `POST /runs` body prefilled from a run, for Copy to a new launch (P1 Task 30), with the
    parameters that differ from the pipeline's defaults and the values that load code."""

    workflow: TemplateWorkflow
    profiles: list[str]
    params: dict[str, JsonValue]
    non_default: list[str]
    code_loading: list[CodeLoading]
    environment: str  # the run's, preselected by name, or the default when it is gone (§5.4)
    environment_notice: str | None  # why the default is preselected instead


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


ProcessStatus = Literal[
    "pending",
    "running",
    "done",
    "failed",
    "stopped",
    "awaiting_checkpoint",
    "not_needed",
    "up_to_date",
    "no_tasks",
]


class JobCount(BaseModel):
    done: int
    total: int  # a lower bound while a checkpoint is open


class Requested(BaseModel):
    """The most common request of the jobs; `varies` when they differ."""

    cpus: int | None
    mem_bytes: int | None
    time_limit_s: int | None
    varies: bool


class Used(BaseModel):
    peak_rss_bytes_max: int | None
    elapsed_s_max: float | None


class ProcessEfficiency(BaseModel):
    """Over the last attempts of its tasks (schedulers §3.6): ratios, 0.63 for 63 %."""

    jobs: JobCount
    measured: int
    cpu_mean: float | None
    cpu_max: float | None
    mem_mean: float | None
    mem_max: float | None
    requested: Requested
    used: Used


class Process(BaseModel):
    process: str
    stage_id: str | None
    counts: dict[str, int]
    retries: int
    status: ProcessStatus  # computed, never stored (P1 Task 34; ui-spec §5.2)
    is_checkpoint: bool
    lower_bound: bool
    efficiency: ProcessEfficiency
    pipeline_order: int  # 0 first: the rule graph's topological order, else `items`' (FU-P3-82)


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


class SlurmRequest(BaseModel):
    """What the engine asked SLURM for (api §5 note of 2026-11-07)."""

    partition: str | None
    account: str | None
    qos: str | None
    cpus: int | None
    mem_bytes: int | None
    mem_per_cpu_bytes: int | None
    time_limit_s: int | None
    gres: str | None
    constraint: str | None
    nodes: int | None
    tasks: int | None


class SlurmAllocated(BaseModel):
    """What SLURM gave the job, from `sacct` once it ended."""

    partition: str | None
    account: str | None
    qos: str | None
    ncpus: int | None
    req_mem_bytes: int | None
    time_limit_s: int | None
    alloc_tres: str | None
    nnodes: int | None


class Slurm(BaseModel):
    """`custom_options`: `slurm_extra` or `clusterOptions` was set, the text never kept."""

    request: SlurmRequest
    allocated: SlurmAllocated | None
    custom_options: bool | None


class Efficiency(BaseModel):
    """A job's CPU and memory efficiency (schedulers §3.6), `cpu` and `mem` ratios, never
    clamped; `peak_rss_bytes` and `elapsed_s` the values they come from."""

    cpu: float | None
    mem: float | None
    elapsed_s: float | None
    peak_rss_bytes: int | None
    state: Literal["running", "pending_accounting", "available", "unavailable"]
    source: Literal["sacct", "trace", "benchmark"] | None
    reason: Literal["local", "no_job_id", "accounting_off", "not_found", "cached"] | None


class Task(BaseModel):
    id: str
    process: str
    tag: str | None
    name: str | None
    state: TaskState
    stage_id: str | None
    attempt_n: int | None  # the last attempt's number, for its files (P1 Tasks 28, 29)
    resources: Resources
    slurm: Slurm | None  # null on a local run (P1 Task 34)
    efficiency: Efficiency


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


class TaskOutput(BaseModel):
    """One output of a Snakemake job's `job_info`: `tbd` for a checkpoint's `<TBD>`."""

    path: str
    state: Literal["present", "not_yet", "absent", "temp_removed", "tbd"]
    protected: bool
    removed_at: str | None


class TaskFiles(BaseModel):
    task_id: str
    attempt: int
    work_dir: str | None  # Nextflow: the task's work directory; Snakemake: the launch directory
    native_id: str | None  # the executor's job ID (SLURM), when known
    files: list[TaskFile]
    outputs: list[TaskOutput] | None  # Snakemake's; null for a Nextflow attempt (P1 Task 34)


class ResultEntry(BaseModel):
    """One entry of a results folder (P1 Task 31): a folder's `size` is null, and so are both
    for a `link_outside`; `mtime` is ISO 8601."""

    name: str
    type: Literal["dir", "file", "link_outside"]
    size: int | None
    mtime: str | None


class ResultStat(BaseModel):
    """The listing's entry for one results path (api §5.3), with the root and the path the
    server answered for."""

    root: str
    path: str
    name: str
    type: Literal["dir", "file", "link_outside"]
    size: int | None
    mtime: str | None


class ResultReport(BaseModel):
    path: str  # relative to the results root
    title: str
    group: str | None  # the folder it shares with other reports, such as FastQC's


class WorkDir(BaseModel):
    """One folder of a Nextflow attempt's work directory (api §5.3, FU-P3-85e): the results
    listing without `reports`, names that start with `.` hidden."""

    root: str
    path: str
    exists: bool
    entries: list[ResultEntry]
    truncated: bool


class Results(BaseModel):
    """One folder of a run's results directory, and the reports found below its root."""

    root: str
    path: str
    exists: bool
    entries: list[ResultEntry]
    truncated: bool
    reports: list[ResultReport]
