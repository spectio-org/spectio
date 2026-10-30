"""Spectio's settings, in layers (architecture §7.3), lowest priority first: built-in defaults,
then `spectio.toml`, then `SPECTIO_*` variables, then flags (the keyword arguments of
`Settings`).

`spectio.toml` is `$SPECTIO_CONFIG`, else `~/.spectio/spectio.toml`: the data directory in the
shared home holds it (dev-env §15.3, Where data lives), whatever `data_dir` says.
"""

import json
import os
import secrets
import shlex
import tomllib
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

NF_SPECTIO_VERSION = "0.0.1"  # the nf-spectio the wheel carries (engine-bridges/nf-spectio)
DEFAULT_PORT = 8080  # architecture §7.3


def default_data_dir() -> Path:
    return Path.home() / ".spectio"


def config_path() -> Path:
    return Path(os.environ.get("SPECTIO_CONFIG") or default_data_dir() / "spectio.toml")


def _absolute(path: Path) -> Path:
    path = path.expanduser()
    if not path.is_absolute():
        raise ValueError(f"{path} must be an absolute path")
    return path


AbsPath = Annotated[Path, AfterValidator(_absolute)]
Seconds = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SlurmOpts(_Model):
    """The engines' SLURM executors, for their task jobs (P1 Assumption 14)."""

    partition: str | None = None
    account: str | None = None


class EngineOpts(_Model):
    """How the head script runs each engine: a shell command, from the login shell's PATH or
    given as is (P1 Assumption 14)."""

    nextflow_cmd: str | None = None
    snakemake_cmd: str | None = None
    nxf_opts: str = "-Xmx2g"
    extra_args: dict[Literal["nextflow", "snakemake"], list[str]] = {}  # per engine


class RunnerOpts(_Model):
    head_watch_s: Seconds = 5
    spool_s: Seconds = 2


# One flat name per setting, SPECTIO_<AREA>_<FIELD>, no `__` nesting (architecture §7.3).
_ENV: dict[str, tuple[str, ...]] = {
    "SPECTIO_DATA_DIR": ("data_dir",),
    "SPECTIO_DB_DIR": ("db_dir",),
    "SPECTIO_RUNS_ROOT": ("runs_root",),
    "SPECTIO_PORT": ("port",),
    "SPECTIO_EXECUTOR": ("executor",),
    "SPECTIO_SLURM_PARTITION": ("slurm", "partition"),
    "SPECTIO_SLURM_ACCOUNT": ("slurm", "account"),
    "SPECTIO_ENGINES_NEXTFLOW_CMD": ("engines", "nextflow_cmd"),
    "SPECTIO_ENGINES_SNAKEMAKE_CMD": ("engines", "snakemake_cmd"),
    "SPECTIO_ENGINES_NXF_OPTS": ("engines", "nxf_opts"),
    "SPECTIO_ENGINES_EXTRA_ARGS_NEXTFLOW": ("engines", "extra_args", "nextflow"),
    "SPECTIO_ENGINES_EXTRA_ARGS_SNAKEMAKE": ("engines", "extra_args", "snakemake"),
    "SPECTIO_RUNNER_HEAD_WATCH_S": ("runner", "head_watch_s"),
    "SPECTIO_RUNNER_SPOOL_S": ("runner", "spool_s"),
}


class _FlatEnv(PydanticBaseSettingsSource):
    """The `SPECTIO_*` variables of `_ENV`, nested as the settings are."""

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False  # unused: __call__ reads the whole table

    def __call__(self) -> dict[str, Any]:
        found: dict[str, Any] = {}
        for name, keys in _ENV.items():
            value = os.environ.get(name)
            if value is None:
                continue
            node = found
            for key in keys[:-1]:
                node = node.setdefault(key, {})
            node[keys[-1]] = shlex.split(value) if "extra_args" in keys else value
        return found


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="forbid")

    data_dir: AbsPath = Field(default_factory=default_data_dir)
    db_dir: AbsPath | None = None  # unset: default_db_dir() at each start (§15.3 fallback)
    runs_root: AbsPath = Field(default_factory=lambda: Path.home() / "spectio-runs")
    port: int = Field(DEFAULT_PORT, ge=1024, le=65535)
    executor: Literal["slurm", "local"] = "slurm"  # local: P1 Assumption 23
    host: str | None = None  # the login node spectio init ran on (the host pin)
    slurm: SlurmOpts = SlurmOpts()
    engines: EngineOpts = EngineOpts()
    runner: RunnerOpts = RunnerOpts()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        toml = TomlConfigSettingsSource(settings_cls, toml_file=config_path())
        return init_settings, _FlatEnv(settings_cls), toml


def _toml_value(value: Any) -> str:
    if isinstance(value, dict):  # an inline table; its keys are bare (engine names)
        return "{" + ", ".join(f"{k} = {_toml_value(v)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    if isinstance(value, int | float):
        return repr(value)
    # A JSON string is a TOML basic string, but for DEL, which TOML wants escaped; not
    # ensure_ascii, whose surrogate pairs TOML rejects (SEC-P3T08-05).
    return json.dumps(str(value), ensure_ascii=False).replace("\x7f", "\\u007f")


def render_toml(settings: Settings) -> str:
    """`spectio.toml` for `settings`: unset values left out, and no `[slurm]` in local mode."""
    data = settings.model_dump(mode="json", exclude_none=True)
    if settings.executor == "local":
        del data["slurm"]
    top = [f"{k} = {_toml_value(v)}" for k, v in data.items() if not isinstance(v, dict)]
    tables = [
        "\n".join([f"[{name}]", *(f"{k} = {_toml_value(v)}" for k, v in table.items())])
        for name, table in data.items()
        if isinstance(table, dict)
    ]
    return "\n\n".join(["\n".join(top), *tables]) + "\n"


def write_config(settings: Settings, path: Path | None = None) -> Path:
    """Write `spectio.toml` atomically, mode 0600, in a directory that must exist."""
    path = path or config_path()
    text = render_toml(settings)
    tomllib.loads(text)  # a render that would not load never replaces the file
    tmp = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path
