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
from spectio.runner.rundir import private_dir, write_file
from spectio.runner.types import LaunchSpec

PROFILE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}")  # never a path, a comma or an option
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

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


def _profiles(spec: LaunchSpec) -> list[str]:
    for name in spec.profiles:
        if not PROFILE.fullmatch(name):
            raise ValueError(f"profile name {name!r} is not allowed")
    if spec.engine == "snakemake" and len(spec.profiles) > 1:
        raise ValueError("a Snakemake launch takes one profile")
    return spec.profiles


def engine_args(spec: LaunchSpec) -> list[str]:
    """The engine's arguments after `engine_cmd`, each one word."""
    spectio = _spectio(spec)
    params = str(spectio / "params.json")
    profiles = _profiles(spec)
    if spec.engine == "nextflow":
        args = ["run", str(spec.location), "-params-file", params]
        args += ["-c", str(spectio / "spectio.config"), "-work-dir", str(spec.work_dir)]
        if profiles:
            args += ["-profile", ",".join(profiles)]
    else:
        snakefile = spec.location / "workflow" / "Snakefile"
        if not snakefile.is_file():
            snakefile = spec.location / "Snakefile"
        args = ["--snakefile", str(snakefile), "--directory", str(spec.launch_dir)]
        args += ["--configfile", params, "--logger", "spectio"]
        if spec.slurm is not None:
            args += ["--executor", "slurm"]
            slurm = {"partition": spec.slurm.partition, "account": spec.slurm.account}
            resources = [f"slurm_{key}={value}" for key, value in slurm.items() if value]
            if resources:
                args += ["--default-resources", *resources]
        if profiles:
            args += ["--workflow-profile", str(spec.location / "profiles" / profiles[0])]
    return args + spec.extra_args


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
        if spec.nxf_opts:
            env["NXF_OPTS"] = spec.nxf_opts
    else:
        env["PYTHONPATH"] = str(_spectio(spec) / "pylib")
    env.update(spec.env)
    for name in env:
        if not ENV_NAME.fullmatch(name):
            raise ValueError(f"{name!r} is not a variable name")
    return env


def render_head_script(spec: LaunchSpec) -> str:
    exports = " ".join(f"{k}={shlex.quote(v)}" for k, v in engine_env(spec).items())
    command = " ".join([spec.engine_cmd, *map(shlex.quote, engine_args(spec))])
    inner = (
        f"trap : INT TERM\ncd -- {shlex.quote(str(spec.launch_dir))} || exit 1\n"
        f"export {exports}\n{command}\n"
    )
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
