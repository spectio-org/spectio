"""Demo-data hygiene for the media scripts (see fixtures.yaml and documentation-system.md §5.5)."""

from __future__ import annotations

import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIXTURES = yaml.safe_load((HERE / "fixtures.yaml").read_text())


def sanitise(text: str) -> str:
    for pat, repl in FIXTURES["substitutions"]:
        text = re.sub(pat, repl, text)
    return text


def leaks(text: str) -> list[str]:
    """Forbidden patterns found in `text` (the visible page text or a cast)."""
    found = []
    for pat in FIXTURES["forbidden"]:
        m = re.search(pat, text)
        if m:
            found.append(f"{pat!r} -> {m.group(0)!r}")
    return found


@contextmanager
def sanitised_boards(boards: Path):
    """Sanitised copy of every board, in a sibling directory of the same depth.

    render.js resolves logos relative to `<dir>/../..` and loads the shared
    components from the board's own directory, so the copy keeps both: a
    sibling of design/ui-canvas, with all *.dc.html sanitised. Deleted on exit.
    """
    tmp = Path(tempfile.mkdtemp(prefix=".media-tmp-", dir=boards.parent))
    try:
        for f in boards.iterdir():
            if f.suffix == ".html" or f.name.endswith(".dc.html"):
                (tmp / f.name).write_text(sanitise(f.read_text(encoding="utf-8")), encoding="utf-8")
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
