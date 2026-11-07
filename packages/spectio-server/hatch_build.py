"""Put the built screens in the package as `spectio_server/web/` (P1 Task 21, architecture §7.3).

From a checkout, `web/dist` must be built first (`npm --prefix web ci --ignore-scripts && npm
--prefix web run build`); the sdist carries it under `src/spectio_server/web/`, so no install
path needs Node. `uv build` makes every wheel from its sdist, and an sdist without the screens
fails. A wheel built straight from a checkout goes without them, with a warning; an editable
install serves `web/dist` of the checkout (`static.DIST`).
"""

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

PACKAGED = "src/spectio_server/web"  # where the sdist carries it, and the wheel's `spectio_server/`


class WebHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        root = Path(self.root)
        if version == "editable" or (root / PACKAGED).is_dir():  # an sdist that carries it
            return
        dist = root.parents[1] / "web" / "dist"
        if not (dist / "index.html").is_file():
            missing = (
                f"{dist} is not built: run `npm --prefix web ci --ignore-scripts` "
                "and `npm --prefix web run build` first"
            )
            if self.target_name == "sdist":
                raise FileNotFoundError(missing)
            self.app.display_warning(f"spectio-server: this wheel carries no screens: {missing}")
            return
        dest = PACKAGED if self.target_name == "sdist" else "spectio_server/web"
        build_data["force_include"][str(dist)] = dest
