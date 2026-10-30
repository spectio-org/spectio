"""The head script and the engine checks (P1 Task 9, Assumptions 13, 14 and 17; Review Focus 1
and 4). The head script runs a stub engine through the login shell, which records its argument
list and its environment in the launch directory."""

import json
import os
import shlex
import shutil
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from spectio import loginshell
from spectio.config import SlurmOpts
from spectio.runner.engines import (
    EngineMissing,
    EngineTooOld,
    check_engine,
    unpack_nf_spectio,
)
from spectio.runner.headscript import render_head_script, write_launch_files
from spectio.runner.rundir import make_run_dirs
from spectio.runner.types import LaunchSpec

RUN_ID = "run_01K8T9HEAD0000000000000T09"
BASH = shutil.which("bash") or "/bin/bash"
STUB = """#!/bin/bash
case "$1" in
  -version) echo "      version 26.10.4 build 5960"; exit 0;;
  --version) echo 9.27.1; exit 0;;
esac
printf '%s\\0' "$@" > argv.out
export -p > env.out
exit 0
"""


def stub_engine(where: Path, body: str = STUB) -> Path:
    where.mkdir(parents=True, exist_ok=True)
    path = where / "engine"
    path.write_text(body)
    path.chmod(0o755)
    return path


def make_spec(runs_root: Path, engine: str = "nextflow", **kw: object) -> LaunchSpec:
    runs_root.mkdir(mode=0o700, exist_ok=True)
    paths = make_run_dirs(runs_root, RUN_ID)
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "launch_n": 1,
        "engine": engine,
        "engine_cmd": "false",
        "location": runs_root.parent / "pipeline",
        "launch_dir": paths.launch_dir,
        "work_dir": paths.work_dir,
    }
    values.update(kw)
    return LaunchSpec(**values)  # type: ignore[arg-type]


def run_head(spec: LaunchSpec) -> subprocess.CompletedProcess[str]:
    head = write_launch_files(spec)
    return subprocess.run(
        [BASH, str(head)], capture_output=True, text=True, timeout=60, check=False
    )


def argv(spec: LaunchSpec) -> list[str]:
    return (spec.launch_dir / "argv.out").read_text().split("\0")[:-1]


def exported(spec: LaunchSpec) -> dict[str, str]:
    """The engine's environment, from `export -p` (`declare -x NAME="value"` lines)."""
    found = {}
    for line in (spec.launch_dir / "env.out").read_text().splitlines():
        words = shlex.split(line.removeprefix("declare -x "))
        if words and "=" in words[0]:
            name, _, value = words[0].partition("=")
            found[name] = value
    return found


@pytest.fixture
def bridges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bridges directory as the Task 6 and Task 7 builds leave it: `$SPECTIO_BRIDGES_DIR`."""
    root = tmp_path / "bridges"
    meta = root / "nf-spectio-0.0.1" / "classes" / "META-INF"
    meta.mkdir(parents=True)
    (meta / "MANIFEST.MF").write_text("Plugin-Id: nf-spectio\nPlugin-Version: 0.0.1\n")
    logger = root / "snakemake_logger_plugin_spectio"
    logger.mkdir()
    (logger / "__init__.py").write_text("# the Task 7 logger\n")
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(root))
    return root


def test_head_script_shell_metacharacters(home: Path, bridges: Path) -> None:
    location = home / "p" / "a b'$(x)"
    value = "x\n$(rm -rf ~)"
    engine = stub_engine(home / "bin")
    spec = make_spec(
        home / "runs",
        engine_cmd=shlex.quote(str(engine)),
        location=location,
        params={"x": value},
    )
    text = render_head_script(spec)
    assert subprocess.run([BASH, "-n"], input=text, text=True, check=False).returncode == 0
    assert "$(rm" not in text
    assert run_head(spec).returncode == 0
    params_file = spec.launch_dir / ".spectio" / "params.json"
    assert json.loads(params_file.read_text()) == {"x": value}
    args = argv(spec)
    assert args[:2] == ["run", str(location)]  # one word, verbatim
    assert value not in args


def test_head_script_nextflow_args(home: Path, bridges: Path) -> None:
    engine = stub_engine(home / "bin")
    spec = make_spec(
        home / "runs",
        engine_cmd=shlex.quote(str(engine)),
        profiles=["test", "local"],
        nxf_opts="-Xmx1g",
        extra_args=["-resume"],
    )
    assert run_head(spec).returncode == 0
    spectio_dir = spec.launch_dir / ".spectio"
    args = argv(spec)
    assert args[args.index("-params-file") + 1] == str(spectio_dir / "params.json")
    assert args[args.index("-c") + 1] == str(spectio_dir / "spectio.config")
    assert args[args.index("-profile") + 1] == "test,local"
    assert args[args.index("-work-dir") + 1] == str(spec.work_dir)
    assert args[-1] == "-resume"
    assert "-plugins" not in args
    env = exported(spec)
    assert env["NXF_PLUGINS_DEFAULT"] == "nf-spectio@0.0.1"
    assert env["NXF_OPTS"] == "-Xmx1g"
    assert env["SPECTIO_RUN_ID"] == RUN_ID and env["SPECTIO_LAUNCH_N"] == "1"
    assert env["SPECTIO_SPOOL_DIR"] == str(spectio_dir / "events")
    assert "plugins" not in (spectio_dir / "spectio.config").read_text()  # inbox #69


def test_engine_finds_the_unpacked_nf_spectio(
    home: Path, bridges: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T09-03: the login profile exports another NXF_HOME and spec.env is empty, as in
    production; the engine is still pointed at the plugins directory nf-spectio was unpacked to,
    never at one without it (where Nextflow would look the name up in the registry)."""
    monkeypatch.setenv("NXF_HOME", str(home / "server-nxf"))
    with (home / ".bash_profile").open("a") as f:
        f.write(f"export NXF_HOME={shlex.quote(str(home / 'login-nxf'))}\n")
    spec = make_spec(home / "runs", engine_cmd=shlex.quote(str(stub_engine(home / "bin"))))
    assert run_head(spec).returncode == 0
    plugins = Path(exported(spec)["NXF_PLUGINS_DIR"])
    assert plugins == home / "server-nxf" / "plugins"
    assert (plugins / "nf-spectio-0.0.1" / "classes" / "META-INF" / "MANIFEST.MF").is_file()


def test_nextflow_config_on_slurm(home: Path, bridges: Path) -> None:
    spec = make_spec(home / "runs", slurm=SlurmOpts(partition="htc", account="lab'x"))
    write_launch_files(spec)
    config = (spec.launch_dir / ".spectio" / "spectio.config").read_text()
    assert "process.executor = 'slurm'" in config
    assert "process.queue = 'htc'" in config
    assert "process.clusterOptions = '--account=lab\\'x'" in config
    assert "plugins" not in config


def test_head_script_snakemake_args(home: Path, bridges: Path) -> None:
    engine = stub_engine(home / "bin")
    location = home / "pipeline"
    (location / "workflow").mkdir(parents=True)
    (location / "workflow" / "Snakefile").write_text("")
    spec = make_spec(
        home / "runs",
        engine="snakemake",
        engine_cmd=shlex.quote(str(engine)),
        location=location,
        profiles=["slurm"],
        slurm=SlurmOpts(partition="htc"),
    )
    assert run_head(spec).returncode == 0
    spectio_dir = spec.launch_dir / ".spectio"
    args = argv(spec)
    assert args[args.index("--snakefile") + 1] == str(location / "workflow" / "Snakefile")
    assert args[args.index("--logger") + 1] == "spectio"
    assert args[args.index("--configfile") + 1] == str(spectio_dir / "params.json")
    assert args[args.index("--executor") + 1] == "slurm"
    assert args[args.index("--workflow-profile") + 1] == str(location / "profiles" / "slurm")
    assert args[args.index("--default-resources") + 1] == "slurm_partition=htc"
    env = exported(spec)
    assert env["PYTHONPATH"] == str(spectio_dir / "pylib")
    assert (spectio_dir / "pylib" / "snakemake_logger_plugin_spectio" / "__init__.py").is_file()
    assert "NXF_PLUGINS_DEFAULT" not in env


@pytest.mark.parametrize("profile", ["../x", "a,b", "", "-x"])
def test_profile_names_refused(home: Path, bridges: Path, profile: str) -> None:
    with pytest.raises(ValueError, match="profile"):
        render_head_script(make_spec(home / "runs", profiles=[profile]))


def test_head_env_cleared(
    home: Path, bridges: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPECTIO_SERVER_X", "1")
    monkeypatch.setenv("NXF_DEBUG", "3")
    login_dir = home / "loginbin"
    login_dir.mkdir()
    login(login_dir)
    engine = stub_engine(home / "bin")
    spec = make_spec(home / "runs", engine_cmd=shlex.quote(str(engine)))
    assert run_head(spec).returncode == 0
    env = exported(spec)
    assert "SPECTIO_SERVER_X" not in env and "NXF_DEBUG" not in env
    assert env["HOME"] == str(home)
    assert env["PATH"] == str(login_dir)  # the login shell's


def test_engine_missing_and_too_old(home: Path, login: Callable[..., None]) -> None:
    with pytest.raises(EngineMissing) as missing:
        check_engine("nextflow")
    assert missing.value.class_ == "engine_missing"
    assert "nextflow" in str(missing.value)
    old = home / "old"
    stub_engine(old, '#!/bin/sh\necho "      version 24.10.0 build 5928"\n').rename(
        old / "nextflow"
    )
    login(old)
    with pytest.raises(EngineTooOld) as too_old:
        check_engine("nextflow")
    assert too_old.value.class_ == "engine_version"
    assert str(old / "nextflow") in str(too_old.value) and "24.10.0" in str(too_old.value)
    broken = home / "broken"
    with pytest.raises(EngineMissing, match="exited 127"):
        check_engine("snakemake", shlex.quote(str(broken)))
    info = check_engine("snakemake", shlex.quote(str(stub_engine(home / "bin"))))
    assert info.version == "9.27.1"


def test_unpack_is_idempotent(home: Path, bridges: Path) -> None:
    env = {"NXF_HOME": str(home / "nxf")}
    copy = unpack_nf_spectio(env)
    assert copy == home / "nxf" / "plugins" / "nf-spectio-0.0.1"
    manifest = copy / "classes" / "META-INF" / "MANIFEST.MF"
    manifest.write_text("kept")
    assert unpack_nf_spectio(env) == copy
    assert manifest.read_text() == "kept"  # an existing copy is never replaced
    assert unpack_nf_spectio({**env, "NXF_PLUGINS_DIR": str(home / "pd")}).parent == home / "pd"


def test_login_timeout_kills_the_group(
    home: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T08-04: a timed-out command leaves nothing running."""
    monkeypatch.setattr(loginshell, "TIMEOUT_S", 1)
    pid_file = home / "pid"
    login(Path("/usr/bin"), Path("/bin"))
    done = loginshell.run_login(f"sleep 30 & echo $! > {shlex.quote(str(pid_file))}; wait")
    assert done.returncode == 124
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            state = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1][0]
        except FileNotFoundError:
            return
        if state == "Z":
            return
        time.sleep(0.05)
    pytest.fail(f"sleep {pid} still runs after the timeout")


@pytest.mark.engines
def test_nfcore_style_pins_kept(
    home: Path, tmp_path: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    """FC-318: a pipeline that declares nf-schema@2.7.2 resolves it and nf-spectio@0.0.1."""
    nextflow = os.environ.get("NEXTFLOW") or shutil.which("nextflow")
    java = shutil.which("java")
    if not nextflow or not java:
        pytest.fail("Nextflow and Java must be on the PATH, or NEXTFLOW set")
    repo = Path(__file__).resolve().parents[3]
    bridges = tmp_path / "bridges"
    subprocess.run(
        [str(repo / "engine-bridges" / "nf-spectio" / "build.sh"), str(bridges)],
        env={**os.environ, "NEXTFLOW": nextflow},
        check=True,
        capture_output=True,
    )
    monkeypatch.setenv("SPECTIO_BRIDGES_DIR", str(bridges))
    nxf_home = home / ".nextflow"
    monkeypatch.setenv("NXF_HOME", str(nxf_home))
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    (pipeline / "nextflow.config").write_text("plugins {\n  id 'nf-schema@2.7.2'\n}\n")
    (pipeline / "main.nf").write_text(
        "include { paramsSummaryMap } from 'plugin/nf-schema'\n"
        "workflow { println paramsSummaryMap(workflow) }\n"
    )
    login(Path(nextflow).parent, Path(java).parent, Path("/usr/bin"), Path("/bin"))
    proxy = os.environ.get("JAVA_TOOL_OPTIONS")  # a site's profile would set its proxy
    if proxy:
        with (home / ".bash_profile").open("a") as f:
            f.write(f"export JAVA_TOOL_OPTIONS={shlex.quote(proxy)}\n")
    unpack_nf_spectio()
    check_engine("nextflow", shlex.quote(nextflow))
    spec = make_spec(
        tmp_path / "runs",
        engine_cmd=shlex.quote(nextflow),
        location=pipeline,  # no spec.env: the production loop passes none (SEC-P3T09-03)
    )
    done = run_head(spec)
    out = (spec.launch_dir / ".spectio" / "head.out").read_text()
    assert done.returncode == 0, out
    assert (nxf_home / "plugins" / "nf-schema-2.7.2").is_dir()
    spool = list((spec.launch_dir / ".spectio" / "events").glob("nf-spectio-1-*.jsonl"))
    assert spool and spool[0].stat().st_size > 0, out
