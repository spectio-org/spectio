"""The head script and the engine checks (P1 Task 9, Assumptions 13, 14 and 17; Review Focus 1
and 4). The head script runs a stub engine through the login shell, which records its argument
list and its environment in the launch directory."""

import contextlib
import hashlib
import json
import os
import shlex
import shutil
import signal
import stat
import subprocess
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from spectio import loginshell
from spectio.environments import DefaultResources, LocalValues, SlurmValues
from spectio.runner.engines import (
    EngineMissing,
    EngineTooOld,
    check_engine,
    nf_plugin_copy,
    unpack_nf_spectio,
)
from spectio.runner.headscript import (
    engine_args,
    list_rules_args,
    nextflow_config,
    render_head_script,
    write_launch_files,
)
from spectio.runner.resume import check_dirs
from spectio.runner.rundir import make_run_dirs
from spectio.runner.types import ExtraFile, LaunchSpec, ResumeSource

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
    spec = make_spec(home / "runs", slurm=SlurmValues(partition="htc", account="lab"))
    write_launch_files(spec)
    config = (spec.launch_dir / ".spectio" / "spectio.config").read_text()
    assert "process.executor = 'slurm'" in config
    assert "process.queue = 'htc'" in config
    assert "process.clusterOptions = '--account=lab'" in config
    assert "plugins" not in config
    # A quote no `[slurm]` name can hold (SEC-PRE-FU86-01): checked again here, as Snakemake's
    # values are (CR-P3FU86A-04), so a hand-built SlurmValues never reaches `_groovy`
    for bad in (
        SlurmValues.model_construct(account="lab'x"),
        SlurmValues.model_construct(partition="h'tc"),
    ):
        spec = make_spec(home / "runs", slurm=bad)
        with pytest.raises(ValueError, match="not a SLURM name"):
            nextflow_config(spec)


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
        slurm=SlurmValues(partition="htc"),
    )
    assert run_head(spec).returncode == 0
    spectio_dir = spec.launch_dir / ".spectio"
    args = argv(spec)
    assert args[args.index("--snakefile") + 1] == str(location / "workflow" / "Snakefile")
    assert args[args.index("--logger") + 1] == "spectio"
    assert args[args.index("--configfile") + 1] == str(spectio_dir / "params.json")
    assert args[args.index("--executor") + 1] == "slurm"
    assert args[args.index("--workflow-profile") + 1] == str(location / "profiles" / "slurm")
    # The profile owns resources and concurrency (CR-P3T09-04, CR-P3T09-06).
    assert not {"--default-resources", "--jobs", "--cores"} & set(args)
    env = exported(spec)
    assert env["PYTHONPATH"] == str(spectio_dir / "pylib")
    assert (spectio_dir / "pylib" / "snakemake_logger_plugin_spectio" / "__init__.py").is_file()
    assert "NXF_PLUGINS_DEFAULT" not in env


def snakemake_spec(home: Path, **kw: object) -> LaunchSpec:
    location = home / "pipeline"
    (location / "workflow").mkdir(parents=True, exist_ok=True)
    (location / "workflow" / "Snakefile").write_text("")
    engine = shlex.quote(str(stub_engine(home / "bin")))
    return make_spec(home / "runs", engine="snakemake", engine_cmd=engine, location=location, **kw)


@pytest.mark.parametrize(
    ("slurm", "added"),
    [(None, ["--cores", "all"]), (SlurmValues(partition="htc"), ["--jobs", "100"])],
)
def test_snakemake_concurrency_without_a_profile(
    home: Path, bridges: Path, slurm: SlurmValues | None, added: list[str]
) -> None:
    """CR-P3T09-04: Snakemake 9 refuses to run without --cores (local) or --jobs (SLURM); with
    no workflow profile and no such option in extra_args, the head passes one."""
    spec = snakemake_spec(home, slurm=slurm)
    assert run_head(spec).returncode == 0
    args = argv(spec)
    flag = args.index(added[0])
    assert args[flag : flag + 2] == added
    assert not {"--cores", "--jobs"} - {added[0]} & set(args)
    if slurm is not None:  # no profile: Spectio's partition and account apply
        assert args[args.index("--default-resources") + 1] == "slurm_partition='htc'"
    last = [] if slurm is None else ["--local-cores", "2"]  # after extra_args (SEC-P3FU86A-02)
    for given in (["-j", "8"], ["--cores=2"], ["-c4"], ["--jobs", "3"]):
        args = engine_args(replace(spec, extra_args=given))
        end = len(args) - len(last)
        assert args[end:] == last and args[end - len(given) : end] == given
        assert added[0] not in args[: end - len(given)]


def test_snakemake_slurm_local_cores_last(home: Path, bridges: Path) -> None:
    """SEC-P3FU86A-02: `--local-cores 2` comes after `extra_args`, with a workflow profile too,
    so an earlier `--local-cores` in `extra_args` never lifts it (api §5.4)."""
    spec = snakemake_spec(home, slurm=SlurmValues(partition="htc"))
    for given, profiles in ((["--local-cores", "64"], []), (["--local-cores=64"], ["slurm"])):
        args = engine_args(replace(spec, extra_args=given, profiles=profiles))
        assert args[-2:] == ["--local-cores", "2"] and args.count("--local-cores") == 1 + (
            given[0] == "--local-cores"
        )
    assert "--local-cores" not in engine_args(snakemake_spec(home))


def test_workflow_profile_keeps_its_default_resources(home: Path, bridges: Path) -> None:
    """CR-P3T09-06: `--default-resources` on the command line would replace the profile's whole
    `default-resources` (its `runtime` here); with a profile, none is passed."""
    profile = home / "pipeline" / "profiles" / "slurm"
    profile.mkdir(parents=True)
    (profile / "config.yaml").write_text("jobs: 5\ndefault-resources:\n  runtime: 5\n")
    spec = snakemake_spec(
        home, profiles=["slurm"], slurm=SlurmValues(partition="htc", account="lab")
    )
    args = engine_args(spec)
    assert args[args.index("--workflow-profile") + 1] == str(profile)
    assert not {"--default-resources", "--jobs", "--cores"} & set(args)


def test_pythonpath_prepended_to_the_login_profiles(home: Path, bridges: Path) -> None:
    """CR-P3T09-05: a PYTHONPATH the login profile (or a module) sets is kept, after pylib."""
    with (home / ".bash_profile").open("a") as f:
        f.write("export PYTHONPATH=/x\n")
    spec = snakemake_spec(home)
    assert run_head(spec).returncode == 0
    pylib = spec.launch_dir / ".spectio" / "pylib"
    assert exported(spec)["PYTHONPATH"] == f"{pylib}:/x"


@pytest.mark.parametrize(
    ("field", "value"), [("run_id", "run_x\ntouch /tmp/p"), ("run_id", "x"), ("launch_n", 0)]
)
def test_head_script_refuses_a_bad_run_id(
    home: Path, bridges: Path, field: str, value: object
) -> None:
    """CR-P3T09-10, SEC-P3T09-07: the run ID and launch number go into a comment of head.sh."""
    with pytest.raises(ValueError, match=r"run ID|launch number"):
        render_head_script(make_spec(home / "runs", "nextflow", **{field: value}))


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


def test_plugins_dir_is_absolute(home: Path) -> None:
    """SEC-P3T09-05: `~` is expanded, and a relative directory, which the server and the head
    (in the launch directory) would read differently, is refused."""
    copy = "nf-spectio-0.0.1"
    assert nf_plugin_copy({"NXF_PLUGINS_DIR": "~/p"}) == home / "p" / copy
    assert nf_plugin_copy({"NXF_HOME": "~/n"}) == home / "n" / "plugins" / copy
    for env in ({"NXF_HOME": "nxf"}, {"NXF_PLUGINS_DIR": "p"}):
        with pytest.raises(ValueError, match="absolute"):
            nf_plugin_copy(env)


@pytest.mark.parametrize("planted", ["symlink", "group-writable", "file"])
def test_unpack_refuses_an_untrusted_copy(home: Path, bridges: Path, planted: str) -> None:
    """SEC-P3T09-06: an existing nf-spectio copy is kept only if it is a real directory of the
    user's that group and others cannot write; every head loads it."""
    plugins = home / "nxf" / "plugins"
    plugins.mkdir(parents=True)
    copy = plugins / "nf-spectio-0.0.1"
    if planted == "symlink":
        (home / "elsewhere").mkdir()
        copy.symlink_to(home / "elsewhere")
    elif planted == "group-writable":
        copy.mkdir()
        copy.chmod(0o775)
    else:
        copy.write_text("")
    with pytest.raises(PermissionError, match=r"nf-spectio-0\.0\.1"):
        unpack_nf_spectio({"NXF_HOME": str(home / "nxf")})


def test_unpack_private_under_umask_002(home: Path, bridges: Path) -> None:
    """CR-P3T09-R5-01, SEC-P3T09-R5-01: under umask 002, from a bridge copy at 0775 with a file
    at 0664, the unpacked copy has no group or other write bit, so the next call keeps it."""
    source = bridges / "nf-spectio-0.0.1"
    for path in (source, *source.rglob("*")):
        path.chmod(0o775 if path.is_dir() else 0o664)
    env = {"NXF_HOME": str(home / "nxf")}
    old = os.umask(0o002)
    try:
        copy = unpack_nf_spectio(env)
        assert unpack_nf_spectio(env) == copy
    finally:
        os.umask(old)
    for path in (copy, *copy.rglob("*")):
        assert not os.lstat(path).st_mode & 0o022, path
    assert stat.S_IMODE(os.lstat(copy.parent).st_mode) == 0o700  # made new here


def test_unpack_refuses_a_symlink_in_the_bridge(home: Path, bridges: Path) -> None:
    """CR-P3T09-R5-01: the bundled copy holds no symlink; one is refused, not copied."""
    (bridges / "nf-spectio-0.0.1" / "link").symlink_to("/etc")
    with pytest.raises(PermissionError, match="symlink"):
        unpack_nf_spectio({"NXF_HOME": str(home / "nxf")})
    assert not (home / "nxf" / "plugins" / "nf-spectio-0.0.1").exists()


def test_login_timeout_bounded_by_a_detached_child(
    home: Path, login: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-P3T09-R5-04: a child that left the group and holds the pipes (`setsid sleep 600 &`
    in the login profile) does not hold run_login past its timeout and a short wait."""
    monkeypatch.setattr(loginshell, "TIMEOUT_S", 1)
    login(Path("/usr/bin"), Path("/bin"))
    pid_file = home / "detached.pid"
    with (home / ".bash_profile").open("a") as f:
        f.write(f"setsid sleep 600 & echo $! > {shlex.quote(str(pid_file))}\n")
    started = time.monotonic()
    try:
        done = loginshell.run_login("sleep 30")
        assert done.returncode == 124
        assert time.monotonic() - started < 15
    finally:
        with contextlib.suppress(OSError, ValueError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)


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
        except (FileNotFoundError, ProcessLookupError):
            # Gone: reaped before the open (ENOENT) or between the open and the read (ESRCH).
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


LISTING_STUB = """#!/bin/bash
for a in "$@"; do
  if [ "$a" = --list-rules ]; then
    printf '%s\\0' "$@" > list-argv.out
    [ -n "$LIST_FAILS" ] && { echo partial; exit 1; }
    [ -n "$LIST_SLEEPS" ] && "$LIST_SLEEPS" 30
    printf 'all\\ncount_reads (Count reads)\\n'; exit 0
  fi
done
printf '%s\\0' "$@" > argv.out
exit 0
"""


@pytest.mark.parametrize("fails", [False, True])
def test_snakemake_head_writes_rules_txt(home: Path, bridges: Path, fails: bool) -> None:
    """The head writes `.spectio/rules.txt` from `snakemake --list-rules` with the launch's
    configuration (P1 Task 27), 0600; a failing listing leaves none, says so on stderr and
    never stops the run."""
    spec = snakemake_spec(home, extra_args=["--config", "x=1"])
    stub_engine(home / "bin", LISTING_STUB)
    if fails:
        spec = replace(spec, env={"LIST_FAILS": "1"})
    assert run_head(spec).returncode == 0
    spectio_dir = spec.launch_dir / ".spectio"
    listed = (spec.launch_dir / "list-argv.out").read_text().split("\0")[:-1]
    assert listed == [
        "--snakefile",
        str(spec.location / "workflow" / "Snakefile"),
        "--directory",
        str(spec.launch_dir),
        "--configfile",
        str(spectio_dir / "params.json"),
        "--config",
        "x=1",
        "--list-rules",
    ]
    assert "--logger" not in listed
    assert "--list-rules" not in argv(spec)  # the run itself
    rules = spectio_dir / "rules.txt"
    assert not (spectio_dir / "rules.txt.tmp").exists()
    if fails:
        assert not rules.exists()
        assert "--list-rules failed" in (spectio_dir / "head.out").read_text()
    else:
        assert rules.read_text() == "all\ncount_reads (Count reads)\n"
        assert stat.S_IMODE(rules.stat().st_mode) == 0o600


def test_cancel_during_the_listing(home: Path, bridges: Path) -> None:
    """CR-P3T27-01: a Cancel while `--list-rules` runs (the runner writes `.spectio/cancel`,
    then signals the group) stops the listing and the engine never starts; head.exit is 143."""
    spec = replace(snakemake_spec(home), env={"LIST_SLEEPS": shutil.which("sleep") or "/bin/sleep"})
    stub_engine(home / "bin", LISTING_STUB)
    head = write_launch_files(spec)
    proc = subprocess.Popen([BASH, str(head)], start_new_session=True)
    spectio_dir = spec.launch_dir / ".spectio"
    try:
        deadline = time.monotonic() + 20
        while not (spec.launch_dir / "list-argv.out").exists():
            assert time.monotonic() < deadline, "the listing never started"
            time.sleep(0.05)
        time.sleep(0.3)
        (spectio_dir / "cancel").write_text("")
        os.killpg(proc.pid, signal.SIGTERM)
        assert proc.wait(timeout=15) == 143
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    assert not (spec.launch_dir / "argv.out").exists()
    assert (spectio_dir / "head.exit").read_text().split()[0] == "143"


def test_nextflow_head_lists_no_rules(home: Path, bridges: Path) -> None:
    spec = make_spec(home / "runs", engine_cmd=shlex.quote(str(stub_engine(home / "bin"))))
    assert "--list-rules" not in render_head_script(spec)


# --- Resume (P1 Task 30; api §5.1 note 2026-10-28; dev-env §15.3 req. 16) -------------------

PARENT_ID = "run_01K8T9HEAD0000000000000P30"
SESSION = "5f1c8a43-7f62-4a5e-9d4f-0a1b2c3d4e5f"
RESUME_STUB = """#!/bin/bash
for a in "$@"; do
  [ "$a" = --unlock ] && { printf '%s\\0' "$@" > unlock.out; exit 0; }
  [ "$a" = --list-rules ] && exit 1
done
printf '%s\\0' "$@" > argv.out
export -p > env.out
umask > umask.out
[ -e .spectio-launch.lock ] && echo "$(< .spectio-launch.lock)" > lock.out
exit 0
"""


def resume_spec(home: Path, engine: str = "nextflow", **kw: object) -> LaunchSpec:
    """A child launch that resumes PARENT_ID in its launch and work directories."""
    spec = make_spec(home / "runs", engine, **kw)
    parent = make_run_dirs(home / "runs", PARENT_ID)
    st = parent.launch_dir.stat()
    resume = ResumeSource(
        launch_dir=parent.launch_dir,
        work_dir=parent.work_dir,
        device=st.st_dev,
        inode=st.st_ino,
        engine_session_id=SESSION if engine == "nextflow" else None,
    )
    return replace(spec, resume_of=resume)


def test_resume_head_script_nf(home: Path, bridges: Path) -> None:
    """The child's head runs in the parent's launch directory, with `-resume <session id>` and
    the parent's work directory; its spool and engine log stay in its own `.spectio/`; the
    engine runs under umask 022 and while the launch-directory lock names the child."""
    engine = shlex.quote(str(stub_engine(home / "bin", RESUME_STUB)))
    spec = resume_spec(home, engine_cmd=engine)
    assert spec.resume_of is not None
    parent_dir = spec.resume_of.launch_dir
    assert run_head(spec).returncode == 0
    args = (parent_dir / "argv.out").read_text().split("\0")[:-1]
    assert args[args.index("-resume") + 1] == SESSION
    assert args[args.index("-work-dir") + 1] == str(spec.resume_of.work_dir)
    own = spec.launch_dir / ".spectio"
    assert args[args.index("-params-file") + 1] == str(own / "params.json")
    assert (parent_dir / "umask.out").read_text().strip() == "0022"
    assert (parent_dir / "lock.out").read_text().strip() == RUN_ID
    assert not (parent_dir / ".spectio-launch.lock").exists()  # removed when the head ends
    assert (own / "head.exit").is_file() and not (parent_dir / ".spectio" / "head.exit").exists()
    env = exported(replace(spec, launch_dir=parent_dir))
    assert env["SPECTIO_SPOOL_DIR"] == str(own / "events")
    assert env["NXF_LOG_FILE"] == str(own / "nextflow.log")


@pytest.mark.parametrize("unlock", [False, True])
def test_resume_head_script_smk(home: Path, bridges: Path, unlock: bool) -> None:
    """`--unlock` runs first only when the runner proved the parent's head gone, then the run
    with `--rerun-incomplete` in the parent's launch directory."""
    location = home / "pipeline"
    (location / "workflow").mkdir(parents=True)
    (location / "workflow" / "Snakefile").write_text("")
    engine = shlex.quote(str(stub_engine(home / "bin", RESUME_STUB)))
    spec = resume_spec(home, "snakemake", engine_cmd=engine, location=location)
    assert spec.resume_of is not None
    source = replace(spec.resume_of, unlock=unlock)
    spec = replace(spec, resume_of=source)
    parent_dir = source.launch_dir
    assert run_head(spec).returncode == 0
    args = (parent_dir / "argv.out").read_text().split("\0")[:-1]
    assert args[args.index("--directory") + 1] == str(parent_dir)
    assert "--rerun-incomplete" in args and "--unlock" not in args
    unlocked = parent_dir / "unlock.out"
    assert unlocked.exists() == unlock
    if unlock:
        found = unlocked.read_text().split("\0")[:-1]
        assert found[found.index("--directory") + 1] == str(parent_dir)
    assert not (parent_dir / ".spectio" / "rules.txt").exists()  # never the parent's files


UMASK_002_STUB = """#!/bin/bash
umask 002  # a login profile's umask (user-private groups)
{mkdir} -p .nextflow/cache  # as Nextflow makes its own directory: an existing one is kept
exit 0
"""


def test_req16_nextflow_dir_private_under_umask_002(home: Path, bridges: Path) -> None:
    """The head makes `.nextflow/` 0700 before the engine runs (CR-P3T30-02): a first launch
    whose login profile sets umask 002 can still be resumed."""
    body = UMASK_002_STUB.format(mkdir=shutil.which("mkdir") or "/bin/mkdir")
    engine = shlex.quote(str(stub_engine(home / "bin", body)))
    spec = make_spec(home / "runs", engine_cmd=engine)
    assert run_head(spec).returncode == 0
    assert stat.S_IMODE((spec.launch_dir / ".nextflow").stat().st_mode) == 0o700
    check_dirs(home / "runs", RUN_ID)  # not refused


def test_req16_dir_swapped(home: Path, bridges: Path) -> None:
    """The launch directory replaced after the check: `stat .` gives another device and inode,
    so the head refuses and the engine never runs."""
    engine = shlex.quote(str(stub_engine(home / "bin", RESUME_STUB)))
    spec = resume_spec(home, engine_cmd=engine)
    assert spec.resume_of is not None
    parent_dir = spec.resume_of.launch_dir
    parent_dir.rename(parent_dir.with_name("launch.old"))
    parent_dir.mkdir(mode=0o700)
    done = run_head(spec)
    assert done.returncode != 0
    assert not (parent_dir / "argv.out").exists()
    assert "not the one checked" in (spec.launch_dir / ".spectio" / "head.out").read_text()


def test_lock_held_refuses_a_second_head(home: Path, bridges: Path) -> None:
    """`.spectio-launch.lock` (O_EXCL) already there: another head runs in the directory, so this
    one starts no engine and leaves the other's lock alone."""
    engine = shlex.quote(str(stub_engine(home / "bin", RESUME_STUB)))
    spec = resume_spec(home, engine_cmd=engine)
    assert spec.resume_of is not None
    lock = spec.resume_of.launch_dir / ".spectio-launch.lock"
    lock.write_text(PARENT_ID + "\n")
    assert run_head(spec).returncode == 75
    assert not (spec.resume_of.launch_dir / "argv.out").exists()
    assert lock.read_text() == PARENT_ID + "\n"


def test_head_pid_not_written_stops_the_head(home: Path, bridges: Path) -> None:
    """No head.pid means no engine ran (SEC-P3T30-03): when the head cannot write head.pid, it
    stops before the cancel check, the lock and the engine, so Resume may trust its absence."""
    engine = shlex.quote(str(stub_engine(home / "bin", RESUME_STUB)))
    spec = make_spec(home / "runs", engine_cmd=engine)
    (spec.launch_dir / ".spectio" / "head.pid.tmp").mkdir(parents=True)
    assert run_head(spec).returncode != 0
    assert not (spec.launch_dir / "argv.out").exists()
    assert not (spec.launch_dir / ".spectio-launch.lock").exists()
    assert not (spec.launch_dir / ".spectio" / "head.pid").exists()


@pytest.mark.parametrize("session", ["x; rm -rf ~", "5f1c8a43", SESSION + "\n"])
def test_req16_session_id_uuid_in_the_head(home: Path, bridges: Path, session: str) -> None:
    spec = resume_spec(home)
    assert spec.resume_of is not None
    spec = replace(spec, resume_of=replace(spec.resume_of, engine_session_id=session))
    with pytest.raises(ValueError, match="UUID"):
        render_head_script(spec)


# --- FU-P3-86c: the environment's values (api §5.4, How values reach the engines) ----------

CAPS = LocalValues(cpus=2, mem_mib=8192)  # the built-in `local` of a SLURM server


def test_req18_snapshot_nextflow_values(home: Path) -> None:
    slurm = SlurmValues(partition="htc", account="lab", time_min=90, mem_mib=4096)
    config = nextflow_config(make_spec(home / "runs", slurm=slurm))
    assert "process.time = '90m'" in config and "process.memory = '4096 MB'" in config
    config = nextflow_config(make_spec(home / "runs", local=CAPS))
    assert "process.executor = 'local'" in config
    assert "executor {\n  $local {\n    cpus = 2\n    memory = '8192 MB'\n  }\n}" in config
    assert "$local" not in nextflow_config(make_spec(home / "runs"))


def test_req18_snapshot_snakemake_slurm_values(home: Path, bridges: Path) -> None:
    slurm = SlurmValues(partition="htc", account="lab", time_min=90, mem_mib=4096)
    args = engine_args(snakemake_spec(home, slurm=slurm))
    at = args.index("--default-resources")
    assert args[at + 1 : at + 5] == [
        "slurm_partition='htc'",
        "slurm_account='lab'",
        "runtime=90",
        "mem_mb=4096",
    ]
    assert args[-2:] == ["--local-cores", "2"]


@pytest.mark.parametrize("profiles", [[], ["slurm"]])
@pytest.mark.parametrize("given", [[], ["--jobs", "8"], ["--cores", "16"], ["-c32"]])
def test_req18_snapshot_local_cores_last(
    home: Path, bridges: Path, profiles: list[str], given: list[str]
) -> None:
    """SEC-PRE-FU86-R1-02: a capped `local` environment gets `--cores <cpus>` last, after
    `extra_args` and with a workflow profile too, then `--resources mem_mb` after a bare
    `--default-resources` (Snakemake's own defaults)."""
    spec = snakemake_spec(home, local=CAPS, profiles=profiles, extra_args=given)
    args = engine_args(spec)
    tail = ["--default-resources", "--resources", "mem_mb=8192", "--cores", "2"]
    assert args[-5:] == tail
    assert args[-5 - len(given) : -5] == given
    assert "--local-cores" not in args and "all" not in args


def test_req18_snapshot_later_cores_wins_on_snakemake(home: Path) -> None:
    """The [to be validated] of api §5.4: a later `--cores` wins over an earlier `--jobs`, `-j`,
    `--cores` or a workflow profile's `cores` (Snakemake 9.27.1 `cli.py:2103-2109`: `--jobs`
    is an alias only while `--cores` is unset)."""
    snakemake = shutil.which("snakemake")
    if snakemake is None:
        pytest.skip("no snakemake on PATH")
    where = home / "smk"
    (where / "prof").mkdir(parents=True)
    (where / "Snakefile").write_text(
        'rule all:\n    output: "out.txt"\n    shell: "echo {workflow.cores} > {output}"\n'
    )
    (where / "prof" / "config.yaml").write_text("cores: 8\n")
    for given in (["--jobs", "8"], ["-j", "8"], ["--cores", "8"], ["--workflow-profile", "prof"]):
        (where / "out.txt").unlink(missing_ok=True)
        subprocess.run(
            [
                snakemake,
                "-q",
                *given,
                "--default-resources",
                "--resources",
                "mem_mb=8192",
                "--cores",
                "2",
            ],
            cwd=where,
            capture_output=True,
            check=True,
            timeout=120,
        )
        assert (where / "out.txt").read_text().strip() == "2", given


def test_req18_snapshot_bare_double_dash_refused(home: Path, bridges: Path) -> None:
    """SEC-P3FU86A-R3-01: a bare `--` in a Snakemake `extra_args` would turn the caps after it
    into targets, so the launch is refused."""
    for env in ({"slurm": SlurmValues()}, {"local": CAPS}):
        spec = snakemake_spec(home, extra_args=["--", "all"], **env)
        with pytest.raises(ValueError, match="bare --"):
            engine_args(spec)


@pytest.mark.parametrize(
    "bad",
    [
        {"local": LocalValues.model_construct(cpus=True, mem_mib=None)},
        {"local": LocalValues.model_construct(cpus=257, mem_mib=None)},
        {"local": LocalValues.model_construct(cpus=None, mem_mib="1; rm")},  # type: ignore[arg-type]
        {"slurm": SlurmValues.model_construct(time_min=5.0)},  # type: ignore[arg-type]
        {"slurm": SlurmValues.model_construct(mem_mib=0)},
    ],
)
def test_req18_snapshot_values_checked_where_used(
    home: Path, bridges: Path, bad: dict[str, object]
) -> None:
    """SEC-PRE-FU86-R1-06: each integer is `type(v) is int` in its bounds where it is used."""
    for build in (engine_args, nextflow_config):
        with pytest.raises(ValueError, match="not an integer"):
            build(snakemake_spec(home, **bad))


def test_req18_snapshot_head_out_names_the_environment(home: Path, bridges: Path) -> None:
    """SEC-PRE-FU86-R1-10: the first line of head.out names the environment and its values."""
    engine = shlex.quote(str(stub_engine(home / "bin")))
    slurm = SlurmValues(partition="htc", account="mylab")
    spec = make_spec(home / "runs", engine_cmd=engine, environment="mylab", slurm=slurm)
    assert run_head(spec).returncode == 0
    first = (spec.launch_dir / ".spectio" / "head.out").read_text().splitlines()[0]
    assert first == "Spectio: environment mylab (SLURM: partition htc, account mylab)"
    local = make_spec(home / "runs", engine_cmd=engine, environment="local", local=CAPS)
    assert run_head(local).returncode == 0
    first = (local.launch_dir / ".spectio" / "head.out").read_text().splitlines()[0]
    assert first == "Spectio: environment local (local: cpus 2, memory 8192 MiB)"


# --- FU-P3-110b: default resources and the extra config file (api §5.7, req. 20) -------------

NF_EXTRA = "process.memory = '1 GB'\nprocess { withName: 'BIG' { memory = '3 GB' } }\n"


def extra(text: str = NF_EXTRA, kept_as: str = "extra.config") -> ExtraFile:
    return ExtraFile(kept_as, hashlib.sha256(text.encode()).hexdigest(), text)


def test_req20_nextflow_resources_in_spectio_config(home: Path) -> None:
    run = DefaultResources(cpus=4, mem_mib=2048, time_min=60)
    config = nextflow_config(make_spec(home / "runs", local=CAPS, default_resources=run))
    assert "process.cpus = 4\nprocess.memory = '2048 MB'\nprocess.time = '60m'\n" in config
    slurm = SlurmValues(partition="htc", time_min=90, mem_mib=4096)
    only_mem = DefaultResources(mem_mib=100)
    config = nextflow_config(make_spec(home / "runs", slurm=slurm, default_resources=only_mem))
    # the run's key replaces the environment's; one the run leaves out keeps the environment's
    assert "process.memory = '100 MB'" in config and "4096" not in config
    assert config.count("process.time = '90m'") == 1 and "process.cpus" not in config


def test_req20_snakemake_one_default_resources_list(home: Path, bridges: Path) -> None:
    run = DefaultResources(mem_mib=100, time_min=5)
    slurm = SlurmValues(partition="htc", time_min=90, mem_mib=4096)
    args = engine_args(snakemake_spec(home, slurm=slurm, default_resources=run))
    assert args.count("--default-resources") == 1
    at = args.index("--default-resources")
    assert args[at + 1 : at + 5] == ["slurm_partition='htc'", "runtime=5", "mem_mb=100", "--jobs"]
    args = engine_args(snakemake_spec(home, local=CAPS, default_resources=run))
    tail = ["--default-resources", "mem_mb=100", "runtime=5", "--resources", "mem_mb=8192"]
    assert args[-7:] == [*tail, "--cores", "2"]
    args = engine_args(snakemake_spec(home, default_resources=DefaultResources(time_min=5)))
    assert args[-2:] == ["--default-resources", "runtime=5"] and args.count("all") == 1


@pytest.mark.parametrize(
    ("kw", "why"),
    [
        ({"default_resources": DefaultResources(cpus=2)}, "threads"),
        ({"default_resources": DefaultResources(time_min=5), "profiles": ["slurm"]}, "profile"),
        ({"default_resources": DefaultResources.model_construct(mem_mib=True)}, "not an integer"),
    ],
)
def test_req20_snakemake_resources_refused_in_the_head(
    home: Path, bridges: Path, kw: dict[str, object], why: str
) -> None:
    with pytest.raises(ValueError, match=why):
        engine_args(snakemake_spec(home, **kw))


def test_req20_nextflow_resources_checked_where_used(home: Path) -> None:
    bad = DefaultResources.model_construct(cpus=257)
    with pytest.raises(ValueError, match="not an integer"):
        nextflow_config(make_spec(home / "runs", default_resources=bad))


def test_req20_nextflow_extra_config_first(home: Path, bridges: Path) -> None:
    engine = shlex.quote(str(stub_engine(home / "bin")))
    spec = make_spec(home / "runs", engine_cmd=engine, config_file=extra())
    assert run_head(spec).returncode == 0
    own = spec.launch_dir / ".spectio"
    args = argv(spec)
    assert args[args.index("-c") + 1] == f"{own}/extra.config,{own}/spectio.config"
    kept = own / "extra.config"
    assert kept.read_text() == NF_EXTRA and stat.S_IMODE(kept.stat().st_mode) == 0o600


def test_req20_snakemake_extra_configfile_before_params(home: Path, bridges: Path) -> None:
    text = "ref:\n  build: GRCh38\n"
    spec = snakemake_spec(home, config_file=extra(text, "extra.yaml"))
    write_launch_files(spec)
    own = spec.launch_dir / ".spectio"
    for args in (engine_args(spec), list_rules_args(spec)):
        at = args.index("--configfile")
        assert args[at + 1 : at + 3] == [f"{own}/extra.yaml", f"{own}/params.json"]
    assert (own / "extra.yaml").read_text() == text


@pytest.mark.parametrize(
    "bad",
    [
        ExtraFile("extra.config", "0" * 64, NF_EXTRA),  # the bytes changed
        ExtraFile("../extra.config", hashlib.sha256(b"x").hexdigest(), "x"),
        ExtraFile("extra.config", hashlib.sha256(b"x").hexdigest(), None),  # cleared
    ],
)
def test_req20_extra_file_checked_before_the_engine(
    home: Path, bridges: Path, bad: ExtraFile
) -> None:
    spec = make_spec(home / "runs", config_file=bad)
    with pytest.raises(ValueError, match="config file"):
        write_launch_files(spec)
    assert not (spec.launch_dir / ".spectio" / "head.sh").exists()


def test_req20_nextflow_comma_in_the_launch_directory_refused(home: Path) -> None:
    spec = make_spec(home / "ru,ns", config_file=extra())
    with pytest.raises(ValueError, match="comma"):
        engine_args(spec)


def test_req20_banner_names_the_run_values_and_the_file(home: Path, bridges: Path) -> None:
    engine = shlex.quote(str(stub_engine(home / "bin")))
    found = extra()
    spec = make_spec(
        home / "runs",
        engine_cmd=engine,
        environment="local",
        local=CAPS,
        default_resources=DefaultResources(cpus=1, time_min=30),
        config_file=found,
    )
    assert run_head(spec).returncode == 0
    first = (spec.launch_dir / ".spectio" / "head.out").read_text().splitlines()[0]
    assert first == (
        "Spectio: environment local (local: cpus 2, memory 8192 MiB);"
        f" run: cpus 1, time 30 min; config extra.config (sha256 {found.sha256[:12]})"
    )


def test_req20_order_on_nextflow(home: Path, tmp_path: Path) -> None:
    """The [to be validated] of api §5.7: in `-c a,b` the later file wins over the same generic
    key, and the user's `withName` still wins over both."""
    nextflow = os.environ.get("NEXTFLOW") or shutil.which("nextflow")
    if nextflow is None or shutil.which("java") is None:
        pytest.skip("no nextflow and java on PATH")
    run = DefaultResources(mem_mib=2048)
    spec = make_spec(tmp_path / "runs", config_file=extra(), default_resources=run)
    write_launch_files(spec)
    spec.location.mkdir(exist_ok=True)
    (spec.location / "main.nf").write_text("workflow {}\n")
    args = engine_args(spec)
    files = args[args.index("-c") + 1]
    done = subprocess.run(
        [nextflow, "config", "-flat", "-c", files, str(spec.location)],
        capture_output=True,
        text=True,
        check=True,
        timeout=300,
    )
    assert "process.memory = '2048 MB'" in done.stdout
    assert "process.withName:BIG.memory = '3 GB'" in done.stdout


def test_req20_order_on_snakemake(home: Path, bridges: Path) -> None:
    """The deep merge of api §5.7: the workflow's own `configfile:`, then the extra file, then
    the form's params, key by key."""
    snakemake = shutil.which("snakemake")
    if snakemake is None:
        pytest.skip("no snakemake on PATH")
    spec = snakemake_spec(
        home,
        params={"ref": {"release": 112}},
        config_file=extra("ref:\n  build: GRCh38\n", "extra.yaml"),
    )
    (spec.location / "config.yaml").write_text("ref: {build: GRCh37, release: 100, x: own}\n")
    (spec.location / "workflow" / "Snakefile").write_text(
        f'configfile: "{spec.location}/config.yaml"\n'
        'rule all:\n    output: "out.json"\n'
        "    run:\n        import json; json.dump(config, open(output[0], 'w'))\n"
    )
    write_launch_files(spec)
    subprocess.run(
        [snakemake, "-q", *list_rules_args(spec)[:-1], "--cores", "1"],
        capture_output=True,
        check=True,
        timeout=300,
    )
    found = json.loads((spec.engine_dir / "out.json").read_text())
    assert found["ref"] == {"build": "GRCh38", "release": 112, "x": "own"}
