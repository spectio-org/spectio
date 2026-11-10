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

from pydantic import AfterValidator, BaseModel, ConfigDict, model_validator

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
    revision: str | None = None  # required for Git, `null` for a path
    profile: ProfileName | None = None
    params_file: ParamsFile | None = None

    @model_validator(mode="after")
    def _revision(self) -> "Entry":
        if not self.location.startswith("/"):
            locations.check_revision(self.revision)
        elif self.revision is not None:
            raise ValueError("a path takes no revision")
        return self


KIND = envfile.Kind(FILE, "pipelines", Entry, MAX_ENTRIES, frozenset({"new"}), False)


def catalog_path() -> Path:
    """The one path of the file, beside `envfile.environments_path()`."""
    return KIND.path()
