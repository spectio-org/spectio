"""`python -m spectio`: how `spectio serve --detach` starts its pane, with `python -P` (no script
directory or working directory on `sys.path`)."""

from spectio.cli.main import app

if __name__ == "__main__":
    app(prog_name="spectio")
