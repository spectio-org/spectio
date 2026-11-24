"""The effective parameters of api §5.12 (inbox #161): a pipeline's defaults with the source of
each, what inspect answers, and what `POST /runs` validates — never a real engine command."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from spectio.config import Settings
from spectio.runner.rundir import read_run_manifest, run_paths
from spectio_server.defaults import DefaultsCache, effective_defaults
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

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
) -> Any:
    return effective_defaults(root, engine, name, profiles, schema, cache=DefaultsCache())


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
    assert {w["field"].split(".", 1)[0] for w in warnings} == {"params"}
    # both missing names are named, whatever field the error carries (§5.12 fixes it in parallel)
    assert {w["message"].split("'")[1] for w in warnings} == {"input", "outdir"}
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
