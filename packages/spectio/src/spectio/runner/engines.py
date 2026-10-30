"""The engines and their bridges (P1 Task 9, Assumptions 14 and 17).

`check_engine` runs the engine's version command through the login shell, as the head script
will run the engine, and refuses one that is missing or older than the floor (architecture
§13.4; Review Focus 4). The bridges come from `bridge_dir()`: `$SPECTIO_BRIDGES_DIR` (the Task 6
and Task 7 build output, in a checkout) or the wheel's `spectio/bridges` (Task 21).
"""

import os
import re
import secrets
import shlex
import shutil
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from spectio.config import NF_SPECTIO_VERSION
from spectio.loginshell import run_login, which

NEXTFLOW_VERSION = re.compile(r"version ([0-9][0-9.]*)")  # as nf-spectio's build.sh reads it
SNAKEMAKE_VERSION = re.compile(r"([0-9]+\.[0-9]+(?:\.[0-9]+)?)")
NF_SPECTIO_DIR = f"nf-spectio-{NF_SPECTIO_VERSION}"
SNAKEMAKE_LOGGER = "snakemake_logger_plugin_spectio"  # the Task 7 module, put on PYTHONPATH

# engine: (version flag, pattern, floor, name) — floors from P1 Global Constraints.
_ENGINES = {
    "nextflow": ("-version", NEXTFLOW_VERSION, (25, 4), "Nextflow"),
    "snakemake": ("--version", SNAKEMAKE_VERSION, (9, 0), "Snakemake"),
}


class EngineError(Exception):
    """The engine cannot run this launch; `class_` is the run's `failure_class` (api §7)."""

    class_ = "engine_missing"


class EngineMissing(EngineError):
    pass


class EngineTooOld(EngineError):
    class_ = "engine_version"


@dataclass(frozen=True)
class EngineInfo:
    path: str  # the engine found on the login PATH, or the command as given
    version: str


def check_engine(engine: str, cmd: str | None = None) -> EngineInfo:
    """The engine `cmd` runs (default: the engine on the login shell's PATH), with its version.

    Raises EngineMissing when it is not found or its version command fails, EngineTooOld when
    its version is under the floor; the message names the command and the version found.
    """
    flag, pattern, floor, name = _ENGINES[engine]
    if cmd is None:
        found = which(engine)[engine]
        if found is None:
            raise EngineMissing(f"{engine} not found on the login shell's PATH")
        path, cmd = found, shlex.quote(found)
    else:
        path = cmd
    out = run_login(f"{cmd} {flag}")
    match = pattern.search(out.stdout) if out.returncode == 0 else None
    if not match:
        first = "".join((out.stderr or out.stdout).strip().splitlines()[:1])
        raise EngineMissing(f"`{cmd} {flag}` exited {out.returncode}: {first}")
    version = match.group(1)
    if tuple(int(n) for n in version.split(".")[:2]) < floor:
        raise EngineTooOld(
            f"{cmd}: {name} {version} is older than {'.'.join(map(str, floor))}, "
            "the oldest Spectio supports"
        )
    return EngineInfo(path, version)


def bridge_dir() -> Path:
    given = os.environ.get("SPECTIO_BRIDGES_DIR")
    return Path(given) if given else Path(str(files("spectio") / "bridges"))


class BridgeMissing(FileNotFoundError):
    pass


def bridge(name: str) -> Path:
    path = bridge_dir() / name
    if not path.is_dir():
        raise BridgeMissing(f"{path} is missing: build the bridges or set SPECTIO_BRIDGES_DIR")
    return path


def nf_plugin_copy(env: Mapping[str, str]) -> Path:
    """`$NXF_PLUGINS_DIR/nf-spectio-<ver>` (default `$NXF_HOME/plugins`, architecture §13.8),
    with `~` expanded. Raises ValueError on a relative directory: the server and the head, which
    runs in the launch directory, would read it differently (SEC-P3T09-05)."""
    nxf_home = Path(env.get("NXF_HOME") or Path.home() / ".nextflow").expanduser()
    plugins = Path(env.get("NXF_PLUGINS_DIR") or nxf_home / "plugins").expanduser()
    if not plugins.is_absolute():
        raise ValueError(
            f"the Nextflow plugins directory {plugins} (NXF_PLUGINS_DIR or NXF_HOME) "
            "is not an absolute path"
        )
    return plugins / NF_SPECTIO_DIR


def _existing_copy(dest: Path) -> bool:
    """Whether a copy is there; raises PermissionError when it is not a real directory of this
    user's that group and others cannot write, since every head loads it (SEC-P3T09-06)."""
    try:
        st = os.lstat(dest)
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o022:
        raise PermissionError(
            f"{dest} is not a directory of yours that only you can write "
            f"(owner uid {st.st_uid}, mode {stat.filemode(st.st_mode)}): remove it"
        )
    return True


def unpack_nf_spectio(env: Mapping[str, str] | None = None) -> Path:
    """Copy the bundled nf-spectio into the plugins directory; an existing copy of the same
    version is kept as it is, so a second call changes nothing (architecture §13.8)."""
    dest = nf_plugin_copy(os.environ if env is None else env)
    if _existing_copy(dest):
        return dest
    source = bridge(NF_SPECTIO_DIR)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{secrets.token_hex(8)}")
    shutil.copytree(source, tmp, symlinks=True)
    try:
        tmp.rename(dest)
    except OSError:
        shutil.rmtree(tmp)
        if not _existing_copy(dest):  # not merely a copy made at the same time
            raise
    return dest
