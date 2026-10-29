"""The runner imports statically, so that lint-imports sees every import (SEC-P3T1-06).

ruff's banned-api (TID251) refuses `importlib.import_module`; it does not resolve the builtin
`__import__`, so this test refuses that one.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def test_no_dunder_import() -> None:
    # `__import__(...)`, and `builtins.__import__` or `importlib.__import__` as attributes.
    files = sorted(SRC.rglob("*.py"))
    assert files
    found = [
        f"{path.relative_to(SRC)}:{node.lineno}"
        for path in files
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if (isinstance(node, ast.Name) and node.id == "__import__")
        or (isinstance(node, ast.Attribute) and node.attr == "__import__")
    ]
    assert not found, f"__import__ in the runner: {found}"
