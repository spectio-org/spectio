"""The pipeline catalog routes and inspect's `params_file` (FU-P3-87b; api §5.6; dev-env §15.3
req. 18): the five routes, their refusals and their absence where the API is not served, the
session, cross-site and `Origin` checks of req. 2 and 7 per route, no `git` on a `POST` or on a
bad `params_file`, and every way the params file can fail to read (SEC-PRE-FU87-01 to -04)."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from spectio import envfile
from spectio.config import Settings, SlurmOpts
from spectio.runner.types import Stalled
from spectio_server.api import workflows as wf
from spectio_server.store.writer import Writer

from .conftest import client_for
from .test_environments import problem
from .test_launch import INSPECT, FakeGit

API = "/api/v1"
CAT = f"{API}/catalog"
RNASEQ = {
    "name": "rnaseq",
    "label": "RNA-seq",
    "engine": "nextflow",
    "location": "nf-core/rnaseq",
    "revision": "3.14.0",
    "profile": "test",
    "params_file": "conf/test.yaml",
}
ITEM_KEYS = {"name", "label", "engine", "location", "revision", "profile", "params_file", "etag"}


def path() -> Path:
    return Path(os.environ["SPECTIO_CONFIG"]).parent / "catalog.toml"


def hand_write(text: str, mode: int = 0o600) -> None:
    path().write_text(text)
    path().chmod(mode)


def create(client: TestClient, body: dict[str, Any] = RNASEQ) -> Any:
    found = client.post(CAT, json=body)
    assert found.status_code == 201, found.text
    return found


@pytest.fixture
def fake_git(monkeypatch: pytest.MonkeyPatch) -> FakeGit:
    """`git` recorded, never run: a clone makes a Nextflow pipeline."""
    fake = FakeGit()
    monkeypatch.setattr(wf, "run_git", fake)
    return fake


# --- The routes ------------------------------------------------------------------------------


def test_req18_catalog_list_missing(authed_client: TestClient) -> None:
    found = authed_client.get(CAT)
    assert found.status_code == 200, found.text
    assert found.json() == {
        "items": [],
        "file": {"path": str(path()), "state": "missing", "detail": None},
    }


def test_req18_catalog_create_get_put_delete(authed_client: TestClient, fake_git: FakeGit) -> None:
    made = create(authed_client)
    assert fake_git.calls == []  # Save contacts no remote (inbox #147 choice 4)
    assert made.headers["location"] == f"{CAT}/rnaseq"
    item = made.json()
    assert set(item) == ITEM_KEYS and made.headers["etag"] == item["etag"]
    assert {k: item[k] for k in RNASEQ} == RNASEQ
    local = {"name": "mine", "engine": "snakemake", "location": "/srv/mine"}
    create(authed_client, local)
    body = authed_client.get(CAT).json()
    assert [i["name"] for i in body["items"]] == ["mine", "rnaseq"]
    assert body["file"]["state"] == "ok" and body["items"][0]["revision"] is None
    got = authed_client.get(f"{CAT}/rnaseq")
    assert got.status_code == 200 and got.headers["etag"] == item["etag"]
    assert (path().stat().st_mode & 0o777) == 0o600

    changed = {**RNASEQ, "revision": "3.15.0"}
    problem(authed_client.put(f"{CAT}/rnaseq", json=changed), 428, "if-match-required")
    star = {"If-Match": "*"}
    problem(
        authed_client.put(f"{CAT}/rnaseq", json=changed, headers=star), 428, "if-match-required"
    )
    stale = {"If-Match": '"0000"'}
    problem(authed_client.put(f"{CAT}/rnaseq", json=changed, headers=stale), 412, "etag-mismatch")
    put = authed_client.put(f"{CAT}/rnaseq", json=changed, headers={"If-Match": item["etag"]})
    assert put.status_code == 200, put.text
    assert put.json()["revision"] == "3.15.0" and put.headers["etag"] != item["etag"]
    tag = {"If-Match": put.headers["etag"]}
    renamed = {**changed, "name": "other"}
    problem(
        authed_client.put(f"{CAT}/rnaseq", json=renamed, headers=tag),
        422,
        "validation-failed",
        "name",
    )
    problem(
        authed_client.put(f"{CAT}/gone", json={**changed, "name": "gone"}, headers=tag),
        404,
        "not-found",
    )

    problem(authed_client.delete(f"{CAT}/rnaseq"), 428, "if-match-required")
    problem(authed_client.delete(f"{CAT}/rnaseq", headers=star), 428, "if-match-required")
    old = {"If-Match": item["etag"]}
    problem(authed_client.delete(f"{CAT}/rnaseq", headers=old), 412, "etag-mismatch")
    assert authed_client.delete(f"{CAT}/rnaseq", headers=tag).status_code == 204
    problem(authed_client.get(f"{CAT}/rnaseq"), 404, "not-found")
    problem(authed_client.delete(f"{CAT}/rnaseq", headers=tag), 404, "not-found")
    assert [i["name"] for i in authed_client.get(CAT).json()["items"]] == ["mine"]
    assert fake_git.calls == []


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**RNASEQ, "name": "new"}, "name"),
        ({**RNASEQ, "name": "../x"}, "name"),
        ({**RNASEQ, "name": "a" * 33}, "name"),
        ({**RNASEQ, "label": "a‮b"}, "label"),
        ({**RNASEQ, "engine": "cwl"}, "engine"),
        ({**RNASEQ, "location": "relative/dir/x"}, "location"),
        ({**RNASEQ, "location": "git://example.org/x"}, "location"),
        ({**RNASEQ, "location": "https://u:p@example.org/x"}, "location"),
        ({**RNASEQ, "location": "/srv/x\n"}, "location"),
        ({**RNASEQ, "location": "/" + "a" * 4096}, "location"),
        ({**RNASEQ, "revision": None}, "revision"),  # a Git location without a revision
        ({**RNASEQ, "revision": "-x"}, "revision"),
        ({**RNASEQ, "location": "/srv/x"}, "revision"),  # a path with a revision
        ({**RNASEQ, "profile": "../x"}, "profile"),
        ({**RNASEQ, "params_file": "../x.yaml"}, "params_file"),
        ({**RNASEQ, "params_file": "/etc/x.yaml"}, "params_file"),
        ({**RNASEQ, "params_file": "/".join(["a"] * 9) + ".json"}, "params_file"),
        ({**RNASEQ, "params_file": "conf/test.txt"}, "params_file"),
        ({**RNASEQ, "etag": '"x"'}, "etag"),
        ({k: v for k, v in RNASEQ.items() if k != "engine"}, "engine"),
    ],
)
def test_req18_catalog_refusals(
    authed_client: TestClient, fake_git: FakeGit, body: dict[str, Any], field: str
) -> None:
    found = authed_client.post(CAT, json=body)
    problem(found, 422, "validation-failed", field)
    assert "u:p" not in found.text
    assert not path().exists() and fake_git.calls == []


def test_req18_catalog_conflicts(authed_client: TestClient) -> None:
    create(authed_client)
    problem(authed_client.post(CAT, json=RNASEQ), 409, "catalog-entry-exists")


@pytest.mark.parametrize(
    ("text", "mode", "state"),
    [
        (
            '[pipelines.x]\nengine = "nextflow"\nlocation = "/srv/x"\nrevision = "v1"\n',
            0o600,
            "invalid",
        ),
        ('[pipelines.x]\nengine = "nextflow"\nlocation = "/srv/x"\n', 0o620, "refused"),
    ],
)
def test_req18_catalog_file_unusable(
    authed_client: TestClient, text: str, mode: int, state: str
) -> None:
    """An empty list with the state and its detail; never overwritten."""
    hand_write(text, mode)
    body = authed_client.get(CAT).json()
    assert body["items"] == [] and body["file"]["state"] == state and body["file"]["detail"]
    problem(authed_client.get(f"{CAT}/x"), 404, "not-found")
    problem(authed_client.post(CAT, json=RNASEQ), 409, "catalog-file-unusable")
    assert path().read_text() == text


def test_req18_catalog_unreachable(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def stalled(*args: Any, **kwargs: Any) -> Any:
        raise Stalled("the file system did not answer within 5 s")

    monkeypatch.setattr(envfile, "read_kind", stalled)
    monkeypatch.setattr(envfile, "update_kind", stalled)
    assert authed_client.get(CAT).json()["file"]["state"] == "unreachable"
    problem(authed_client.get(f"{CAT}/rnaseq"), 503, "runner-offline")
    problem(authed_client.post(CAT, json=RNASEQ), 503, "runner-offline")


def test_req18_catalog_file_changed(
    authed_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    create(authed_client)
    render = envfile.render

    def edited(*args: Any) -> bytes:
        hand_write(path().read_text().replace("3.14.0", "3.14.1"))
        return render(*args)

    monkeypatch.setattr(envfile, "render", edited)
    problem(authed_client.post(CAT, json={**RNASEQ, "name": "two"}), 409, "catalog-file-changed")
    assert "3.14.1" in path().read_text() and "two" not in path().read_text()


def test_req18_catalog_absent_on_tcp_slurm(settings: Settings, writer: Writer) -> None:
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    client = client_for(slurm, writer)
    assert client.app.state.no_api is not None  # type: ignore[attr-defined]
    tag = {"If-Match": '"x"'}
    for response in (
        client.get(CAT),
        client.get(f"{CAT}/rnaseq"),
        client.post(CAT, json=RNASEQ),
        client.put(f"{CAT}/rnaseq", json=RNASEQ, headers=tag),
        client.delete(f"{CAT}/rnaseq", headers=tag),
    ):
        problem(response, 404, "not-found")
        assert "Unix socket" in response.json()["detail"]
    assert not path().exists()


def calls(tag: str) -> list[tuple[str, str, dict[str, Any]]]:
    put = {"json": {**RNASEQ, "label": "New"}, "headers": {"If-Match": tag}}
    return [
        ("GET", CAT, {}),
        ("GET", f"{CAT}/rnaseq", {}),
        ("POST", CAT, {"json": {**RNASEQ, "name": "other"}}),
        ("PUT", f"{CAT}/rnaseq", put),
        ("DELETE", f"{CAT}/rnaseq", {"headers": {"If-Match": tag}}),
    ]


def test_req18_catalog_session_cross_site_origin(authed_client: TestClient) -> None:
    """Req. 2 and 7 per route: no session is `401`; another site is `403`, a `GET` too; a write
    without an `Origin` is `403`. Nothing is written."""
    create(authed_client)
    before = path().read_bytes()
    tag = authed_client.get(f"{CAT}/rnaseq").headers["etag"]
    cookies = dict(authed_client.cookies)
    authed_client.cookies.clear()
    for method, url, kw in calls(tag):
        assert authed_client.request(method, url, **kw).status_code == 401, (method, url)
    authed_client.cookies.update(cookies)
    for foreign in (
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Referer": "http://evil.example/page"},
        {"Origin": "http://evil.example"},
    ):
        for method, url, kw in calls(tag):
            headers = {**kw.get("headers", {}), **foreign}
            problem(
                authed_client.request(method, url, **{**kw, "headers": headers}), 403, "cross-site"
            )
    origin = authed_client.headers.pop("origin")
    for method, url, kw in calls(tag)[2:]:
        assert authed_client.request(method, url, **kw).status_code == 403, (method, url)
    authed_client.headers["origin"] = origin
    assert path().read_bytes() == before


def test_req18_catalog_write_logged(
    authed_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO", logger="spectio_server.api.catalog"):
        create(authed_client)
    (record,) = [r for r in caplog.records if r.name == "spectio_server.api.catalog"]
    message = record.getMessage()
    assert message.startswith("catalog POST /catalog rnaseq: None -> ")
    assert "'revision': '3.14.0'" in message


# --- Inspect's params_file -------------------------------------------------------------------


@pytest.fixture
def pipeline(tmp_path: Path, synthetic: Path) -> Path:
    """A copy of the synthetic Nextflow pipeline, private, with a `conf/` to put files in."""
    root = tmp_path / "pipe"
    shutil.copytree(synthetic / "nextflow", root)
    for p in (root, root / "conf"):
        p.chmod(0o755)
    return root


def inspect(client: TestClient, root: Path | str, params_file: str, **query: str) -> Any:
    return client.get(INSPECT, params={"location": str(root), "params_file": params_file, **query})


def params_of(client: TestClient, root: Path, name: str = "conf/p.json") -> dict[str, Any]:
    found = inspect(client, root, name)
    assert found.status_code == 200, found.text
    body: dict[str, Any] = found.json()["params_file"]
    assert body["path"] == name
    return body


def test_req18_catalog_params_not_asked(authed_client: TestClient, pipeline: Path) -> None:
    found = authed_client.get(INSPECT, params={"location": str(pipeline)})
    assert found.status_code == 200 and found.json()["params_file"] is None


def test_req18_catalog_params_read(authed_client: TestClient, pipeline: Path) -> None:
    (pipeline / "conf" / "p.json").write_text(json.dumps({"input": "a.csv", "n": [1, {"b": 2}]}))
    body = params_of(authed_client, pipeline)
    assert body["values"] == {"input": "a.csv", "n": [1, {"b": 2}]} and body["error"] is None
    (pipeline / "conf" / "p.yml").write_text("input: b.csv\nwhen: 2026-11-10\n")
    body = params_of(authed_client, pipeline, "conf/p.yml")
    assert body["values"] == {"input": "b.csv", "when": "2026-11-10"}


@pytest.mark.parametrize(
    "value",
    ["../x.json", "/etc/x.json", "/".join(["a"] * 9) + ".json", "conf/p.txt", "conf//p.json", ""],
)
def test_req18_catalog_params_bad_before_resolve(
    authed_client: TestClient, fake_git: FakeGit, value: str
) -> None:
    """SEC-PRE-FU87-04: `422` on `params_file` before anything is fetched: no `git` runs."""
    found = inspect(authed_client, "nf-core/rnaseq", value, revision="3.14.0")
    problem(found, 422, "validation-failed", "params_file")
    assert fake_git.calls == []


def _deep(n: int) -> str:
    return json.dumps({"a": json.loads("[" * (n - 1) + "]" * (n - 1))})


@pytest.mark.parametrize(
    ("name", "make", "says"),
    [
        ("conf/gone.json", None, "no such file"),
        ("conf/list.json", lambda p: p.write_text("[1, 2]"), "not a map"),
        ("conf/big.json", lambda p: p.write_text(" " * (256 * 1024) + "{}"), "larger than"),
        ("conf/bytes.json", lambda p: p.write_bytes(b'{"a": "\xff"}'), "UTF-8"),
        ("conf/bad.json", lambda p: p.write_text("{nope"), "not JSON"),
        ("conf/bad.yaml", lambda p: p.write_text("a: [\n"), "not YAML"),
        ("conf/alias.yaml", lambda p: p.write_text("a: &x 1\nb: *x\n"), "alias"),
        ("conf/deep.json", lambda p: p.write_text(_deep(33)), "deeper than 32"),
        ("conf/nested.json", lambda p: p.write_text("[" * 10000), "too deep"),
        ("conf/nested.yaml", lambda p: p.write_text("[" * 10000), "not YAML"),
        ("conf/nan.json", lambda p: p.write_text('{"a": NaN}'), "not JSON"),
        ("conf/huge.json", lambda p: p.write_text('{"a": 1e999}'), "not JSON"),
        ("conf/inf.yaml", lambda p: p.write_text("a: .inf\n"), "not YAML"),
        ("conf/nan.yaml", lambda p: p.write_text("a: [.nan]\n"), "not YAML"),
        ("conf/date.yaml", lambda p: p.write_text("2026-01-01: x\n"), "not YAML"),
        ("conf/datekey.yaml", lambda p: p.write_text("? 2020-01-01\n: x\n"), "not YAML"),
        ("conf/deepdate.yaml", lambda p: p.write_text("a:\n  2020-01-01: x\n"), "not YAML"),
        ("conf/dir.json", lambda p: p.mkdir(), "not a regular file"),
        ("conf/fifo.json", lambda p: os.mkfifo(p), "not a regular file"),
        ("conf/link.json", lambda p: p.symlink_to(p.parent / "real.json"), "symbolic link"),
    ],
)
def test_req18_catalog_params_read_failures(
    authed_client: TestClient, pipeline: Path, name: str, make: Any, says: str
) -> None:
    """SEC-PRE-FU87-03: each failure is `values: null` and an `error` in words, never a `422` or
    a `500`; the pipeline still loads, and the error quotes none of the file's bytes."""
    (pipeline / "conf" / "real.json").write_text('{"secret": "s3cr3t"}')
    if make is not None:
        make(pipeline / name)
    found = inspect(authed_client, pipeline, name)
    assert found.status_code == 200, found.text
    body = found.json()
    assert body["engine"] == "nextflow"
    params = body["params_file"]
    assert params["values"] is None and says in params["error"], params
    assert len(params["error"]) <= 200 and "s3cr3t" not in params["error"]
    assert "nope" not in params["error"] and "\\xff" not in params["error"]


def test_req18_catalog_params_deep_32_read(authed_client: TestClient, pipeline: Path) -> None:
    (pipeline / "conf" / "p.json").write_text(_deep(32))
    assert params_of(authed_client, pipeline)["values"] is not None


def test_req18_catalog_params_hidden_key_listed(authed_client: TestClient, pipeline: Path) -> None:
    """SEC-PRE-FU87-01: a hidden field's key and a key with no field come back in `values`."""
    schema = json.loads((pipeline / "nextflow_schema.json").read_text())
    schema.setdefault("properties", {})["secret_opt"] = {"type": "string", "hidden": True}
    (pipeline / "nextflow_schema.json").write_text(json.dumps(schema))
    values = {"secret_opt": "x", "no_such_field": 1}
    (pipeline / "conf" / "p.json").write_text(json.dumps(values))
    assert params_of(authed_client, pipeline)["values"] == values


def test_req18_catalog_params_code_loading_flagged(
    authed_client: TestClient, pipeline: Path
) -> None:
    """`custom_config_base` in the file, and a group-writable params file of a local pipeline,
    appear in `code_loading` with `writable_by_others`."""
    file = pipeline / "conf" / "p.yaml"
    file.write_text("custom_config_base: https://example.org/configs\n")
    file.chmod(0o664)
    loading = params_of(authed_client, pipeline, "conf/p.yaml")["code_loading"]
    by_field = {e["field"]: e for e in loading}
    assert by_field["params.custom_config_base"]["value"] == "https://example.org/configs"
    assert by_field["params_file"] == {
        "field": "params_file",
        "value": str(file),
        "writable_by_others": True,
    }
    assert by_field["workflow.location"]["writable_by_others"] is False
    file.chmod(0o644)
    loading = params_of(authed_client, pipeline, "conf/p.yaml")["code_loading"]
    assert {e["field"]: e for e in loading}["params_file"]["writable_by_others"] is False


def test_req18_catalog_params_git_pipeline(authed_client: TestClient, fake_git: FakeGit) -> None:
    """A Git pipeline: no `params_file` entry in `code_loading` (the cache is Spectio's), the
    file's values still flagged; a missing file still loads the pipeline."""
    found = inspect(authed_client, "nf-core/rnaseq", "conf/test.json", revision="3.14.0")
    assert found.status_code == 200, found.text
    params = found.json()["params_file"]
    assert params["values"] is None and params["code_loading"] == []
