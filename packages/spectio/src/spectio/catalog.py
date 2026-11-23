"""The pipeline catalog as typed data and its file (FU-P3-87a; api §5.6; dev-env §15.3 req. 18).

An entry is a named pipeline location with optional launch defaults, one `[pipelines.<name>]`
table in `catalog.toml` next to `environments.toml`, read and written by `spectio.envfile` (the
same reads, states, identity check, lock and rename). The model is strict, as those of §5.4: a
location or revision refused by `spectio.locations` raises ValueError inside pydantic, so a bad
value written by hand makes the file `invalid`, never a 500, and its detail never quotes it.
Saving checks how the fields are written, not what they name: nothing here reads the directory
or contacts a remote.
"""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from spectio import envfile, locations
from spectio.environments import Label, Name, ProfileName

FILE = "catalog.toml"
MAX_ENTRIES = 100

Location = Annotated[str, AfterValidator(locations.check_location)]
ParamsFile = Annotated[str, AfterValidator(locations.check_params_file)]


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    name: Name
    label: Label | None = None
    engine: Literal["nextflow", "snakemake"]
    location: Location
    # required for Git, `null` for a path; checked as a field, so a refusal names `revision`
    revision: str | None = Field(None, validate_default=True)
    profile: ProfileName | None = None
    params_file: ParamsFile | None = None

    @field_validator("revision")
    @classmethod
    def _revision(cls, revision: str | None, info: ValidationInfo) -> str | None:
        location = info.data.get("location")  # absent when the location was refused
        if location is None:
            return revision
        if not location.startswith("/"):
            return locations.check_revision(revision)
        if revision is not None:
            raise ValueError("a path takes no revision")
        return revision


KIND = envfile.Kind(FILE, "pipelines", Entry, MAX_ENTRIES, frozenset({"new"}), False)


def catalog_path() -> Path:
    """The one path of the file, beside `envfile.environments_path()`."""
    return KIND.path()
