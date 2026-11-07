"""`spectio --version` (P1 Task 21: tests/packaging/test_wheel.sh checks it on the wheel)."""

from importlib.metadata import version

from typer.testing import CliRunner

from spectio.cli.main import app


def test_version() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"spectio {version('spectio')}\n"
