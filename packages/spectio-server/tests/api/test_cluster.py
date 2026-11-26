"""`GET /api/v1/cluster/facts` (#401): the SLURM lookup parsed from synthetic command output,
served from a cache, and `scheduler: null` where there is no SLURM. No test runs a SLURM
command: `Facts.run` is replaced. Every name here is made up."""

import os
import pwd
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spectio.config import Settings, SlurmOpts
from spectio_server import cluster
from spectio_server.cluster import Facts, assemble, parse_gres, parse_sinfo

FACTS = "/api/v1/cluster/facts"
SINFO = """\
cpu*|7-00:00:00|30|128|515000|amd,zen4|(null)|idle
cpu*|7-00:00:00|10|128|515000|amd,zen4|(null)|mixed
cpu*|7-00:00:00|2|128|515000|amd,zen4|(null)|down*
gpu|1-00:00:00|3|64|257000|intel|gpu:H100:4(S:0-1)|idle
gpu|1-00:00:00|1|64|257000|intel|gpu:H100:4(S:0-1)|allocated
gpu|1-00:00:00|2|32|128000|intel,old|gpu:4|idle
test|30:00|1|8|16000|(null)|(null)|idle
big|infinite|4|256|1000000|(null)|gpu:L40:2,shard:8|idle
garbage line
x|1|2
"""
SCONTROL = """\
PartitionName=cpu AllowGroups=ALL AllowAccounts=ALL Default=YES State=UP
PartitionName=gpu AllowGroups=ALL AllowAccounts=lab-a,lab-c Default=NO State=UP
PartitionName=test AllowGroups=nobody-group AllowAccounts=ALL Default=NO State=UP
PartitionName=big AllowGroups=ALL AllowAccounts=ALL Default=NO State=UP
"""
ASSOC = "lab-a|\nlab-b|cpu\nlab-a|\n"


def by_name(body: dict[str, Any]) -> dict[str, Any]:
    return {p["name"]: p for p in body["partitions"]}


def test_sinfo_groups_the_states_of_a_partition() -> None:
    parts = parse_sinfo(SINFO)
    assert list(parts) == ["cpu", "gpu", "test", "big"]
    assert parts["cpu"] == {
        "default": True,
        "max_time_min": 10080,
        "groups": [
            {
                "nodes": 42,
                "idle": 30,  # `down*` and `mixed` are not idle
                "cpus": 128,
                "mem_mib": 515000,
                "features": ["amd", "zen4"],
                "gpus": [],
            }
        ],
    }
    gpu = parts["gpu"]
    assert gpu["default"] is False and gpu["max_time_min"] == 1440
    assert [(g["nodes"], g["idle"], g["cpus"]) for g in gpu["groups"]] == [(4, 3, 64), (2, 2, 32)]
    assert gpu["groups"][0]["gpus"] == [{"type": "H100", "count": 4}]
    assert gpu["groups"][1]["gpus"] == [{"type": None, "count": 4}]
    assert gpu["groups"][1]["features"] == ["intel", "old"]
    assert parts["test"]["max_time_min"] == 30
    assert parts["big"]["max_time_min"] is None  # infinite
    assert parts["big"]["groups"][0]["gpus"] == [{"type": "L40", "count": 2}]  # shard is not a GPU


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("7-00:00:00", 10080),
        ("1-12", 2160),
        ("1-12:30", 2190),
        ("2:00:00", 120),
        ("30:00", 30),
        ("30:01", 31),  # a started minute counts
        ("45", 45),
        ("infinite", None),
        ("UNLIMITED", None),
        ("1:2:3:4", None),
        ("x-1", None),
    ],
)
def test_time_limit_in_minutes(text: str, minutes: int | None) -> None:
    assert cluster._minutes(text) == minutes


@pytest.mark.parametrize(
    ("text", "gpus"),
    [
        ("gpu:H100:4(S:0-1)", [{"type": "H100", "count": 4}]),
        ("gpu:4", [{"type": None, "count": 4}]),
        ("gpu:a100_80g:no_consume:2", [{"type": "a100_80g", "count": 2}]),
        (
            "gpu:H100:2(S:0,1),gpu:L40:1",
            [{"type": "H100", "count": 2}, {"type": "L40", "count": 1}],
        ),
        ("(null)", []),
        ("shard:8,gpu", []),
    ],
)
def test_gres_to_gpus(text: str, gpus: list[dict[str, Any]]) -> None:
    assert parse_gres(text) == gpus


def test_assemble_allows_by_accounts_and_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cluster, "_my_groups", lambda: {"staff"})
    at = datetime(2026, 11, 26, 10, 0, tzinfo=UTC)
    body = assemble(SINFO, SCONTROL, ASSOC, at)
    assert body["scheduler"] == "slurm" and body["fetched_at"] == "2026-11-26T10:00:00Z"
    assert body["accounts"] == ["lab-a", "lab-b"]
    found = by_name(body)
    assert found["cpu"]["default"] is True and found["cpu"]["allowed"] is True
    assert found["gpu"]["allowed"] is True  # lab-a is allowed there
    assert found["test"]["allowed"] is False  # AllowGroups names a group the user is not in
    assert found["big"]["allowed"] is True


def test_assemble_a_partition_the_accounts_do_not_reach(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cluster, "_my_groups", lambda: set())
    only_b = assemble(SINFO, SCONTROL, "lab-b|cpu\n")  # lab-b is limited to cpu, gpu wants lab-a
    found = by_name(only_b)
    assert found["cpu"]["allowed"] is True
    assert found["gpu"]["allowed"] is False and found["big"]["allowed"] is False


def test_assemble_unknown_parts_are_empty_and_allowed() -> None:
    body = assemble(SINFO, None, None)  # scontrol and sacctmgr failed
    assert body["accounts"] == []
    assert body["partitions"][0]["default"] is True  # from sinfo's `*`
    assert all(p["allowed"] for p in body["partitions"])


def stubbed(client: TestClient, answers: dict[str, str | None]) -> list[tuple[str, list[str]]]:
    calls: list[tuple[str, list[str]]] = []

    def run(name: str, args: list[str]) -> str | None:
        calls.append((name, args))
        return answers.get(name)

    client.app.state.cluster.run = run  # type: ignore[attr-defined]
    return calls


def test_route_serves_the_facts_and_caches_them(authed_client: TestClient) -> None:
    calls = stubbed(authed_client, {"sinfo": SINFO, "scontrol": SCONTROL, "sacctmgr": ASSOC})
    answer = authed_client.get(FACTS)
    assert answer.status_code == 200
    body = answer.json()
    assert body["scheduler"] == "slurm" and body["accounts"] == ["lab-a", "lab-b"]
    assert {"name", "default", "allowed", "max_time_min", "groups"} == set(body["partitions"][0])
    assert set(body["partitions"][1]["groups"][0]) == {
        "nodes", "idle", "cpus", "mem_mib", "features", "gpus",
    }  # fmt: skip
    assert [c[0] for c in calls] == ["sinfo", "scontrol", "sacctmgr"]
    sinfo_args = calls[0][1]
    assert sinfo_args == ["--noheader", "-o", "%P|%l|%D|%c|%m|%f|%G|%T"]
    assert calls[2][1][-2:] == [
        f"user={pwd.getpwuid(os.geteuid()).pw_name}",
        "format=account,partition",
    ]
    assert authed_client.get(FACTS).json() == body
    assert len(calls) == 3  # the second answer came from the cache


def test_cache_expires_after_its_ttl(settings: Settings) -> None:
    now = [1000.0]
    facts = Facts(settings, clock=lambda: now[0])
    calls: list[str] = []

    def run(name: str, args: list[str]) -> str | None:
        calls.append(name)
        return SINFO if name == "sinfo" else None

    facts.run = run
    facts.get()
    now[0] += cluster.TTL_S - 1
    facts.get()
    assert calls.count("sinfo") == 1
    now[0] += 2
    facts.get()
    assert calls.count("sinfo") == 2


def test_no_scheduler_is_null_and_asked_again_sooner(settings: Settings) -> None:
    now = [0.0]
    facts = Facts(settings, clock=lambda: now[0])
    answers: dict[str, str | None] = {}
    facts.run = lambda name, args: answers.get(name)
    assert facts.get() == {"scheduler": None, "fetched_at": None, "partitions": [], "accounts": []}
    answers["sinfo"] = SINFO  # SLURM came back
    now[0] += cluster.FAILED_TTL_S + 1
    assert facts.get()["scheduler"] == "slurm"


def test_route_without_slurm_is_200_null(authed_client: TestClient) -> None:
    stubbed(authed_client, {})
    answer = authed_client.get(FACTS)
    assert answer.status_code == 200
    assert answer.json() == {
        "scheduler": None,
        "fetched_at": None,
        "partitions": [],
        "accounts": [],
    }


def test_route_with_failing_parts_still_lists_partitions(authed_client: TestClient) -> None:
    stubbed(authed_client, {"sinfo": SINFO})  # scontrol and sacctmgr failed
    body = authed_client.get(FACTS).json()
    assert body["accounts"] == [] and len(body["partitions"]) == 4
    assert all(p["allowed"] for p in body["partitions"])


def test_route_needs_the_session(settings: Settings, writer) -> None:  # type: ignore[no-untyped-def]
    from .conftest import client_for

    assert client_for(settings, writer, signed_in=False).get(FACTS).status_code == 401


def test_run_tool_without_the_command(settings: Settings, tmp_path: Path) -> None:
    """A missing, a group-writable and a failing tool each give None, never an exception."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    slurm = SlurmOpts(sacct=bin_dir / "sacct")
    mine = settings.model_copy(update={"slurm": slurm})
    assert cluster.run_tool(mine, "sinfo", []) is None  # not there
    tool = bin_dir / "sinfo"
    tool.write_text("#!/bin/sh\necho 'cpu*|1:00:00|1|1|1|(null)|(null)|idle'\n")
    tool.chmod(0o770)
    assert cluster.run_tool(mine, "sinfo", []) is None  # others may write it: refused
    tool.chmod(0o755)
    assert cluster.run_tool(mine, "sinfo", []) == "cpu*|1:00:00|1|1|1|(null)|(null)|idle\n"
    tool.write_text("#!/bin/sh\nexit 1\n")
    assert cluster.run_tool(mine, "sinfo", []) is None
