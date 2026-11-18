"""The head script, `<launch>/.spectio/head.sh` (P1 Task 9, Assumptions 13 and 17).

One script for both launchers: under `setsid bash` here, as the tmux pane's command in Task 10.
It writes `.spectio/head.pid` (PID, process group, start time, boot ID, host name), clears the
environment down to an allow-list, runs the engine through the user's login shell (`bash -l`),
copies the engine's output to `.spectio/head.out`, and ends with `.spectio/head.exit` (exit
code, epoch). Parameters reach the engine as a file, never as shell words; every value is
quoted with `shlex.quote` (Review Focus 1). Only `engine_cmd`, from `spectio.toml`, is shell.
"""

import contextlib
import hashlib
import json
import os
import re
import shlex
import shutil
from pathlib import Path

from spectio.config import NF_SPECTIO_VERSION, slurm_name
from spectio.environments import PROFILE, LocalValues, SlurmValues
from spectio.loginshell import KEEP
from spectio.runner.engines import SNAKEMAKE_LOGGER, bridge, nf_plugin_copy, unpack_nf_spectio
from spectio.runner.rundir import RUN_ID, private_dir, write_file
from spectio.runner.types import ExtraFile, LaunchSpec
from spectio_sdk.targets import REGISTRY_NAME, RULE, VERSION, RunTarget

ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Snakemake 9 refuses to run without --cores (local) or --jobs (remote executors):
# CR-P3T09-04, verified on 9.27.1 (docs/reviews/code/P3-t09.md). With no workflow profile and
# no such option in extra_args, the head passes `--cores all` (as rna-seq-kallisto-sleuth's CI
# does, docs/research/corpus-and-ci-2026-10-26.md) or `--jobs SLURM_JOBS`: Spectio's own cap on
# the jobs in the queue at once, twice the synthetic profile's `jobs: 50`
# (tests/pipelines/synthetic/snakemake/profiles/slurm/config.yaml); whether sites' per-user
# limits (MaxSubmitJobs) want less is [to be validated].
SLURM_JOBS = 100
# The cores of local rules on a SLURM launch: else every core of the login node (Snakemake
# 9.27.1 `cli.py:586`; SEC-PRE-FU86-R1-02).
LOCAL_CORES = 2
# `snakemake --list-rules` before the run (P1 Task 27): the rules the server groups into stages,
# with this launch's configuration, in `.spectio/rules.txt`. It never holds the run back: a
# listing that fails or takes more than LIST_RULES_S leaves no file, and one line on stderr
# (so in head.out). `timeout` runs only an executable `engine_cmd`, not a shell function of the
# login profile: then the listing fails, and the server groups the rules it reads in the source.
# `timeout`, `mv` and `rm` are taken from the server's PATH: the login profile may set one
# without them.
LIST_RULES_S = 120
# `--foreground` keeps the listing in the head's process group, so a Cancel's signal reaches
# it; the cancel marker, written before the signal, is checked again after it, so the engine
# never starts once the run is cancelled (CR-P3T27-01).
_LIST_RULES = (
    "(umask 077; {timeout} --foreground {s} {command} > {tmp} 2>/dev/null) &&\n"
    "  {mv} -f {tmp} {rules} ||\n"
    "  {{ {rm} -f {tmp}; echo 'spectio: snakemake --list-rules failed:"
    " stages from the rule files' >&2; }}\n"
    "[ -e {cancel} ] && exit 143\n"
)
# A Resume (P1 Task 30, dev-env §15.3 req. 16) runs in the parent's launch directory: the engine
# starts only if `stat .` there gives the device and inode the runner checked, under umask 022.
_RESUME = (
    '[ "$({stat} -c %d:%i .)" = {dev}:{ino} ] ||\n'
    "  {{ echo 'spectio: the launch directory is not the one checked (req. 16)' >&2; exit 1; }}\n"
    "umask 022\n"
)
# The engine starts in a subshell, whose INT and TERM are not trapped, and which checks the
# cancel marker first: a Cancel writes it before its SIGTERM, so a SIGTERM that a trapping shell
# took before the engine started is never lost; one after the check reaches the subshell, or
# the engine it became (bash execs the last command). Without it the engine could still start
# after a Cancel and run until its SIGKILL (FU-P3-108a).
_ENGINE = "( [ -e {cancel} ] && exit 143; {command} )\n"
SESSION_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
LOCK = ".spectio-launch.lock"  # in the engine's directory, while a head of Spectio runs there
LOCKED = 75  # head.exit's code when another head holds the lock
# The names a run's extra config file is kept as in `.spectio/`, by engine (api §5.7).
KEPT_AS = {"nextflow": ("extra.config",), "snakemake": ("extra.yaml", "extra.json")}
SHA256 = re.compile(r"[0-9a-f]{64}")

# The outer script: {launch}, {inner} and {keep} are quoted by `render_head_script`. Both
# shells trap INT and TERM (a trap, not an ignored signal, which the engine would inherit), so
# that the engine gets Ctrl-C and SIGTERM while they wait for it, and head.exit is written only
# once it has ended. A `.spectio/cancel` there once head.pid is written stops the engine from
# ever starting (CR-P3T09-02). `tee` ignores both, so that the engine's last words still
# reach head.out. The engine runs only while this head holds `.spectio-launch.lock` in the
# engine's directory, created with O_EXCL (`set -C`) and holding the run ID, so that a second
# Spectio head never starts there (dev-env §15.3 req. 16); a lock left by a killed head is
# removed by the runner once that head is proven gone (`resume.clear_stale_lock`). A head that
# cannot write head.pid stops before all of this, so that no head.pid means no engine ran
# (`resume.head_gone`, SEC-P3T30-03).
# The head files are made under `umask 077`, so they are 0600 whatever the inherited umask
# (`read_small` refuses a group-writable file: CR-P3T09-01, SEC-P3T09-01); the engine gets the
# inherited umask back, and the login profile may change it.
# head.exit's epoch is bash's own `%(%s)T` (bash >= 4.2), not `$(date)`: a Cancel's SIGTERM to
# the group kills a child of the tail, which left an epoch-less head.exit that never parses, and
# a run that never ends (FU-P3-77).
# head.out starts with the environment's line (`banner`), before the login profile's output.
_HEAD = """#!/usr/bin/env bash
um=$(umask); umask 077
# Spectio head script: run {run_id}, launch {launch_n}. Written by Spectio at each launch.
cd -- {launch} || exit 1
trap : INT TERM
s=$(</proc/$$/stat); s=${{s##*) }}; read -r -a f <<< "$s"
{{ printf '%s %s %s %s %s\\n' "$$" "${{f[2]}}" "${{f[19]}}" \\
  "$(</proc/sys/kernel/random/boot_id)" "$HOSTNAME" > .spectio/head.pid.tmp &&
  mv -f .spectio/head.pid.tmp .spectio/head.pid; }} || exit 1  # no head.pid, no engine
keep=()
for v in {keep}; do [ -n "${{!v+x}}" ] && keep+=("$v=${{!v}}"); done
lock={lock}
if [ -e .spectio/cancel ]; then
  code=143  # cancelled before the engine ran
elif ! (set -C; printf '%s\\n' {run_id} > "$lock") 2>/dev/null; then
  if [ -e .spectio/cancel ]; then
    code=143  # a Cancel's SIGTERM ended the subshell that takes the lock
  else
    echo "spectio: $lock exists: another Spectio head runs there" > .spectio/head.out
    code={locked}
  fi
else
  {banner} > .spectio/head.out
  (umask "$um"; exec env -i "${{keep[@]}}" bash -l -c {inner} spectio-head) 2>&1 |
    (trap '' INT TERM; exec tee -a .spectio/head.out)
  code=${{PIPESTATUS[0]}}
  {{ [ "$(< "$lock")" = {run_id} ]; }} 2>/dev/null && {rm} -f -- "$lock"
fi
printf '%s %(%s)T\\n' "$code" -1 > .spectio/head.exit.tmp
mv -f .spectio/head.exit.tmp .spectio/head.exit
exit "$code"
"""


def _spectio(spec: LaunchSpec) -> Path:
    return spec.launch_dir / ".spectio"


def _extra(spec: LaunchSpec) -> Path | None:
    """Where the run's extra config file is kept (api §5.7), its name and hash checked again."""
    kept = spec.config_file
    if kept is None:
        return None
    if kept.kept_as not in KEPT_AS[spec.engine] or not SHA256.fullmatch(kept.sha256):
        raise ValueError(f"the config file's name {kept.kept_as[:40]!r} or hash is not allowed")
    return _spectio(spec) / kept.kept_as


def _extra_bytes(kept: ExtraFile) -> bytes:
    """The bytes of the launch command, checked against their SHA-256 before they are kept."""
    if kept.text is None:
        raise ValueError("the config file's bytes are not in the launch command")
    data = kept.text.encode()
    if hashlib.sha256(data).hexdigest() != kept.sha256:
        raise ValueError("the config file's bytes do not match their SHA-256")
    return data


def engine_args(spec: LaunchSpec) -> list[str]:
    """The engine's arguments after `engine_cmd`, each one word."""
    spectio = _spectio(spec)
    params = str(spectio / "params.json")
    profiles = spec.profiles
    for name in profiles:
        if not PROFILE.fullmatch(name):
            raise ValueError(f"profile name {name!r} is not allowed")
    if spec.engine == "snakemake" and len(profiles) > 1:
        raise ValueError("a Snakemake launch takes one profile")
    target = spec.target
    if spec.engine == "nextflow":
        args = ["run", str(spec.location)] if target is None else _module_run(spec, target)
        args += ["-params-file", params]
        # The user's file first, Spectio's own last, so that its generic keys win (api §5.7).
        configs = [str(p) for p in (_extra(spec), spectio / "spectio.config") if p is not None]
        if len(configs) > 1 and "," in str(spectio):
            raise ValueError("a comma in the launch directory would split -c's list of files")
        args += ["-c", ",".join(configs), "-work-dir", str(spec.engine_work_dir)]
        if profiles:
            args += ["-profile", ",".join(profiles)]
        if spec.resume_of is not None:
            session = spec.resume_of.engine_session_id
            if session is not None and not SESSION_ID.fullmatch(session):
                raise ValueError(f"engine_session_id {session!r} is not a UUID (req. 16)")
            args += ["-resume", *([session] if session else [])]
    else:
        run = _run(spec)
        if "cpus" in run:  # refused by `POST /runs` too (api §5.7)
            raise ValueError("Snakemake takes CPUs from each rule's threads")
        if run and profiles:
            raise ValueError(f"the profile {profiles[0]} sets the resources")
        args = [*_snakemake_base(spec, target), "--logger", "spectio"]
        if spec.resume_of is not None:  # `snakemake/cli.py:919-922`, v9.27.1
            args.append("--rerun-incomplete")
        if spec.slurm is not None:
            # The SLURM plugin deletes a job's log when the job succeeds; kept, every job has
            # its log while the run directory exists (architecture §13.7, `slurm.py:209-243`).
            args += ["--executor", "slurm", "--slurm-keep-successful-logs"]
        if profiles:
            # The profile owns resources and concurrency: `--default-resources` here would
            # replace its whole `default-resources` (CR-P3T09-06), so the environment's SLURM
            # values apply only to a launch without a profile.
            args += ["--workflow-profile", str(spec.location / "profiles" / profiles[0])]
        else:
            if spec.slurm is not None:
                resources = _slurm_resources(spec.slurm, run)
                if resources:
                    args += ["--default-resources", *resources]
            if not any(_sets_concurrency(arg) for arg in spec.extra_args):
                if spec.slurm is not None:
                    args += ["--jobs", str(SLURM_JOBS)]
                elif _cap(spec.local, "cpus") is None:
                    args += ["--cores", "all"]
    args += spec.extra_args
    if spec.engine == "snakemake":
        # Last, after `extra_args` and a workflow profile, so that none lifts them (api §5.4,
        # SEC-P3FU86A-02, SEC-PRE-FU86-R1-02); a later `--cores` wins over an earlier `--jobs`
        # or a profile's `cores` (Snakemake 9.27.1 `cli.py:2103-2109`). A bare `--` would turn
        # them into targets (SEC-P3FU86A-R3-01).
        if "--" in spec.extra_args:
            raise ValueError("a bare -- in [engines] extra_args.snakemake is not allowed")
        if target is not None and any(_stops(arg) for arg in spec.extra_args):
            # A target never meets a stop flag: those belong to stage gates (api §5.10).
            raise ValueError("[engines] extra_args.snakemake holds a stop flag beside a target")
        if spec.slurm is not None:
            args += ["--local-cores", str(LOCAL_CORES)]
        else:
            args += _local_caps(spec.local, _run(spec))
    return args


def _int(value: object, low: int, high: int) -> int:
    """`value` when it is an int in its bounds: checked again where it is used
    (SEC-PRE-FU86-R1-06)."""
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{value!r} is not an integer from {low} to {high}")
    return value


MEM_MIB = (1, 4_194_304)
TIME_MIN = (1, 43_200)
_RUN_BOUNDS = {"cpus": (1, 256), "mem_mib": MEM_MIB, "time_min": TIME_MIN}


def _run(spec: LaunchSpec) -> dict[str, int]:
    """The run's `default_resources` that are set (api §5.7), each checked again here."""
    found = spec.default_resources
    if found is None:
        return {}
    values = {key: getattr(found, key) for key in _RUN_BOUNDS}
    return {k: _int(v, *_RUN_BOUNDS[k]) for k, v in values.items() if v is not None}


def _cap(local: LocalValues | None, key: str) -> int | None:
    value = None if local is None else getattr(local, key)
    if value is None:
        return None
    return _int(value, *((1, 256) if key == "cpus" else MEM_MIB))


def _slurm_resources(slurm: SlurmValues, run: dict[str, int]) -> list[str]:
    """`--default-resources` values: partition and account as Python string literals, since
    Snakemake evaluates each value after expanding `~` and `$` (9.27.1 `resources.py:801-825`)
    and a SLURM name holds no quote (SEC-PRE-FU86-01), checked again here; integers as such.
    The run's time and memory replace the environment's, in this one list (api §5.7)."""
    found = [
        f"slurm_{key}='{slurm_name(value)}'"
        for key, value in (("partition", slurm.partition), ("account", slurm.account))
        if value
    ]
    if (time := run.get("time_min", slurm.time_min)) is not None:
        found.append(f"runtime={_int(time, *TIME_MIN)}")
    if (mem := run.get("mem_mib", slurm.mem_mib)) is not None:
        found.append(f"mem_mb={_int(mem, *MEM_MIB)}")
    return found


def _local_caps(local: LocalValues | None, run: dict[str, int]) -> list[str]:
    """The caps of a `local` environment: one `--default-resources` list, bare (Snakemake's
    own, so a rule that declares no memory still counts some) or with the run's values (api
    §5.7), then `--resources mem_mb`, and `--cores`."""
    args = []
    mem = _cap(local, "mem_mib")
    own = [f"{n}={run[k]}" for k, n in (("mem_mib", "mem_mb"), ("time_min", "runtime")) if k in run]
    if mem is not None or own:
        args += ["--default-resources", *own]
    if mem is not None:
        args += ["--resources", f"mem_mb={mem}"]
    if (cpus := _cap(local, "cpus")) is not None:
        args += ["--cores", str(cpus)]
    return args


def _module_run(spec: LaunchSpec, target: RunTarget) -> list[str]:
    """`module run <name> -version <v>` for a registry module, always pinned (api §5.10, #161
    §D); `module run <dir>` for a local one, whose version is its `meta.yml`'s."""
    if target.kind != "module":
        raise ValueError(f"a Nextflow run cannot target a {target.kind}")
    if target.source != "registry":
        return ["module", "run", str(spec.location)]
    version = target.version
    if version is None or version == "latest" or not VERSION.fullmatch(version):
        raise ValueError("a registry module runs at a pinned version")
    if not REGISTRY_NAME.fullmatch(target.name) or str(spec.location) != target.name:
        raise ValueError(f"{target.name!r} is not a registry module name")
    return ["module", "run", target.name, "-version", version]


# Snakemake options that stop or limit a run; gates own them, a target never meets them.
STOP_FLAGS = ("--until", "--omit-from", "--allowed-rules", "--forcerun")
STOP_SHORT = "UOR"  # `-U`, `-O`, `-R`, also attached (`-Umerge`) or grouped (`-pU`, `-nRx`)
# Snakemake options that are prefixes of a stop flag: argparse takes an exact name first
EXACT = ("--force",)


def _stops(arg: str) -> bool:
    """A stop flag, or what argparse reads as one: a short form, or a long one's prefix."""
    if not arg.startswith("--"):  # a short cluster with U, O or R anywhere: refused whole
        return arg.startswith("-") and any(letter in STOP_SHORT for letter in arg[1:])
    name = arg.split("=", 1)[0]
    return len(name) > 2 and name not in EXACT and any(flag.startswith(name) for flag in STOP_FLAGS)


def _snakemake_base(spec: LaunchSpec, target: RunTarget | None = None) -> list[str]:
    snakefile = spec.location / "workflow" / "Snakefile"
    if not snakefile.is_file():
        snakefile = spec.location / "Snakefile"
    rule: list[str] = []
    if target is not None:
        if target.kind != "rule" or not RULE.fullmatch(target.name):
            raise ValueError(f"{target.name!r} is not a rule name")
        # A positional right after `--directory D`: after `--configfile`, which takes several
        # values, it would be read as a config file (spike module-run, finding 6).
        rule = [target.name]
    # "Multiple files overwrite each other in the given order" (api §5.7): the user's, then
    # the form's
    files = [str(p) for p in (_extra(spec), _spectio(spec) / "params.json") if p is not None]
    return [
        "--snakefile",
        str(snakefile),
        "--directory",
        str(spec.engine_dir),
        *rule,
        "--configfile",
        *files,
    ]


def list_rules_args(spec: LaunchSpec) -> list[str]:
    """`--list-rules` with the launch's Snakefile, configuration and extra arguments."""
    return _snakemake_base(spec) + spec.extra_args + ["--list-rules"]


def _sets_concurrency(arg: str) -> bool:
    """`--cores`, `--jobs`, `-c` or `-j`, with or without its value attached."""
    return arg.split("=", 1)[0] in ("--cores", "--jobs") or arg[:2] in ("-c", "-j")


def engine_env(spec: LaunchSpec) -> dict[str, str]:
    """What the head script exports after the login profile, before the engine runs."""
    env = {
        "SPECTIO_RUN_ID": spec.run_id,
        "SPECTIO_LAUNCH_N": str(spec.launch_n),
        "SPECTIO_SPOOL_DIR": str(_spectio(spec) / "events"),
    }
    if spec.engine == "nextflow":
        env["NXF_PLUGINS_DEFAULT"] = f"nf-spectio@{NF_SPECTIO_VERSION}"  # never -plugins (#69)
        # Where `write_launch_files` unpacks nf-spectio, whatever NXF_HOME the login profile
        # sets: the engine never looks for it elsewhere, nor in the registry (SEC-P3T09-03).
        env["NXF_PLUGINS_DIR"] = str(nf_plugin_copy({**os.environ, **spec.env}).parent)
        env["NXF_ANSI_LOG"] = "false"
        # One engine log per run: `.nextflow.log` rolls at each start in the same directory
        # (architecture §13.7, `LoggerHelper.groovy:301-322`).
        env["NXF_LOG_FILE"] = str(_spectio(spec) / "nextflow.log")
        if spec.nxf_opts:
            env["NXF_OPTS"] = spec.nxf_opts
    env.update(spec.env)
    for name in env:
        if not ENV_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a variable name")
    return env


def render_head_script(spec: LaunchSpec) -> str:
    # Both go into a comment line of head.sh (CR-P3T09-10, SEC-P3T09-07).
    if not RUN_ID.fullmatch(spec.run_id):
        raise ValueError(f"{spec.run_id!r} is not a run ID")
    if type(spec.launch_n) is not int or spec.launch_n < 1:
        raise ValueError(f"{spec.launch_n!r} is not a launch number")
    exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in engine_env(spec).items())
    command = " ".join([spec.engine_cmd, *map(shlex.quote, engine_args(spec))])
    tools = {t: shlex.quote(shutil.which(t) or t) for t in ("timeout", "mv", "rm", "stat")}
    own = str(_spectio(spec))
    inner = (
        f"trap : INT TERM\ncd -- {shlex.quote(str(spec.engine_dir))} || exit 1\nexport {exports}\n"
    )
    if spec.resume_of is not None:
        resume = spec.resume_of
        inner += _RESUME.format(stat=tools["stat"], dev=int(resume.device), ino=int(resume.inode))
    if spec.engine == "nextflow":  # `.command.log` never starts with the environment (req. 13)
        inner += "unset NXF_DEBUG\n"
    if spec.engine == "snakemake":  # in front of the login profile's own (CR-P3T09-05)
        pylib = shlex.quote(str(_spectio(spec) / "pylib"))
        inner += f"export PYTHONPATH={pylib}${{PYTHONPATH:+:$PYTHONPATH}}\n"
        if spec.resume_of is not None and spec.resume_of.unlock:  # `cli.py:1226`, v9.27.1
            unlock = " ".join([spec.engine_cmd, *map(shlex.quote, _snakemake_base(spec))])
            inner += f"{unlock} --unlock || exit $?\n"
        listing = " ".join([spec.engine_cmd, *map(shlex.quote, list_rules_args(spec))])
        inner += _LIST_RULES.format(
            s=LIST_RULES_S,
            command=listing,
            timeout=tools["timeout"],
            mv=tools["mv"],
            rm=tools["rm"],
            tmp=shlex.quote(own + "/rules.txt.tmp"),
            rules=shlex.quote(own + "/rules.txt"),
            cancel=shlex.quote(own + "/cancel"),
        )
    inner += _ENGINE.format(cancel=shlex.quote(own + "/cancel"), command=command)
    line = banner(spec)
    return _HEAD.format(
        run_id=spec.run_id,
        launch_n=spec.launch_n,
        launch=shlex.quote(str(spec.launch_dir)),
        keep=" ".join(KEEP),
        inner=shlex.quote(inner),
        lock=shlex.quote(str(spec.engine_dir / LOCK)),
        locked=LOCKED,
        rm=tools["rm"],
        banner=":" if line is None else f"printf '%s\\n' {shlex.quote(line)}",
    )


def _groovy(value: str) -> str:
    """A single-quoted Groovy string, which interpolates nothing."""
    if any(ord(c) < 0x20 for c in value):
        raise ValueError(f"{value!r} holds a control character")
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def nextflow_config(spec: LaunchSpec) -> str:
    """`.spectio/spectio.config`: the environment's executor and values (api §5.4); never a
    `plugins` block, which would replace the pipeline's plugins (inbox #69). Generic `process`
    settings, so the pipeline's selectors still win. The run's `default_resources` replace the
    environment's time and memory, key by key (api §5.7)."""
    lines = ["// Written by Spectio for this launch."]
    run = _run(spec)
    slurm = spec.slurm
    if slurm is not None:
        lines.append("process.executor = 'slurm'")
        if slurm.partition:
            lines.append(f"process.queue = {_groovy(slurm_name(slurm.partition))}")
        if slurm.account:
            account = "--account=" + slurm_name(slurm.account)  # SEC-PRE-FU86-01, again
            lines.append(f"process.clusterOptions = {_groovy(account)}")
    else:
        lines.append("process.executor = 'local'")
    own = slurm or SlurmValues()
    if (cpus := run.get("cpus")) is not None:
        lines.append(f"process.cpus = {_int(cpus, 1, 256)}")
    if (mem := run.get("mem_mib", own.mem_mib)) is not None:
        lines.append(f"process.memory = '{_int(mem, *MEM_MIB)} MB'")
    if (time := run.get("time_min", own.time_min)) is not None:
        lines.append(f"process.time = '{_int(time, *TIME_MIN)}m'")
    if slurm is not None:
        return "\n".join(lines) + "\n"
    caps = []
    if (cpus := _cap(spec.local, "cpus")) is not None:
        caps.append(f"    cpus = {cpus}")
    if (mem := _cap(spec.local, "mem_mib")) is not None:
        caps.append(f"    memory = '{mem} MB'")
    if caps:  # scoped to the local executor
        lines += ["executor {", "  $local {", *caps, "  }", "}"]
    return "\n".join(lines) + "\n"


def banner(spec: LaunchSpec) -> str | None:
    """The first line of head.out: the environment and its values (SEC-PRE-FU86-R1-10), the
    run's default resources and its extra config file (api §5.7)."""
    parts = [] if spec.environment is None else [_environment_text(spec)]
    names = (("cpus", "cpus {}"), ("mem_mib", "memory {} MiB"), ("time_min", "time {} min"))
    run = _run(spec)
    if run:
        parts.append("run: " + ", ".join(text.format(run[k]) for k, text in names if k in run))
    if (kept := _extra(spec)) is not None and spec.config_file is not None:
        parts.append(f"config {kept.name} (sha256 {spec.config_file.sha256[:12]})")
    return "Spectio: " + "; ".join(parts) if parts else None


def _environment_text(spec: LaunchSpec) -> str:
    if spec.slurm is not None:
        values = [(k, getattr(spec.slurm, k)) for k in ("partition", "account")]
        named = [f"{k} {v}" for k, v in values if v]
        if spec.slurm.time_min is not None:
            named.append(f"time {spec.slurm.time_min} min")
        if spec.slurm.mem_mib is not None:
            named.append(f"memory {spec.slurm.mem_mib} MiB")
        kind = "SLURM"
    else:
        named = []
        if (cpus := _cap(spec.local, "cpus")) is not None:
            named.append(f"cpus {cpus}")
        if (mem := _cap(spec.local, "mem_mib")) is not None:
            named.append(f"memory {mem} MiB")
        kind = "local"
    values_text = f"{kind}: {', '.join(named)}" if named else kind
    return f"environment {spec.environment} ({values_text})"


def write_launch_files(spec: LaunchSpec) -> Path:
    """Write `.spectio/{params.json, spectio.config, head.sh}` and deliver the bridge: unpack
    nf-spectio, or copy the Snakemake logger to `.spectio/pylib/`. Returns the head script.
    Raises BridgeMissing when the bridge is not there, ValueError on a bad spec.
    For Nextflow, `.nextflow/` is made 0700 in the engine's directory first, so that the umask
    the engine gets (the login profile's) never leaves it group-writable, which a Resume
    refuses (`resume.check_dirs`, CR-P3T30-02)."""
    script = render_head_script(spec).encode()
    params = json.dumps(spec.params, ensure_ascii=False).encode()
    extra = spec.config_file
    kept = None if extra is None else (extra.kept_as, _extra_bytes(extra))
    if spec.engine == "nextflow":
        with contextlib.suppress(FileExistsError):  # a symlink there is refused at Resume
            os.mkdir(spec.engine_dir / ".nextflow", 0o700)
    with private_dir(spec.launch_dir, ".spectio") as fd:
        write_file(fd, "params.json", params)
        if kept is not None:  # the run's snapshot (api §5.7)
            write_file(fd, *kept)
        if spec.engine == "nextflow":
            write_file(fd, "spectio.config", nextflow_config(spec).encode())
            unpack_nf_spectio({**os.environ, **spec.env})
        else:
            pylib = _spectio(spec) / "pylib"
            shutil.rmtree(pylib, ignore_errors=True)
            os.mkdir("pylib", 0o700, dir_fd=fd)
            shutil.copytree(bridge(SNAKEMAKE_LOGGER), pylib / SNAKEMAKE_LOGGER)
        write_file(fd, "head.sh", script)
    return _spectio(spec) / "head.sh"
