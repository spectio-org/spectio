"""Computes, execution profiles and their launch (#408; api §5.13): the routes, their refusals
and their absence where the API is not served, the session, cross-site and `Origin` checks of
req. 2 and 7, the 409s that keep a compute or a profile in use, the migration of
`environments.toml` on the first read, a catalog entry's profiles and how a launch turns a
profile and its compute into the run's snapshot."""

import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from spectio.config import Settings, SlurmOpts
from spectio_server.store.schema import runner_commands
from spectio_server.store.writer import Writer

from .conftest import client_for
from .test_execution_profiles import (
    API,
    COMPUTES,
    MYLAB,
    PROFILES,
    as_slurm,
    column,
    create,
    launch,
    launched,
    problem,
)

PROFILE = {"name": "mylab", "label": "My lab", "compute": "mylab"}
LAB = {**PROFILE, "software": ["conda"]}  # for a compute that has only conda


def conf(name: str) -> Path:
    return Path(os.environ["SPECTIO_CONFIG"]).parent / name


def hand_write(name: str, text: str, mode: int = 0o600) -> None:
    conf(name).write_text(text)
    conf(name).chmod(mode)


# --- The lists and the built-ins -------------------------------------------------------------


def test_lists_have_the_builtins(authed_client: TestClient, settings: Settings) -> None:
    found = authed_client.get(COMPUTES).json()
    assert found["file"] == {"path": str(conf("computes.toml")), "state": "missing", "detail": None}
    (local,) = found["items"]
    assert (local["name"], local["builtin"], local["usable"]) == ("local", True, True)
    assert (local["label"], local["local"], local["software"]) == (
        "This machine",
        None,
        ["conda", "apptainer"],
    )
    found = authed_client.get(PROFILES).json()
    assert found["default"] == "local"
    (profile,) = found["items"]
    assert (profile["name"], profile["compute"], profile["builtin"], profile["default"]) == (
        "local",
        "local",
        True,
        True,
    )
    assert set(profile["resources"]) == {
        "partition",
        "constraint",
        "gres",
        "time_min",
        "mem_mib",
        "cpus",
    }
    assert set(profile["resources"].values()) == {None}
    as_slurm(authed_client, settings)
    items = authed_client.get(COMPUTES).json()["items"]
    assert [i["name"] for i in items] == ["slurm", "local"]
    assert items[1]["local"] == {"cpus": 2, "mem_mib": 8192}
    slurm = authed_client.get(f"{PROFILES}/slurm").json()
    assert slurm["resources"]["partition"] == "htc" and slurm["default"]


def test_compute_crud(authed_client: TestClient) -> None:
    made = authed_client.post(COMPUTES, json={**MYLAB, "apptainer_args": "--bind /g"})
    assert made.status_code == 201, made.text
    assert made.headers["location"] == f"{COMPUTES}/mylab" and made.headers["etag"]
    item = made.json()
    assert item["local"] == {"cpus": 4, "mem_mib": None} and not item["builtin"]
    got = authed_client.get(f"{COMPUTES}/mylab")
    assert got.headers["etag"] == item["etag"]
    assert [i["name"] for i in authed_client.get(COMPUTES).json()["items"]] == ["local", "mylab"]
    problem(authed_client.put(f"{COMPUTES}/mylab", json=MYLAB), 428, "if-match-required")
    stale = {"If-Match": '"stale"'}
    problem(authed_client.put(f"{COMPUTES}/mylab", json=MYLAB, headers=stale), 412, "etag-mismatch")
    tag = {"If-Match": item["etag"]}
    new = {**MYLAB, "label": "Renamed"}
    put = authed_client.put(f"{COMPUTES}/mylab", json=new, headers=tag)
    assert put.status_code == 200 and put.json()["label"] == "Renamed"
    problem(
        authed_client.put(f"{COMPUTES}/mylab", json={**new, "name": "x"}, headers=tag),
        422,
        "validation-failed",
        "name",
    )
    tag = {"If-Match": put.headers["etag"]}
    assert authed_client.delete(f"{COMPUTES}/mylab", headers=tag).status_code == 204
    problem(authed_client.get(f"{COMPUTES}/mylab"), 404, "not-found")


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**MYLAB, "name": "local"}, "name"),
        ({**MYLAB, "name": "new"}, "name"),
        ({**MYLAB, "name": "../spectio"}, "name"),
        ({"name": "x", "executor": "slurm"}, "executor"),  # a local server
        ({**MYLAB, "builtin": False}, "builtin"),
        ({**MYLAB, "usable": True}, "usable"),
        ({**MYLAB, "local": {"cpus": True}}, "local.cpus"),
        ({**MYLAB, "local": {"cpus": 0}}, "local.cpus"),
        ({**MYLAB, "slurm": {"account": "lab"}}, "body"),  # slurm values on a local one
        ({**MYLAB, "software": ["npm"]}, "software.0"),
        ({**MYLAB, "software": ["conda", "conda"]}, "software"),
        ({**MYLAB, "apptainer_args": "--bind\rtouch x"}, "apptainer_args"),
    ],
)
def test_compute_refusals(authed_client: TestClient, body: dict[str, Any], field: str) -> None:
    problem(authed_client.post(COMPUTES, json=body), 422, "validation-failed", field)
    assert not conf("computes.toml").exists()


def test_slurm_compute_account_is_strict(authed_client: TestClient, settings: Settings) -> None:
    as_slurm(authed_client, settings)
    good = {"name": "hpc", "executor": "slurm", "slurm": {"account": "lab-a"}}
    problem(
        authed_client.post(COMPUTES, json={**good, "slurm": {"account": "$HOME"}}),
        422,
        "validation-failed",
    )
    made = authed_client.post(COMPUTES, json=good)
    assert made.status_code == 201 and made.json()["slurm"] == {"account": "lab-a"}


# --- Execution profiles ----------------------------------------------------------------------


def test_profile_crud(authed_client: TestClient) -> None:
    authed_client.post(COMPUTES, json=MYLAB)
    body = {**PROFILE, "resources": {"cpus": 2, "mem_mib": 1024}, "software": ["conda"]}
    made = authed_client.post(PROFILES, json=body)
    assert made.status_code == 201, made.text
    item = made.json()
    assert made.headers["location"] == f"{PROFILES}/mylab" and made.headers["etag"] == item["etag"]
    assert item["resources"]["cpus"] == 2 and item["software"] == ["conda"]
    assert item["engine_profiles"] == {"nextflow": None, "snakemake": None}
    problem(authed_client.post(PROFILES, json=body), 409, "execution-profile-exists")
    tag = {"If-Match": item["etag"]}
    put = authed_client.put(f"{PROFILES}/mylab", json={**body, "label": "New"}, headers=tag)
    assert put.status_code == 200 and put.json()["label"] == "New"
    assert authed_client.get(f"{PROFILES}/mylab").json()["etag"] == put.headers["etag"]
    problem(authed_client.delete(f"{PROFILES}/mylab"), 428, "if-match-required")
    tag = {"If-Match": put.headers["etag"]}
    assert authed_client.delete(f"{PROFILES}/mylab", headers=tag).status_code == 204
    problem(authed_client.get(f"{PROFILES}/mylab"), 404, "not-found")


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({**LAB, "name": "local"}, "name"),
        ({**LAB, "compute": "gone"}, "compute"),
        ({**LAB, "compute": "../x"}, "compute"),
        ({**PROFILE}, "software"),  # mylab only has conda below
        ({**LAB, "resources": {"partition": "htc"}}, "resources.partition"),  # local compute
        ({**LAB, "resources": {"time_min": 60}}, "resources.time_min"),
        ({**LAB, "resources": {"cpus": 5}}, "resources.cpus"),  # the compute's cap is 4
        ({**LAB, "resources": {"mem_mib": True}}, "resources.mem_mib"),
        ({**LAB, "resources": {"cpus": 0}}, "resources.cpus"),
        ({**LAB, "resources": {"gres": "gpu 1"}}, "resources.gres"),
        ({**LAB, "engine_profiles": {"nextflow": "../x"}}, "engine_profiles.nextflow"),
        ({**LAB, "builtin": False}, "builtin"),
    ],
)
def test_profile_refusals(authed_client: TestClient, body: dict[str, Any], field: str) -> None:
    authed_client.post(COMPUTES, json={**MYLAB, "software": ["conda"]})
    problem(authed_client.post(PROFILES, json=body), 422, "validation-failed", field)
    assert not conf("execution-profiles.toml").exists()


def test_slurm_profile_on_a_slurm_compute(authed_client: TestClient, settings: Settings) -> None:
    as_slurm(authed_client, settings)
    authed_client.post(COMPUTES, json={"name": "hpc", "executor": "slurm"})
    body = {
        "name": "gpu",
        "compute": "hpc",
        "resources": {"partition": "gpu", "constraint": "avx512", "gres": "gpu:H100:1"},
    }
    made = authed_client.post(PROFILES, json=body)
    assert made.status_code == 201 and made.json()["resources"]["gres"] == "gpu:H100:1"


def test_builtins_and_uses_are_409(authed_client: TestClient) -> None:
    create(authed_client)
    tag = {"If-Match": '"x"'}
    for kind, body, slug in (
        (COMPUTES, MYLAB, "compute"),
        (PROFILES, PROFILE, "execution-profile"),
    ):
        for name in ("local", "slurm"):
            put = authed_client.put(f"{kind}/{name}", json={**body, "name": name}, headers=tag)
            problem(put, 409, f"{slug}-builtin")
            problem(authed_client.delete(f"{kind}/{name}", headers=tag), 409, f"{slug}-builtin")
    # a compute that a profile uses
    etag = authed_client.get(f"{COMPUTES}/mylab").headers["etag"]
    problem(
        authed_client.delete(f"{COMPUTES}/mylab", headers={"If-Match": etag}),
        409,
        "compute-in-use",
    )
    # a profile that a catalog entry names
    entry = {
        "name": "rna",
        "engine": "nextflow",
        "location": "/pipelines/rna",
        "profiles": ["mylab"],
    }
    assert authed_client.post(f"{API}/catalog", json=entry).status_code == 201
    etag = authed_client.get(f"{PROFILES}/mylab").headers["etag"]
    problem(
        authed_client.delete(f"{PROFILES}/mylab", headers={"If-Match": etag}),
        409,
        "execution-profile-in-use",
    )
    entry_tag = authed_client.get(f"{API}/catalog/rna").headers["etag"]
    assert (
        authed_client.delete(f"{API}/catalog/rna", headers={"If-Match": entry_tag}).status_code
        == 204
    )
    assert authed_client.delete(f"{PROFILES}/mylab", headers={"If-Match": etag}).status_code == 204
    etag = authed_client.get(f"{COMPUTES}/mylab").headers["etag"]
    assert authed_client.delete(f"{COMPUTES}/mylab", headers={"If-Match": etag}).status_code == 204


def test_deleting_the_default_profile_restores_the_builtin(authed_client: TestClient) -> None:
    create(authed_client)
    path = conf("execution-profiles.toml")
    path.write_text(f'default = "mylab"\n{path.read_text()}')
    assert authed_client.get(PROFILES).json()["default"] == "mylab"
    etag = authed_client.get(f"{PROFILES}/mylab").headers["etag"]
    assert authed_client.delete(f"{PROFILES}/mylab", headers={"If-Match": etag}).status_code == 204
    assert authed_client.get(PROFILES).json()["default"] == "local"
    assert "default" not in path.read_text()


def test_hand_written_slurm_compute_on_a_local_server(
    authed_client: TestClient, synthetic: Path
) -> None:
    """Listed, not usable, the file `ok`; a profile on it is refused at launch."""
    hand_write("computes.toml", '[computes.hpc]\nexecutor = "slurm"\n')
    hand_write("execution-profiles.toml", '[execution-profiles.hpc]\ncompute = "hpc"\n')
    body = authed_client.get(COMPUTES).json()
    assert body["file"]["state"] == "ok"
    (hpc,) = [i for i in body["items"] if i["name"] == "hpc"]
    assert not hpc["usable"] and "spectio init --local" in hpc["unusable_reason"]
    found = launch(authed_client, synthetic, execution_profile="hpc")
    problem(found, 422, "validation-failed", "execution_profile")
    problem(
        authed_client.post(PROFILES, json={"name": "other", "compute": "hpc"}),
        422,
        "validation-failed",
        "compute",
    )


@pytest.mark.parametrize(
    ("text", "mode", "state"),
    [
        ("a=" + "[" * 30000 + "]" * 30000, 0o600, "invalid"),
        ('[computes.x]\nexecutor = "local"\n', 0o620, "refused"),
        ('[computes.x]\nexecutor = "local"\nlocal = {cpus = 0}\n', 0o600, "invalid"),
    ],
)
def test_compute_file_unusable(
    authed_client: TestClient, synthetic: Path, text: str, mode: int, state: str
) -> None:
    """Only the built-ins, with the state and its detail; never overwritten; a launch with a
    built-in still works."""
    hand_write("computes.toml", text, mode)
    body = authed_client.get(COMPUTES).json()
    assert body["file"]["state"] == state and body["file"]["detail"]
    assert [i["name"] for i in body["items"]] == ["local"]
    problem(authed_client.post(COMPUTES, json=MYLAB), 409, "compute-file-unusable")
    assert conf("computes.toml").read_text() == text
    assert launch(authed_client, synthetic).status_code == 201


def test_hand_edit_picked_up(authed_client: TestClient) -> None:
    create(authed_client)
    assert authed_client.get(f"{COMPUTES}/mylab").json()["local"]["cpus"] == 4
    hand_write("computes.toml", conf("computes.toml").read_text().replace("cpus = 4", "cpus = 6"))
    assert authed_client.get(f"{COMPUTES}/mylab").json()["local"]["cpus"] == 6


def test_routes_absent_on_tcp_slurm(settings: Settings, writer: Writer) -> None:
    """On a SLURM server's TCP port (`no_api_reason`) none of the routes is mounted."""
    slurm = settings.model_copy(update={"executor": "slurm", "slurm": SlurmOpts(partition="htc")})
    client = client_for(slurm, writer)
    assert client.app.state.no_api is not None  # type: ignore[attr-defined]
    tag = {"If-Match": '"x"'}
    for response in (
        client.get(COMPUTES),
        client.get(f"{COMPUTES}/slurm"),
        client.post(COMPUTES, json=MYLAB),
        client.put(f"{COMPUTES}/mylab", json=MYLAB, headers=tag),
        client.delete(f"{COMPUTES}/mylab", headers=tag),
        client.get(PROFILES),
        client.post(PROFILES, json=PROFILE),
    ):
        problem(response, 404, "not-found")
        assert "Unix socket" in response.json()["detail"]
    assert not conf("computes.toml").exists() and not conf("execution-profiles.toml").exists()


def calls(tag: str) -> list[tuple[str, str, dict[str, Any]]]:
    put = {"json": {**PROFILE, "label": "New"}, "headers": {"If-Match": tag}}
    return [
        ("GET", PROFILES, {}),
        ("GET", f"{PROFILES}/mylab", {}),
        ("POST", PROFILES, {"json": {**PROFILE, "name": "other"}}),
        ("PUT", f"{PROFILES}/mylab", put),
        ("DELETE", f"{PROFILES}/mylab", {"headers": {"If-Match": tag}}),
        ("GET", COMPUTES, {}),
        ("POST", COMPUTES, {"json": {**MYLAB, "name": "other"}}),
        ("DELETE", f"{COMPUTES}/mylab", {"headers": {"If-Match": tag}}),
    ]


def test_session_cross_site_origin(authed_client: TestClient) -> None:
    """Req. 2 and 7 per route: no session is `401`; another site is `403`, a `GET` too; a write
    without an `Origin` is `403`. Nothing is written."""
    create(authed_client)
    before = conf("execution-profiles.toml").read_bytes(), conf("computes.toml").read_bytes()
    tag = authed_client.get(f"{PROFILES}/mylab").headers["etag"]
    cookies = dict(authed_client.cookies)
    authed_client.cookies.clear()
    for method, url, kw in calls(tag):
        assert authed_client.request(method, url, **kw).status_code == 401, (method, url)
    authed_client.cookies.update(cookies)
    for foreign in ({"Sec-Fetch-Site": "cross-site"}, {"Origin": "http://evil.example"}):
        for method, url, kw in calls(tag):
            headers = {**kw.get("headers", {}), **foreign}
            found = authed_client.request(method, url, **{**kw, "headers": headers})
            problem(found, 403, "cross-site")
    origin = authed_client.headers.pop("origin")
    for method, url, kw in [c for c in calls(tag) if c[0] != "GET"]:
        assert authed_client.request(method, url, **kw).status_code == 403, (method, url)
    authed_client.headers["origin"] = origin
    assert (
        conf("execution-profiles.toml").read_bytes(),
        conf("computes.toml").read_bytes(),
    ) == before


def test_writes_are_logged(authed_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO", logger="spectio_server.api.computes"):
        authed_client.post(COMPUTES, json=MYLAB)
    (record,) = [r for r in caplog.records if r.name == "spectio_server.api.computes"]
    assert record.getMessage().startswith("POST /computes mylab: ")
    assert "'cpus': 4" in record.getMessage()


# --- The migration of environments.toml ------------------------------------------------------

ENVIRONMENTS = """\
default = "mylab"

[environments.mylab]
label = "My lab"
executor = "local"
software = ["conda"]
apptainer_args = "--bind /g"

[environments.mylab.local]
cpus = 4
mem_mib = 8192

[environments.mylab.profiles]
snakemake = "lab"

[environments.hpc]
executor = "slurm"

[environments.hpc.slurm]
partition = "gpu"
account = "lab-a"
time_min = 120
mem_mib = 4096
constraint = "avx512"
gres = "gpu:H100:1"
"""


def test_migration_of_environments(settings: Settings, writer: Writer) -> None:
    """Each environment becomes the compute and the profile of its name, `default` goes to the
    profiles, `environments.toml` is untouched, and a second start changes nothing."""
    hand_write("environments.toml", ENVIRONMENTS)
    client = client_for(settings, writer)
    as_slurm(client, settings)
    computes = {c["name"]: c for c in client.get(COMPUTES).json()["items"] if not c["builtin"]}
    assert computes["mylab"]["local"] == {"cpus": 4, "mem_mib": 8192}
    assert computes["mylab"]["software"] == ["conda"]
    assert computes["mylab"]["apptainer_args"] == "--bind /g"
    assert computes["hpc"]["slurm"] == {"account": "lab-a"} and computes["hpc"]["local"] is None
    listed = client.get(PROFILES).json()
    assert listed["default"] == "mylab"
    profiles = {p["name"]: p for p in listed["items"] if not p["builtin"]}
    assert profiles["mylab"]["compute"] == "mylab" and profiles["mylab"]["software"] == ["conda"]
    assert profiles["mylab"]["engine_profiles"] == {"nextflow": None, "snakemake": "lab"}
    assert profiles["mylab"]["resources"]["cpus"] is None  # the local caps are the compute's
    assert profiles["hpc"]["resources"] == {
        "partition": "gpu",
        "constraint": "avx512",
        "gres": "gpu:H100:1",
        "time_min": 120,
        "mem_mib": 4096,
        "cpus": None,
    }
    assert conf("environments.toml").read_text() == ENVIRONMENTS
    # a profile edited since is not migrated again by a second start, nor a deleted one
    etag = client.get(f"{PROFILES}/hpc").headers["etag"]
    assert client.delete(f"{PROFILES}/hpc", headers={"If-Match": etag}).status_code == 204
    before = conf("computes.toml").read_bytes(), conf("execution-profiles.toml").read_bytes()
    again = client_for(settings, writer)
    as_slurm(again, settings)
    assert [p["name"] for p in again.get(PROFILES).json()["items"]] == ["slurm", "local", "mylab"]
    assert (
        conf("computes.toml").read_bytes(),
        conf("execution-profiles.toml").read_bytes(),
    ) == before


def test_migration_skips_a_file_that_exists_and_a_bad_environments_file(
    authed_client: TestClient,
) -> None:
    hand_write("environments.toml", "not toml [[[")
    assert authed_client.get(COMPUTES).json()["file"]["state"] == "missing"
    assert not conf("computes.toml").exists()


def test_migrated_environment_launches_as_it_did(
    settings: Settings, writer: Writer, synthetic: Path
) -> None:
    """The snapshot of a run launched by the name of a migrated environment is the one that
    environment gave, plus the two names."""
    hand_write("environments.toml", ENVIRONMENTS)
    client = client_for(settings, writer)
    rid = launched(client, synthetic, environment="mylab")
    env = column(writer, rid)
    assert env == {
        "name": "mylab",
        "label": "My lab",
        "executor": "local",
        "slurm": None,
        "local": {"cpus": 4, "mem_mib": 8192},
        "software": ["conda"],
        "apptainer_args": "--bind /g",
        "compute": "mylab",
        "execution_profile": "mylab",
        "state": "recorded",
    }


# --- The catalog's profiles ------------------------------------------------------------------


def test_catalog_entry_profiles_are_checked_on_save(authed_client: TestClient) -> None:
    create(authed_client)
    entry = {"name": "rna", "engine": "nextflow", "location": "/pipelines/rna"}
    cat = f"{API}/catalog"
    for body, field in (
        ({**entry, "profiles": ["gone"]}, "profiles.0"),
        ({**entry, "profiles": ["local", "gone"]}, "profiles.1"),
        ({**entry, "default_profile": "gone"}, "default_profile"),
        ({**entry, "profiles": ["local"], "default_profile": "mylab"}, "body"),  # not in profiles
        ({**entry, "profiles": ["local", "local"]}, "body"),
        ({**entry, "profiles": []}, "profiles"),
    ):
        problem(authed_client.post(cat, json=body), 422, "validation-failed", field)
    good = {**entry, "profiles": ["local", "mylab"], "default_profile": "mylab"}
    made = authed_client.post(cat, json=good)
    assert made.status_code == 201, made.text
    assert (made.json()["profiles"], made.json()["default_profile"]) == (
        ["local", "mylab"],
        "mylab",
    )
    got = authed_client.get(f"{cat}/rna").json()
    assert (got["profiles"], got["default_profile"]) == (["local", "mylab"], "mylab")
    bare = authed_client.post(cat, json={**entry, "name": "bare"}).json()
    assert (bare["profiles"], bare["default_profile"]) == (None, None)


# --- Launch ----------------------------------------------------------------------------------


def test_launch_by_execution_profile_and_by_its_old_name(
    authed_client: TestClient, synthetic: Path, writer: Writer
) -> None:
    create(authed_client)
    one = column(writer, launched(authed_client, synthetic, execution_profile="mylab"))
    two = column(writer, launched(authed_client, synthetic, environment="mylab"))
    assert one == two and (one["compute"], one["execution_profile"]) == ("mylab", "mylab")
    default = column(writer, launched(authed_client, synthetic))
    assert (default["compute"], default["execution_profile"]) == ("local", "local")
    both = launch(authed_client, synthetic, execution_profile="mylab", environment="mylab")
    problem(both, 422, "validation-failed", "environment")
    gone = launch(authed_client, synthetic, execution_profile="gone")
    problem(gone, 422, "validation-failed", "execution_profile")


def test_launch_resolves_a_slurm_profile(
    authed_client: TestClient, synthetic: Path, settings: Settings, writer: Writer
) -> None:
    """The partition, constraint, GRES, time and memory of the profile and the account of its
    compute are the snapshot's `slurm`; the profile's CPUs are the default of a Nextflow run."""
    as_slurm(authed_client, settings)
    authed_client.post(
        COMPUTES, json={"name": "hpc", "executor": "slurm", "slurm": {"account": "lab-a"}}
    )
    resources = {
        "partition": "gpu",
        "constraint": "avx512",
        "gres": "gpu:H100:1",
        "time_min": 240,
        "mem_mib": 65536,
        "cpus": 8,
    }
    body = {"name": "gpu", "compute": "hpc", "resources": resources}
    assert authed_client.post(PROFILES, json=body).status_code == 201
    rid = launched(authed_client, synthetic, execution_profile="gpu")
    env = column(writer, rid)
    assert env["slurm"] == {
        "partition": "gpu",
        "account": "lab-a",
        "time_min": 240,
        "mem_mib": 65536,
        "constraint": "avx512",
        "gres": "gpu:H100:1",
    }
    assert (env["compute"], env["execution_profile"], env["executor"]) == ("hpc", "gpu", "slurm")
    query = select(runner_commands.c.payload).where(runner_commands.c.run_id == rid)
    sent = writer.submit(lambda c: c.execute(query).scalar_one()).result()
    assert "default_resources" not in sent  # Snakemake takes its CPUs from each rule
    nf = launch(authed_client, synthetic, "nextflow", execution_profile="gpu")
    assert nf.status_code == 201, nf.text
    query = select(runner_commands.c.payload).where(runner_commands.c.run_id == nf.json()["id"])
    assert writer.submit(lambda c: c.execute(query).scalar_one()).result()["default_resources"] == {
        "cpus": 8,
        "mem_mib": None,
        "time_min": None,
    }
    own = launch(
        authed_client,
        synthetic,
        "nextflow",
        execution_profile="gpu",
        default_resources={"cpus": 2},
    )
    query = select(runner_commands.c.payload).where(runner_commands.c.run_id == own.json()["id"])
    assert (
        writer.submit(lambda c: c.execute(query).scalar_one()).result()["default_resources"]["cpus"]
        == 2
    )


def test_launch_local_profile_replaces_the_caps(
    authed_client: TestClient, synthetic: Path, writer: Writer
) -> None:
    authed_client.post(COMPUTES, json={**MYLAB, "local": {"cpus": 8, "mem_mib": 16384}})
    body = {**PROFILE, "resources": {"cpus": 2}}
    assert authed_client.post(PROFILES, json=body).status_code == 201
    env = column(writer, launched(authed_client, synthetic, execution_profile="mylab"))
    assert env["local"] == {"cpus": 2, "mem_mib": 16384}


def test_launch_refuses_a_profile_whose_software_left_its_compute(
    authed_client: TestClient, synthetic: Path
) -> None:
    create(authed_client)
    hand_write(
        "computes.toml",
        conf("computes.toml")
        .read_text()
        .replace('software = ["conda", "apptainer"]', 'software = ["conda"]'),
    )
    found = launch(authed_client, synthetic, execution_profile="mylab")
    problem(found, 422, "validation-failed", "execution_profile")
    assert "mylab has no apptainer" in found.json()["errors"][0]["message"]
