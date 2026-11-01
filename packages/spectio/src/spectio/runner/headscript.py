"""The head script, `<launch>/.spectio/head.sh` (P1 Task 9, Assumptions 13 and 17).

One script for both launchers: under `setsid bash` here, as the tmux pane's command in Task 10.
It writes `.spectio/head.pid` (PID, process group, start time, boot ID, host name), clears the
environment down to an allow-list, runs the engine through the user's login shell (`bash -l`),
copies the engine's output to `.spectio/head.out`, and ends with `.spectio/head.exit` (exit
code, epoch). Parameters reach the engine as a file, never as shell words; every value is
quoted with `shlex.quote` (Review Focus 1). Only `engine_cmd`, from `spectio.toml`, is shell.
"""

import json
import os
import re
import shlex
import shutil
from pathlib import Path

from spectio.config import NF_SPECTIO_VERSION
from spectio.loginshell import KEEP
from spectio.runner.engines import SNAKEMAKE_LOGGER, bridge, nf_plugin_copy, unpack_nf_spectio
from spectio.runner.rundir import RUN_ID, private_dir, write_file
from spectio.runner.types import LaunchSpec

PROFILE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")  # never a path, a comma or an option
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Snakemake 9 refuses to run without --cores (local) or --jobs (remote executors):
# CR-P3T09-04, verified on 9.27.1 (docs/reviews/code/P3-t09.md). With no workflow profile and
# no such option in extra_args, the head passes `--cores all` (as rna-seq-kallisto-sleuth's CI
# does, docs/research/corpus-and-ci-2026-10-26.md) or `--jobs SLURM_JOBS`: Spectio's own cap on
# the jobs in the queue at once, twice the synthetic profile's `jobs: 50`
# (tests/pipelines/synthetic/snakemake/profiles/slurm/config.yaml); whether sites' per-user
# limits (MaxSubmitJobs) want less is [to be validated].
SLURM_JOBS = 100
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
    "(umask 077; {timeout} --foreground {s} {command} > .spectio/rules.txt.tmp 2>/dev/null) &&\n"
    "  {mv} -f .spectio/rules.txt.tmp .spectio/rules.txt ||\n"
    "  {{ {rm} -f .spectio/rules.txt.tmp; echo 'spectio: snakemake --list-rules failed:"
    " stages from the rule files' >&2; }}\n"
    "[ -e .spectio/cancel ] && exit 143\n"
)

# The outer script: {launch}, {inner} and {keep} are quoted by `render_head_script`. Both
# shells trap INT and TERM (a trap, not an ignored signal, which the engine would inherit), so
# that the engine gets Ctrl-C and SIGTERM while they wait for it, and head.exit is written only
# once it has ended. A `.spectio/cancel` there once head.pid is written stops the engine from
# ever starting (CR-P3T09-02). `tee` ignores both, so that the engine's last words still
# reach head.out.
# The head files are made under `umask 077`, so they are 0600 whatever the inherited umask
# (`read_small` refuses a group-writable file: CR-P3T09-01, SEC-P3T09-01); the engine gets the
# inherited umask back, and the login profile may change it.
_HEAD = """#!/usr/bin/env bash
um=$(umask); umask 077
# Spectio head script: run {run_id}, launch {launch_n}. Written by Spectio at each launch.
cd -- {launch} || exit 1
trap : INT TERM
s=$(</proc/$$/stat); s=${{s##*) }}; read -r -a f <<< "$s"
printf '%s %s %s %s %s\\n' "$$" "${{f[2]}}" "${{f[19]}}" \\
  "$(</proc/sys/kernel/random/boot_id)" "$HOSTNAME" > .spectio/head.pid.tmp
mv -f .spectio/head.pid.tmp .spectio/head.pid
keep=()
for v in {keep}; do [ -n "${{!v+x}}" ] && keep+=("$v=${{!v}}"); done
if [ -e .spectio/cancel ]; then
  code=143  # cancelled before the engine ran
else
  (umask "$um"; exec env -i "${{keep[@]}}" bash -l -c {inner} spectio-head) 2>&1 |
    (trap '' INT TERM; exec tee .spectio/head.out)
  code=${{PIPESTATUS[0]}}
fi
printf '%s %s\\n' "$code" "$(date +%s)" > .spectio/head.exit.tmp
mv -f .spectio/head.exit.tmp .spectio/head.exit
exit "$code"
"""


def _spectio(spec: LaunchSpec) -> Path:
    return spec.launch_dir / ".spectio"


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
    if spec.engine == "nextflow":
        args = ["run", str(spec.location), "-params-file", params]
        args += ["-c", str(spectio / "spectio.config"), "-work-dir", str(spec.work_dir)]
        if profiles:
            args += ["-profile", ",".join(profiles)]
    else:
        args = [*_snakemake_base(spec), "--logger", "spectio"]
        if spec.slurm is not None:
            # The SLURM plugin deletes a job's log when the job succeeds; kept, every job has
            # its log while the run directory exists (architecture §13.7, `slurm.py:209-243`).
            args += ["--executor", "slurm", "--slurm-keep-successful-logs"]
        if profiles:
            # The profile owns resources and concurrency: `--default-resources` here would
            # replace its whole `default-resources` (CR-P3T09-06), so [slurm] partition and
            # account apply only to a launch without a profile.
            args += ["--workflow-profile", str(spec.location / "profiles" / profiles[0])]
        else:
            if spec.slurm is not None:
                slurm = {"partition": spec.slurm.partition, "account": spec.slurm.account}
                resources = [f"slurm_{key}={value}" for key, value in slurm.items() if value]
                if resources:
                    args += ["--default-resources", *resources]
            if not any(_sets_concurrency(arg) for arg in spec.extra_args):
                args += ["--cores", "all"] if spec.slurm is None else ["--jobs", str(SLURM_JOBS)]
    return args + spec.extra_args


def _snakemake_base(spec: LaunchSpec) -> list[str]:
    snakefile = spec.location / "workflow" / "Snakefile"
    if not snakefile.is_file():
        snakefile = spec.location / "Snakefile"
    params = str(_spectio(spec) / "params.json")
    return [
        "--snakefile",
        str(snakefile),
        "--directory",
        str(spec.launch_dir),
        "--configfile",
        params,
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
    inner = (
        f"trap : INT TERM\ncd -- {shlex.quote(str(spec.launch_dir))} || exit 1\nexport {exports}\n"
    )
    if spec.engine == "nextflow":  # `.command.log` never starts with the environment (req. 13)
        inner += "unset NXF_DEBUG\n"
    if spec.engine == "snakemake":  # in front of the login profile's own (CR-P3T09-05)
        pylib = shlex.quote(str(_spectio(spec) / "pylib"))
        inner += f"export PYTHONPATH={pylib}${{PYTHONPATH:+:$PYTHONPATH}}\n"
        listing = " ".join([spec.engine_cmd, *map(shlex.quote, list_rules_args(spec))])
        tools = {t: shlex.quote(shutil.which(t) or t) for t in ("timeout", "mv", "rm")}
        inner += _LIST_RULES.format(s=LIST_RULES_S, command=listing, **tools)
    inner += f"{command}\n"
    return _HEAD.format(
        run_id=spec.run_id,
        launch_n=spec.launch_n,
        launch=shlex.quote(str(spec.launch_dir)),
        keep=" ".join(KEEP),
        inner=shlex.quote(inner),
    )


def _groovy(value: str) -> str:
    """A single-quoted Groovy string, which interpolates nothing."""
    if any(ord(c) < 0x20 for c in value):
        raise ValueError(f"{value!r} holds a control character")
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def nextflow_config(spec: LaunchSpec) -> str:
    """`.spectio/spectio.config`: the SLURM executor on a SLURM environment; never a
    `plugins` block, which would replace the pipeline's plugins (inbox #69)."""
    lines = ["// Written by Spectio for this launch."]
    if spec.slurm is not None:
        lines.append("process.executor = 'slurm'")
        if spec.slurm.partition:
            lines.append(f"process.queue = {_groovy(spec.slurm.partition)}")
        if spec.slurm.account:
            lines.append(f"process.clusterOptions = {_groovy('--account=' + spec.slurm.account)}")
    return "\n".join(lines) + "\n"


def write_launch_files(spec: LaunchSpec) -> Path:
    """Write `.spectio/{params.json, spectio.config, head.sh}` and deliver the bridge: unpack
    nf-spectio, or copy the Snakemake logger to `.spectio/pylib/`. Returns the head script.
    Raises BridgeMissing when the bridge is not there, ValueError on a bad spec."""
    script = render_head_script(spec).encode()
    params = json.dumps(spec.params, ensure_ascii=False).encode()
    with private_dir(spec.launch_dir, ".spectio") as fd:
        write_file(fd, "params.json", params)
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
