"""The run target (api-and-data-model.md §5.10): its model and how the bridges' events carry it."""

from spectio_sdk.events import NextflowFlowCreate, SnakemakeWorkflowStarted
from spectio_sdk.targets import REGISTRY_NAME, RULE, VERSION, RunTarget, reported, stages_note

MODULE = {
    "kind": "module",
    "name": "nf-core/fastqc",
    "version": "0.0.0-6d1763b",
    "hash": "a" * 64,
    "source": "registry",
}


def test_flow_create_keeps_a_module_target() -> None:
    data = NextflowFlowCreate.model_validate({"runName": "x", "target": MODULE})
    assert data.target == RunTarget(**MODULE)  # type: ignore[arg-type]
    assert data.target is not None and data.target.label == "nf-core/fastqc@0.0.0-6d1763b"


def test_a_target_that_does_not_fit_is_dropped_not_the_event() -> None:
    data = NextflowFlowCreate.model_validate(
        {"runName": "x", "target": {"kind": "pipeline", "name": "y"}}
    )
    assert data.runName == "x" and data.target is None
    long = SnakemakeWorkflowStarted.model_validate(
        {"workflow_id": "w", "target": {"kind": "rule", "name": "r" * 5000}}
    )
    assert long.workflow_id == "w" and long.target is None


def test_workflow_started_keeps_a_rule_target() -> None:
    data = SnakemakeWorkflowStarted.model_validate(
        {"target": {"kind": "rule", "name": "qc_report", "flag": "until", "more": 1}}
    )
    assert data.target == RunTarget(kind="rule", name="qc_report", flag="until", more=1)


def test_reported_and_notes() -> None:
    assert reported(None) is None
    assert reported("qc_report") is None
    assert stages_note(RunTarget(**MODULE)) == "This run targets one module"  # type: ignore[arg-type]
    assert stages_note(RunTarget(kind="rule", name="merge")) == "This run targets rule merge"


def test_launch_grammars() -> None:
    assert REGISTRY_NAME.fullmatch("nf-core/fastqc")
    assert not REGISTRY_NAME.fullmatch("nf-core/../x/y")
    assert not REGISTRY_NAME.fullmatch("NF/fastqc")
    assert VERSION.fullmatch("0.0.0-6d1763b") and not VERSION.fullmatch("-x")
    assert RULE.fullmatch("qc_report") and not RULE.fullmatch("1rule")
    assert not RULE.fullmatch("all; rm -rf /")
