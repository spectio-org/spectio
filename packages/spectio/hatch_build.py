"""Put both engine bridges in the package as `spectio/_bridges/` (P1 Task 21, architecture §7.3).

From a checkout, `engine-bridges/nf-spectio/build.sh` builds the unpacked nf-spectio (it needs
Java and Nextflow) and the Snakemake logger module is copied as it is; the sdist carries both
under `src/spectio/_bridges/`, so a wheel built from the sdist needs neither the checkout nor
Nextflow. `uv build` makes every wheel from its sdist, and an sdist without the bridges fails.
A wheel built straight from a checkout (`uv pip install ./packages/spectio`, CI's import check)
goes without them, with a warning; so does an editable install, where a checkout sets
`SPECTIO_BRIDGES_DIR`.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PACKAGED = "src/spectio/_bridges"  # where the sdist carries them, and the wheel's `spectio/`
LOGGER = "snakemake_logger_plugin_spectio"


class BridgesHook(BuildHookInterface):
    PLUGIN_NAME = "custom"
    _tmp: tempfile.TemporaryDirectory[str] | None = None

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        if version == "editable" or (root / PACKAGED).is_dir():  # an sdist that carries them
            return
        self._tmp = tempfile.TemporaryDirectory(prefix="spectio-bridges-")
        out = Path(self._tmp.name)
        try:
            self._build(root.parents[1] / "engine-bridges", out)
        except (OSError, subprocess.CalledProcessError) as exc:
            if self.target_name == "sdist":
                raise
            self.app.display_warning(f"spectio: this wheel carries no engine bridges: {exc}")
            return
        dest = PACKAGED if self.target_name == "sdist" else "spectio/_bridges"
        build_data["force_include"][str(out)] = dest

    def _build(self, bridges: Path, out: Path) -> None:
        logger = bridges / "snakemake-logger-plugin-spectio" / LOGGER
        if not (logger / "__init__.py").is_file():
            raise FileNotFoundError(f"{logger} is missing: the Snakemake logger (P1 Task 7)")
        build = ["bash", str(bridges / "nf-spectio" / "build.sh"), str(out)]
        subprocess.run(build, check=True)  # noqa: S603  (fixed argument list, no shell)
        shutil.copytree(logger, out / LOGGER, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
