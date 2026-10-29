"""The spool event contract (api-and-data-model.md §14): envelope, allow-lists and caps."""

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from spectio_sdk.events import (
    MAX_FILE_BYTES,
    MAX_LINE_BYTES,
    ROTATE_BYTES,
    SpoolEvent,
    UnknownEventType,
    parse_data,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "engine-events"
CAPTURES = ROOT / "spikes" / "engine-events" / "fixtures"  # spike T2
RUN_ID = "run_01K8T2F1XTVRES000000000000"

# D3 (P1 Assumption 3, inbox #55): never stored, whoever sends them.
DENYLIST = {
    "script",
    "env",
    "homeDir",
    "commandLine",
    "configText",
    "cmd",
    "shellcmd",
    "rule_msg",
}
RAW_COMMAND_KEYS = {"script", "env", "cmd", "shellcmd"}
QUOTED_COMMAND = re.compile(r"(?s)Command '.*?'")


def fixture_lines(pattern: str) -> Iterator[str]:
    files = sorted(FIXTURES.glob(pattern))
    assert files, f"no fixture matches {pattern} in {FIXTURES}"
    for path in files:
        yield from path.read_text(encoding="utf-8").splitlines()


def make_event(type_: str, **data: Any) -> SpoolEvent:
    producer = (
        "nf-spectio/0.0.1" if type_.startswith("nextflow.") else "snakemake-logger-spectio/0.0.1"
    )
    return SpoolEvent.model_validate(
        {
            "v": 1,
            "id": "evt_01K8T2F1XTVRES0000000001",
            "run": RUN_ID,
            "launch": 1,
            "producer": producer,
            "seq": 1,
            "time": "2026-10-28T07:18:46.182Z",
            "type": type_,
            "data": data,
        }
    )


def all_keys(value: Any) -> set[str]:
    """Every key at any depth of a dumped model."""
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in all_keys(v)}
    if isinstance(value, list):
        return {k for v in value for k in all_keys(v)}
    return set()


def test_t2_fixtures_validate() -> None:
    # Every converted line of the T2 bridge captures parses, envelope and data.
    lines = list(fixture_lines("*.spool.jsonl"))
    assert len(lines) > 2000
    for line in lines:
        assert len(line.encode()) <= MAX_LINE_BYTES
        parse_data(SpoolEvent.model_validate_json(line))


def test_one_spool_file_per_bridge_capture() -> None:
    # Tower captures are another protocol (nf-tower), not a spool producer: not converted.
    expected = {
        p.name.removesuffix(".jsonl") + ".spool.jsonl"
        for p in CAPTURES.glob("*.jsonl")
        if "_tower_" not in p.name
    }
    assert len(expected) == 9
    assert {p.name for p in FIXTURES.glob("*.spool.jsonl")} == expected


def test_converted_fixtures_are_current(tmp_path: Path) -> None:
    # convert_t2.py is deterministic, and the committed spool files are its output.
    subprocess.run(
        [sys.executable, str(FIXTURES / "convert_t2.py"), str(CAPTURES), str(tmp_path)],
        check=True,
        capture_output=True,
    )
    for path in FIXTURES.glob("*.spool.jsonl"):
        assert (tmp_path / path.name).read_bytes() == path.read_bytes(), path.name


def test_convert_refuses_a_capture_with_a_secret(tmp_path: Path) -> None:
    # The credential guard of tests/slurm/fixture.py (SECRET) applies: exit 1, nothing written.
    captures, out = tmp_path / "captures", tmp_path / "out"
    captures.mkdir()
    out.mkdir()
    for name in ("snakemake-9.27.1_clean.jsonl", "snakemake-9.27.1_leak.jsonl"):
        record = {"event": "None", "extra": {}, "level": "INFO", "msg": "ok", "seq": 1, "t": 1.0}
        if "leak" in name:
            record["msg"] = "export SLURM_JWT=x"
        (captures / name).write_text(json.dumps(record) + "\n")
    done = subprocess.run(
        [sys.executable, str(FIXTURES / "convert_t2.py"), str(captures), str(out)],
        capture_output=True,
        text=True,
    )
    assert done.returncode == 1
    assert "SLURM_JWT" not in done.stdout + done.stderr
    assert list(out.iterdir()) == []


def test_denylisted_fields_never_survive() -> None:
    # D3: allow-list models drop them, at the top and inside the trace record.
    ev = make_event(
        "nextflow.onTaskComplete",
        script="rm -rf",
        env={"K": "v"},
        commandLine="x",
        taskId="4",
        trace={"script": "rm -rf", "env": "K=v", "native_id": "5734", "workdir": "/w"},
    )
    dumped = parse_data(ev).model_dump()
    assert not {"script", "env", "commandLine"} & dumped.keys()
    assert not DENYLIST & all_keys(dumped)
    assert dumped["trace"]["native_id"] == "5734"


@pytest.mark.parametrize(
    ("type_", "data"),
    [
        (
            "nextflow.onFlowCreate",
            {"homeDir": "/home/u", "configText": "x", "commandLine": "nf run"},
        ),
        ("snakemake.workflow_started", {"cmd": "snakemake --config token=s3cret"}),
        ("snakemake.job_info", {"jobid": 1, "rule_name": "a", "shellcmd": "export K=v"}),
        ("snakemake.job_error", {"jobid": 1, "rule_name": "a", "shellcmd": "export K=v"}),
        ("snakemake.shellcmd", {"shellcmd": "export K=v", "msg": "Shell command: export K=v"}),
    ],
)
def test_command_fields_never_survive(type_: str, data: dict[str, Any]) -> None:
    dumped = parse_data(make_event(type_, **data)).model_dump()
    assert not DENYLIST & all_keys(dumped)
    assert "export K=v" not in repr(dumped)


def test_denylisted_fields_dropped_from_real_captures() -> None:
    # The T2 captures carry script, env, cmd and shellcmd: none survives parse_data.
    for line in fixture_lines("*.spool.jsonl"):
        dumped = parse_data(SpoolEvent.model_validate_json(line)).model_dump()
        assert not DENYLIST & all_keys(dumped), line[:200]


def raw_command_values(value: Any, key: str = "") -> Iterator[str]:
    """Raw command text in a capture: denylisted values and quoted `Command '...'` text."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield from raw_command_values(v, k)
    elif isinstance(value, list):
        for v in value:
            yield from raw_command_values(v, key)
    elif isinstance(value, str):
        if key in RAW_COMMAND_KEYS and len(value.strip()) >= 8:
            yield value
        yield from QUOTED_COMMAND.findall(value)


def test_command_values_never_survive_in_real_captures() -> None:
    # Value level, not key level: no command text reaches the stored data under any key.
    leaks = []
    for line in fixture_lines("*.spool.jsonl"):
        stored = json.dumps(
            parse_data(SpoolEvent.model_validate_json(line)).model_dump(), ensure_ascii=False
        )
        for value in raw_command_values(json.loads(line)):
            if value in stored or json.dumps(value, ensure_ascii=False)[1:-1] in stored:
                leaks.append(value[:80])
    assert not leaks, f"{len(leaks)} command values stored: {leaks[:5]}"


def test_snakemake_error_msg_hides_the_command() -> None:
    msg = (
        'RuleException:\nCalledProcessError in file "Snakefile", line 148:\n'
        "Command 'set -euo pipefail; export TOKEN=s3cret; run' returned non-zero exit status 1."
    )
    kept = parse_data(make_event("snakemake.error", exception="RuleException", msg=msg))
    assert kept.model_dump()["msg"] == (
        'RuleException:\nCalledProcessError in file "Snakefile", line 148:\n'
        "Command «hidden» returned non-zero exit status 1."
    )


def test_snakemake_error_msg_fails_closed() -> None:
    # An unterminated quote does not match the pattern: only the first line is kept.
    msg = "RuleException:\nCommand 'export TOKEN=s3cret; run returned 1"
    kept = parse_data(make_event("snakemake.error", msg=msg)).model_dump()
    assert kept["msg"] == "RuleException:"
    msg = "Command 'export TOKEN=s3cret; run returned 1"
    kept = parse_data(make_event("snakemake.error", msg=msg)).model_dump()
    assert "s3cret" not in kept["msg"]


def test_error_messages_capped() -> None:
    long = "x" * 10_000
    assert len(parse_data(make_event("snakemake.error", msg=long)).model_dump()["msg"]) == 4096
    complete = parse_data(make_event("nextflow.onFlowComplete", errorMessage=long))
    assert len(complete.model_dump()["errorMessage"]) == 4096


GOOD_LINE = {
    "v": 1,
    "id": "evt_a",
    "run": RUN_ID,
    "launch": 1,
    "producer": "snakemake-logger-spectio/0.0.1",
    "seq": 1,
    "time": "2026-10-28T07:18:46.182Z",
    "type": "snakemake.job_finished",
    "data": {"job_id": 7},
}


@pytest.mark.parametrize(
    ("name", "change"),
    [
        ("epoch time number", {"time": 1793171926}),
        ("epoch time string", {"time": "1793171926"}),
        ("year 0001", {"time": "0001-01-01T00:00:00Z"}),
        ("year 1969", {"time": "1969-12-31T23:59:59Z"}),
        ("seq 10**30", {"seq": 10**30}),
        ("launch 2**63", {"launch": 2**63}),
        ("job_id string", {"data": {"job_id": "7"}}),
        ("job_id true", {"data": {"job_id": True}}),
        ("job_id negative", {"data": {"job_id": -1}}),
        ("job_id 10**30", {"data": {"job_id": 10**30}}),
        ("NaN", {"type": "snakemake.resources_info", "data": {"cores": float("nan")}}),
        (
            "NaN in free JSON",
            {"type": "snakemake.rulegraph", "data": {"rulegraph": {"x": float("nan")}}},
        ),
        (
            "big int in free JSON",
            {"type": "snakemake.rulegraph", "data": {"rulegraph": {"x": 10**30}}},
        ),
        ("NUL", {"type": "snakemake.error", "data": {"msg": "a\x00b"}}),
        ("NUL in a key", {"data": {"job_id": 7, "a\x00": 1}}),
    ],
)
def test_poison_lines_refused(name: str, change: dict[str, Any]) -> None:
    line = json.dumps(GOOD_LINE | change, allow_nan=True)
    parse_data(SpoolEvent.model_validate_json(json.dumps(GOOD_LINE)))
    with pytest.raises((ValidationError, ValueError)):
        parse_data(SpoolEvent.model_validate_json(line))


def test_envelope_rejects_unknown_keys_and_bad_run_id() -> None:
    good = make_event("nextflow.onFlowBegin").model_dump(mode="json")
    SpoolEvent.model_validate(good)
    bad_values: list[dict[str, Any]] = [
        {"extra": 1},
        {"run": "../x"},
        {"run": "run_01K8T2F1XTVRES00000000000"},  # 25 characters
        {"run": "run_81K8T2F1XTVRES000000000000"},  # above the 128-bit range
        {"run": "run_01K8T2F1XTVRES00000000000I"},  # I is not Crockford base32
        {"id": "e" * 65},
        {"id": "evt_../x"},
        {"id": "evt_a\n"},
        {"v": 2},
        {"v": True},
        {"launch": 0},
        {"launch": "1"},
        {"launch": True},
        {"seq": 0},
        {"seq": 1.5},
        {"time": "2026-10-28T07:18:46"},  # no time zone
        {"producer": "nf-tower/1.32.2"},
        {"producer": "nf-spectio/"},
        {"type": "spectio.run.created"},
        {"type": "nextflow."},
        {"data": "not an object"},
    ]
    for change in bad_values:
        with pytest.raises(ValidationError):
            SpoolEvent.model_validate(good | change)
    for key in good:
        with pytest.raises(ValidationError):
            SpoolEvent.model_validate({k: v for k, v in good.items() if k != key})


def test_producer_must_match_type_engine() -> None:
    good = make_event("nextflow.onFlowBegin").model_dump(mode="json")
    with pytest.raises(ValidationError):
        SpoolEvent.model_validate(good | {"producer": "snakemake-logger-spectio/0.0.1"})


def test_unknown_type_raises() -> None:
    with pytest.raises(UnknownEventType):
        parse_data(make_event("nextflow.onSomethingNew"))
    with pytest.raises(UnknownEventType):
        parse_data(make_event("snakemake.group_info"))


def test_bad_data_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        parse_data(make_event("snakemake.job_finished", job_id="not a number"))


def test_caps() -> None:
    assert MAX_LINE_BYTES == 64 * 1024
    assert ROTATE_BYTES == 32 * 1024 * 1024
    assert MAX_FILE_BYTES == 64 * 1024 * 1024
