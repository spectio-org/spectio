"""spectio-open: name-holding release; the real package is built at https://github.com/weber8thomas/spectio."""

import sys
from importlib.metadata import version

NOTICE = (
    "Spectio Open, the open edition of Spectio, launches, monitors and steers Nextflow and Snakemake runs.\n"
    "This spectio-open release only holds the name on PyPI; the first real version is being built.\n"
    "Source and progress: https://github.com/weber8thomas/spectio"
)


def main() -> None:
    if sys.argv[1:] in (["--version"], ["-V"]):
        print(version("spectio-open"))
    else:
        print(NOTICE)
