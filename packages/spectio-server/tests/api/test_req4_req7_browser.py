"""dev-env §15.3 req. 4 (Host allow-list) and req. 7 (writes: Origin and JSON), and the
cross-site refusal that stands in for the `SameSite=Strict` session (req. 3) until P1 Tasks 12
to 16 (CR-P3T17-01, SEC-P3T17-01, SEC-P3T17-02; inbox #37, #86)."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio.config import Settings
from spectio_server.api import workflows as wf
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

from .conftest import client_for

INSPECT = "/api/v1/workflows:inspect"
RUNS = "/api/v1/runs"
GIT = {"location": "https://github.com/lab/pipeline", "revision": "v1"}


@pytest.fixture
def git_calls(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    calls: list[list[str]] = []

    def record(argv: list[str]) -> Any:
        calls.append(argv)
        raise AssertionError("git must not run")

    monkeypatch.setattr(wf, "run_git", record)
    return calls


def body(synthetic: Path) -> dict[str, Any]:
    return {"workflow": {"location": str(synthetic / "nextflow"), "engine": "nextflow"}}


def no_rows(writer: Writer, settings: Settings) -> bool:
    found = writer.submit(lambda c: list(c.execute(select(runs)).all())).result()
    return found == [] and list(settings.runs_root.iterdir()) == []


@pytest.mark.parametrize("host", ["evil.example", "127.0.0.1.evil.example", "10.0.0.1:8080", ""])
def test_req4_other_host_refused(
    settings: Settings,
    writer: Writer,
    synthetic: Path,
    git_calls: list[list[str]],
    host: str,
) -> None:
    client = client_for(settings, writer)
    headers = {"Host": host, "Origin": f"http://{host}"}
    assert client.get(INSPECT, params=GIT, headers=headers).status_code == 400
    assert client.post(RUNS, json=body(synthetic), headers=headers).status_code == 400
    assert client.get("/", headers={"Host": host}).status_code == 400
    assert git_calls == [] and no_rows(writer, settings)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost:9999", "[::1]:8080", "LOCALHOST"])
def test_req4_loopback_hosts_any_port(settings: Settings, writer: Writer, host: str) -> None:
    client = client_for(settings, writer)
    headers = {"Host": host, "Origin": f"http://{host}"}  # a tunnel's local port (req. 4)
    assert client.get("/", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "origin", [None, "http://evil.example", "http://127.0.0.1:1", "null", "https://127.0.0.1"]
)
def test_req7_write_needs_same_origin(
    settings: Settings, writer: Writer, synthetic: Path, origin: str | None
) -> None:
    client = client_for(settings, writer)
    client.headers.pop("Origin")
    headers = {} if origin is None else {"Origin": origin}
    assert client.post(RUNS, json=body(synthetic), headers=headers).status_code == 403
    assert no_rows(writer, settings)


@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded", None])
def test_req7_write_body_must_be_json(
    authed_client: TestClient,
    settings: Settings,
    writer: Writer,
    synthetic: Path,
    content_type: str | None,
) -> None:
    headers = {} if content_type is None else {"Content-Type": content_type}
    response = authed_client.post(RUNS, content=json.dumps(body(synthetic)), headers=headers)
    assert response.status_code == 415, response.text
    assert no_rows(writer, settings)


def test_req7_json_with_charset_accepted(authed_client: TestClient, synthetic: Path) -> None:
    response = authed_client.post(
        RUNS,
        content=json.dumps(body(synthetic)),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "headers",
    [
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Origin": "http://evil.example"},
        {"Referer": "http://evil.example/page"},
    ],
)
def test_cross_site_get_never_fetches(
    authed_client: TestClient, git_calls: list[list[str]], headers: dict[str, str]
) -> None:
    """An `<img src>` on another site would otherwise start a clone (SEC-P3T17-02)."""
    assert authed_client.get(INSPECT, params=GIT, headers=headers).status_code == 403
    assert git_calls == []


@pytest.mark.parametrize("site", ["same-origin", "none"])
def test_same_origin_get_allowed(authed_client: TestClient, synthetic: Path, site: str) -> None:
    params = {"location": str(synthetic / "nextflow")}
    referer = str(authed_client.base_url) + "/"
    headers = {"Sec-Fetch-Site": site, "Referer": referer}
    assert authed_client.get(INSPECT, params=params, headers=headers).status_code == 200
