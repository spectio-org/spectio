"""`spectio.loginshell.which` (inbox #161 follow-up): the login shell's PATH, never a function."""

import shlex
from pathlib import Path

from spectio.loginshell import which


def test_which_finds_the_binary_behind_a_shell_function(home: Path) -> None:
    """`conda init` makes `conda` a shell function in every login shell; the binary is still on
    PATH and is what Snakemake calls, so it is found, not reported missing."""
    bin_dir = home / "bin"
    bin_dir.mkdir()
    tool = bin_dir / "conda"
    tool.write_text("#!/bin/sh\necho conda 25.1.0\n")
    tool.chmod(0o755)
    with (home / ".bash_profile").open("a") as f:
        f.write(f"export PATH={shlex.quote(str(bin_dir))}:$PATH\nconda() {{ :; }}\n")
    assert which("conda", "absent-tool") == {"conda": str(tool), "absent-tool": None}
