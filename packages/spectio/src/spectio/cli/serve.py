"""`spectio serve` (P1 Task 11): the server on 127.0.0.1, in the foreground.

`--detach` (a tmux session `spectio-server`) comes with the tmux launcher of P1 Task 10. There
is no `--host` flag: 0.0.1 listens on 127.0.0.1 only (dev-env §15.3 req. 1).
"""

import logging

import typer

from spectio.config import Settings


def run_serve(force: bool) -> int:
    try:
        settings = Settings()
    except ValueError as exc:  # a bad spectio.toml or SPECTIO_* value
        typer.echo(f"spectio serve: {exc}", err=True)
        return 2
    try:
        from spectio_server.serve import ServeError, serve  # the server (architecture §6)
    except ImportError:
        typer.echo(
            "spectio serve: the server package is missing: install spectio[server]", err=True
        )
        return 2
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        serve(settings, force=force)
    except ServeError as exc:
        typer.echo(f"spectio serve: {exc}", err=True)
        return 2
    return 0
