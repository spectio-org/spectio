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


class RunDetail(Run):
    params: dict[str, JsonValue]


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


class Task(BaseModel):
    id: str
    process: str
    tag: str | None
    name: str | None
    state: TaskState
    stage_id: str | None


class TaskList(BaseModel):
    items: list[Task]
    next: str | None
