"""The effective parameters of api §5.12 (inbox #161): a pipeline's defaults with the source of
each, what inspect answers, and what `POST /runs` validates — never a real engine command."""

import json
import os
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio_server.defaults import DefaultsCache, effective_defaults
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer
from spectio_server.targets import INSPECTIONS

from .conftest import client_for
from .test_launch import table

INSPECT = "/api/v1/workflows:inspect"
RUNS = "/api/v1/runs"

SCHEMA = {  # a nextflow_schema.json: two required params, one with a default
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["outdir", "input"],
    "properties": {
        "outdir": {"type": "string"},
        "input": {"type": "string"},
        "chunks": {"type": "integer", "default": 0},
    },
}
SMK_SCHEMA = """\

$schema: "http://json-schema.org/draft-07/schema#"
type: object
required: [outdir]
properties:
  outdir: {type: string}
"""


class ConfigEngine:
    """Answers `nextflow config` as the real engine does: params without and with the profile."""

    def __init__(
        self,
        base: dict[str, Any] | None = None,
        profile: dict[str, Any] | None = None,
        rc: int = 0,
        profile_rc: int | None = None,
    ) -> None:
        self.calls: list[tuple[str, list[str]]] = []
        self.base, self.profile, self.rc = base, profile, rc
        self.profile_rc = profile_rc

    def __call__(self, engine: str, argv: list[str]) -> tuple[int, str, str]:
        self.calls.append((engine, list(argv)))
        if "-profile" in argv and self.profile_rc is not None:
            return self.profile_rc, "", f"ERROR ~ exit {self.profile_rc}\n"
        if self.rc:
            return self.rc, "", f"ERROR ~ exit {self.rc}\n"
        params = self.profile if "-profile" in argv else self.base
        return 0, json.dumps({"params": params}), ""


def nf_root(tmp_path: Path, name: str = "pipeline") -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "main.nf").write_text("\n")
    (root / "nextflow_schema.json").write_text(json.dumps(SCHEMA))
    return root


def smk_root(
    tmp_path: Path,
    snakefile: str = 'configfile: "config/config.yaml"\n',
    config: str | None = "outdir: results\n",
    name: str = "smk",
) -> Path:
    root = tmp_path / name
    root.mkdir()
    (root / "Snakefile").write_text(snakefile)
    if config is not None:
        (root / "config").mkdir()
        (root / "config" / "config.yaml").write_text(config)
    (root / "config.schema.yaml").write_text(SMK_SCHEMA)
    return root


def defaults_of(
    engine: ConfigEngine,
    name: str,
    profiles: list[str],
    root: Path,
    schema: dict[str, Any] | None = SCHEMA,
    cache: DefaultsCache | None = None,
) -> Any:
    return effective_defaults(root, engine, name, profiles, schema, cache=cache or DefaultsCache())


# --- The function -----------------------------------------------------------------------------


def test_nextflow_sources(tmp_path: Path) -> None:
    root = nf_root(tmp_path)
    engine = ConfigEngine(
        base={"outdir": "results"}, profile={"outdir": "results", "input": "sheet.csv"}
    )
    values, complete = defaults_of(engine, "nextflow", ["test"], root)
    assert complete
    assert values == {
        "chunks": {"value": 0, "source": "schema"},
        "outdir": {"value": "results", "source": "config"},
        "input": {"value": "sheet.csv", "source": "profile"},
    }
    # an argument list through the login-shell engine, the no-profile answer first (§5.12)
    assert [argv for _, argv in engine.calls] == [
        ["config", "-o", "json", str(root)],
        ["config", "-profile", "test", "-o", "json", str(root)],
    ]


def test_nextflow_without_profiles_names_only_config(tmp_path: Path) -> None:
    engine = ConfigEngine(base={"outdir": "results"})
    values, complete = defaults_of(engine, "nextflow", [], nf_root(tmp_path))
    assert complete and values["outdir"] == {"value": "results", "source": "config"}


def test_nextflow_null_is_not_a_value(tmp_path: Path) -> None:
    """nf-core's `input = null`: `nextflow config` prints null, which gives no value (§5.12), so
    a required `input` stays missing rather than becoming a type error on None."""
    engine = ConfigEngine(base={"outdir": "results", "input": None}, profile={"input": None})
    values, complete = defaults_of(engine, "nextflow", ["test"], nf_root(tmp_path))
    assert complete and "input" not in values


def test_nextflow_failure_or_timeout_is_incomplete(tmp_path: Path) -> None:
    for i, rc in enumerate((1, 124, 125)):  # an error, run_login's timeout, its output cap
        engine = ConfigEngine(rc=rc)
        values, complete = defaults_of(engine, "nextflow", [], nf_root(tmp_path, f"p{i}"))
        assert not complete, rc
        assert values == {"chunks": {"value": 0, "source": "schema"}}


def test_nextflow_profile_failure_keeps_the_config_values(tmp_path: Path) -> None:
    engine = ConfigEngine(base={"outdir": "results"}, profile_rc=1)
    values, complete = defaults_of(engine, "nextflow", ["test"], nf_root(tmp_path))
    assert not complete
    assert values["outdir"] == {"value": "results", "source": "config"}
    assert len(engine.calls) == 2  # both answers were asked; the profile one failed


def test_nextflow_cached_per_dir_and_profiles(tmp_path: Path) -> None:
    engine = ConfigEngine(base={"outdir": "results"}, profile={"outdir": "results", "input": "s"})
    cache = DefaultsCache()
    root = nf_root(tmp_path)
    for _ in range(2):
        effective_defaults(root, engine, "nextflow", ["test"], SCHEMA, cache=cache)
    assert len(engine.calls) == 2  # the second answer came from the cache
    effective_defaults(root, engine, "nextflow", ["other"], SCHEMA, cache=cache)
    # the no-profile answer is kept: only the profile command ran again
    assert engine.calls[-1][1] == ["config", "-profile", "other", "-o", "json", str(root)]
    assert len(engine.calls) == 3


def test_nextflow_failure_is_not_cached(tmp_path: Path) -> None:
    """SEC-03/CR-02: a failed `nextflow config` is not kept: the next read runs it again, so a
    later success is seen."""
    engine = ConfigEngine(rc=1)
    cache = DefaultsCache()
    root = nf_root(tmp_path)
    values, complete = defaults_of(engine, "nextflow", [], root, cache=cache)
    assert not complete and values == {"chunks": {"value": 0, "source": "schema"}}
    engine.rc, engine.base = 0, {"outdir": "results"}
    values, complete = defaults_of(engine, "nextflow", [], root, cache=cache)
    assert complete
    assert values["outdir"] == {"value": "results", "source": "config"}
    assert len(engine.calls) == 2


def test_snakemake_unreadable_config_is_not_cached(tmp_path: Path) -> None:
    """SEC-03/CR-02: an unreadable Snakemake source is not kept either: once the file reads, the
    next read sees it."""
    engine = ConfigEngine()
    cache = DefaultsCache()
    root = smk_root(tmp_path, config="{outdir: results\n")  # not YAML this server reads
    values, complete = defaults_of(engine, "snakemake", [], root, schema=None, cache=cache)
    assert not complete and values == {}
    (root / "config" / "config.yaml").write_text("outdir: results\n")
    values, complete = defaults_of(engine, "snakemake", [], root, schema=None, cache=cache)
    assert complete
    assert values["outdir"] == {"value": "results", "source": "config"}


def test_nextflow_config_edit_is_seen(tmp_path: Path) -> None:
    """SEC-04/CR-02: the cache key keeps the mtime_ns of `nextflow.config` and of `conf/` (0
    when missing): an edited nextflow.config is read again."""
    cache = DefaultsCache()
    root = nf_root(tmp_path)
    (root / "nextflow.config").write_text("params.outdir = 'results'\n")
    engine = ConfigEngine(base={"outdir": "results"})
    values, complete = defaults_of(engine, "nextflow", [], root, cache=cache)
    assert complete and values["outdir"] == {"value": "results", "source": "config"}
    engine.base = {"outdir": "other"}
    (root / "nextflow.config").write_text("params.outdir = 'other'\n")
    os.utime(root / "nextflow.config", ns=(2_000_000_000, 2_000_000_000))  # a different mtime_ns
    values, complete = defaults_of(engine, "nextflow", [], root, cache=cache)
    assert complete and values["outdir"] == {"value": "other", "source": "config"}
    assert len(engine.calls) == 2


def test_cache_keeps_at_most_128_entries(tmp_path: Path) -> None:
    """SEC-02/CR-08: at most 128 entries per map of the cache, the least recently used evicted:
    the 129th directory drops the first, which is read again; a hit is kept."""
    cache = DefaultsCache()
    engine = ConfigEngine(base={"outdir": "results"})
    roots = [nf_root(tmp_path, f"p{i}") for i in range(129)]
    for root in roots:
        effective_defaults(root, engine, "nextflow", [], SCHEMA, cache=cache)
    assert len(engine.calls) == 129
    assert len(cache._kept) == 128 and len(cache._base) == 128
    effective_defaults(roots[0], engine, "nextflow", [], SCHEMA, cache=cache)
    assert len(engine.calls) == 130  # roots[0] was the least recently used: read again
    effective_defaults(roots[128], engine, "nextflow", [], SCHEMA, cache=cache)
    assert len(engine.calls) == 130  # the latest answer is still kept
    assert len(cache._kept) == 128


def test_busy_pool_reads_nothing(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    """With no free inspection slot, the source counts as not read (`defaults_complete` false):
    inspect and `POST /runs` answer, they do not raise (§5.12)."""
    client = client_for(settings, writer)
    engine = ConfigEngine(base={"outdir": "results"})
    client.app.state.target_engine = engine  # type: ignore[attr-defined]
    root = nf_root(tmp_path)
    taken = [INSPECTIONS.acquire(blocking=False) for _ in range(2)]
    try:
        assert all(taken)
        body = client.get(INSPECT, params={"location": str(root)}).json()
        assert body["defaults"] == {"chunks": {"value": 0, "source": "schema"}}
        assert body["defaults_complete"] is False
        assert engine.calls == []  # the busy check answers before the engine is asked
        response = launch(client, root, "nextflow")  # no source gives the required names
        assert response.status_code == 201, response.text
        warnings = response.json()["warnings"]
        assert {w["field"] for w in warnings} == {"params.input", "params.outdir"}
    finally:
        for slot in taken:
            if slot:
                INSPECTIONS.release()
    body = client.get(INSPECT, params={"location": str(root)}).json()  # a slot free again
    assert body["defaults_complete"] is True
    assert body["defaults"]["outdir"] == {"value": "results", "source": "config"}


def test_configfile_control_character_is_not_read(tmp_path: Path) -> None:
    """SEC-05/CR-02: a `configfile:` path with a control character is not read: the source counts
    as not read, never a 500."""
    for i, line in enumerate(
        ('configfile: "con\x00fig.yaml"\n', 'configfile: "conf\x1b[2Jig.yaml"\n')
    ):
        root = smk_root(tmp_path, line, config=None, name=f"smk{i}")
        values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
        assert not complete and values == {}, line


def test_configfile_not_utf8_is_not_read(tmp_path: Path) -> None:
    """CR-345R-02: a config file that is not UTF-8 counts as not read, never a 500."""
    root = smk_root(tmp_path, 'configfile: "other.yaml"\n', config=None)
    (root / "other.yaml").write_bytes(b"\xff\xfe")
    values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
    assert not complete and values == {}


def test_nextflow_conf_file_edit_is_seen(tmp_path: Path) -> None:
    """CR-345R-01: a file of `conf/` edited in place (the directory's mtime unchanged) is read
    again."""
    cache = DefaultsCache()
    root = nf_root(tmp_path)
    (root / "conf").mkdir()
    (root / "conf" / "test.config").write_text("params.outdir = 'a'\n")
    engine = ConfigEngine(base={"outdir": "a"})
    defaults_of(engine, "nextflow", [], root, cache=cache)
    before = (root / "conf").stat().st_mtime_ns
    engine.base = {"outdir": "longer"}
    (root / "conf" / "test.config").write_text("params.outdir = 'longer'\n")
    os.utime(root / "conf", ns=(before, before))  # the directory looks untouched
    values, _ = defaults_of(engine, "nextflow", [], root, cache=cache)
    assert values["outdir"] == {"value": "longer", "source": "config"}


def test_snakemake_configfile_literal(tmp_path: Path) -> None:
    engine = ConfigEngine()
    values, complete = defaults_of(engine, "snakemake", [], smk_root(tmp_path), schema=None)
    assert complete
    assert values == {"outdir": {"value": "results", "source": "config"}}
    assert engine.calls == []  # a Snakemake pipeline is read, never run


def test_snakemake_configfile_not_a_literal(tmp_path: Path) -> None:
    lines = ("configfile: PATH\n", 'configfile: "config/../etc"\n', 'configfile: "/etc/x"\n')
    for i, line in enumerate(lines):
        root = smk_root(tmp_path, line, name=f"smk{i}")
        values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
        assert not complete, line
        assert values == {}, line


def test_snakemake_configfile_missing(tmp_path: Path) -> None:
    root = smk_root(tmp_path, 'configfile: "config/nope.yaml"\n')
    values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
    assert not complete and values == {}


def test_snakemake_default_config(tmp_path: Path) -> None:
    root = smk_root(tmp_path, snakefile="rule all:\n  input: 'x'\n")
    values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
    assert complete and values["outdir"] == {"value": "results", "source": "config"}
    # no configfile line and no config/config.yaml: no source applies, nothing is missing
    values, complete = defaults_of(
        ConfigEngine(),
        "snakemake",
        [],
        smk_root(tmp_path, "rule all:\n", config=None, name="s2"),
        schema=None,
    )
    assert complete and values == {}


def test_snakemake_unreadable_config_is_incomplete(tmp_path: Path) -> None:
    root = smk_root(tmp_path, config="{outdir: results\n")  # not YAML this server reads
    values, complete = defaults_of(ConfigEngine(), "snakemake", [], root, schema=None)
    assert not complete and values == {}


def test_params_file_is_the_highest_default(tmp_path: Path) -> None:
    engine = ConfigEngine(base={"outdir": "results"})
    values, complete = effective_defaults(
        nf_root(tmp_path),
        engine,
        "nextflow",
        [],
        SCHEMA,
        params_file={"outdir": "mine", "input": "sheet.csv"},
        cache=DefaultsCache(),
    )
    assert complete
    assert values["outdir"] == {"value": "mine", "source": "params_file"}
    assert values["input"] == {"value": "sheet.csv", "source": "params_file"}


def test_no_engine_no_config_values(tmp_path: Path) -> None:
    engine = ConfigEngine()
    values, complete = effective_defaults(
        nf_root(tmp_path), engine, None, [], SCHEMA, cache=DefaultsCache()
    )
    assert complete and values == {"chunks": {"value": 0, "source": "schema"}}
    assert engine.calls == []


# --- GET /workflows:inspect -------------------------------------------------------------------


def test_inspect_answers_defaults(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    client = client_for(settings, writer)
    engine = ConfigEngine(
        base={"outdir": "results"}, profile={"outdir": "results", "input": "sheet.csv"}
    )
    client.app.state.target_engine = engine  # type: ignore[attr-defined]
    root = nf_root(tmp_path)
    (root / "params.yaml").write_text("outdir: from-the-file\n")
    asked = {"location": str(root), "profiles": "test"}
    response = client.get(INSPECT, params=asked)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["defaults"]["chunks"] == {"value": 0, "source": "schema"}
    assert body["defaults"]["outdir"] == {"value": "results", "source": "config"}
    assert body["defaults"]["input"] == {"value": "sheet.csv", "source": "profile"}
    assert body["defaults_complete"] is True
    # the params file is asked for in the same call: its values are the highest source
    body = client.get(INSPECT, params={**asked, "params_file": "params.yaml"}).json()
    assert body["defaults"]["outdir"] == {"value": "from-the-file", "source": "params_file"}
    assert body["defaults_complete"] is True


def test_inspect_defaults_incomplete_and_bad_profiles(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    client.app.state.target_engine = ConfigEngine(rc=1)  # type: ignore[attr-defined]
    root = nf_root(tmp_path)
    body = client.get(INSPECT, params={"location": str(root)}).json()
    assert body["defaults"] == {"chunks": {"value": 0, "source": "schema"}}
    assert body["defaults_complete"] is False
    response = client.get(INSPECT, params={"location": str(root), "profiles": "a b"})
    assert response.status_code == 422 and response.json()["errors"][0]["field"] == "profiles"


def test_inspect_snakemake_defaults(settings: Settings, writer: Writer, tmp_path: Path) -> None:
    client = client_for(settings, writer)
    body = client.get(INSPECT, params={"location": str(smk_root(tmp_path))}).json()
    assert body["defaults"] == {"outdir": {"value": "results", "source": "config"}}
    assert body["defaults_complete"] is True


# --- POST /runs -------------------------------------------------------------------------------


def launch(client: TestClient, root: Path, engine: str, **body: Any) -> Any:
    return client.post(
        RUNS, json={"workflow": {"location": str(root), "engine": engine}, "params": {}, **body}
    )


def test_launch_profiles_defaults_fill_required(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    client.app.state.target_engine = ConfigEngine(  # type: ignore[attr-defined]
        base={"outdir": "results"}, profile={"outdir": "results", "input": "sheet.csv"}
    )
    root = nf_root(tmp_path)
    response = launch(client, root, "nextflow", profiles=["test"], params={"outdir": "mine"})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["params"] == {"outdir": "mine"}  # params.json keeps the form's values only
    assert "warnings" not in body
    paths = run_paths(settings.runs_root, body["id"])
    assert read_run_manifest(paths.run_dir).params == {"outdir": "mine"}


def test_launch_required_is_a_warning_when_incomplete(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    client.app.state.target_engine = ConfigEngine(rc=1)  # type: ignore[attr-defined]
    response = launch(client, nf_root(tmp_path), "nextflow")
    assert response.status_code == 201, response.text
    body = response.json()
    warnings = body["warnings"]
    assert {w["field"] for w in warnings} == {"params.input", "params.outdir"}
    assert all(w["message"].endswith("is a required property") for w in warnings)
    assert len(table(writer, runs)) == 1  # the run was created; the engine has the last word


def test_launch_required_is_a_422_when_complete(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    client.app.state.target_engine = ConfigEngine(base={"outdir": "results"})  # type: ignore[attr-defined]
    response = launch(client, nf_root(tmp_path), "nextflow")  # no source gives `input`
    assert response.status_code == 422, response.text
    errors = response.json()["errors"]
    assert errors[0]["field"].startswith("params.")
    assert errors[0]["message"].endswith("is a required property")
    assert table(writer, runs) == []


def test_launch_type_error_stays_a_422_when_incomplete(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    client.app.state.target_engine = ConfigEngine(rc=1)  # type: ignore[attr-defined]
    response = launch(client, nf_root(tmp_path), "nextflow", params={"outdir": 3})
    assert response.status_code == 422, response.text
    assert response.json()["errors"][0]["field"] == "params.outdir"
    assert table(writer, runs) == []


def test_launch_snakemake_config_supplies_required(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    response = launch(client, smk_root(tmp_path), "snakemake")
    assert response.status_code == 201, response.text
    assert "warnings" not in response.json()


def test_launch_snakemake_not_a_literal_warns(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    client = client_for(settings, writer)
    root = smk_root(tmp_path, snakefile="configfile: PATH\n", config=None)
    (root / "config").mkdir()
    (root / "config" / "config.yaml").write_text("outdir: results\n")  # there, but not read
    response = launch(client, root, "snakemake")
    assert response.status_code == 201, response.text
    warnings = response.json()["warnings"]
    assert warnings and warnings[0]["field"].startswith("params.")
    assert warnings[0]["message"].endswith("is a required property")


def test_launch_without_a_usable_schema_runs_no_engine(
    settings: Settings, writer: Writer, tmp_path: Path
) -> None:
    """CR-03: the effective parameters are asked only when the schema can be checked against:
    with no schema, or one inferred from config/config.yaml, no `nextflow config` runs (the JVM
    does not start for nothing)."""
    client = client_for(settings, writer)
    engine = ConfigEngine(base={"outdir": "results"})
    client.app.state.target_engine = engine  # type: ignore[attr-defined]
    root = nf_root(tmp_path)
    (root / "nextflow_schema.json").unlink()  # no schema at all: nothing to validate against
    # even a type error goes unchecked: there is nothing to validate against
    response = launch(client, root, "nextflow", params={"outdir": 3})
    assert response.status_code == 201, response.text
    (root / "config").mkdir()
    (root / "config" / "config.yaml").write_text("outdir: results\n")  # a schema inferred from it
    response = launch(client, root, "nextflow")
    assert response.status_code == 201, response.text
    assert engine.calls == []
