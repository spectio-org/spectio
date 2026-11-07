"""The `spectio` command (cli-and-shared-libraries.md §2)."""

from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import typer

from spectio.cli.doctor import run_doctor
from spectio.cli.init import run_init
from spectio.cli.login import run_login
from spectio.cli.open import run_open
from spectio.cli.serve import run_serve
from spectio.config import Settings

app = typer.Typer(no_args_is_help=True, add_completion=False)

Opt = typer.Option


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"spectio {version('spectio')}")
        raise typer.Exit


@app.callback()
def main(
    _version: Annotated[
        bool | None,
        Opt("--version", callback=_print_version, is_eager=True, help="Print the version"),
    ] = None,
) -> None:
    """Spectio: launch and monitor Nextflow and Snakemake runs."""


@app.command()
def init(
    data_dir: Annotated[Path | None, Opt(help="Default ~/.spectio")] = None,
    db_dir: Annotated[Path | None, Opt(help="Node-local; default $TMPDIR/spectio-<uid>")] = None,
    runs_root: Annotated[Path | None, Opt(help="Shared; default ~/spectio-runs")] = None,
    port: Annotated[int | None, Opt(help="Default 8080, or a free port")] = None,
    local: Annotated[bool, Opt("--local", help="One Linux machine, no scheduler")] = False,
    partition: Annotated[str | None, Opt(help="SLURM partition of the engines' jobs")] = None,
    account: Annotated[str | None, Opt(help="SLURM account of the engines' jobs")] = None,
    nextflow: Annotated[str | None, Opt(help="Command that runs Nextflow")] = None,
    snakemake: Annotated[str | None, Opt(help="Command that runs Snakemake")] = None,
) -> None:
    """Create the data directory, spectio.toml, project "default" and its environment."""
    raise typer.Exit(
        run_init(
            local,
            data_dir=data_dir,
            db_dir=db_dir,
            runs_root=runs_root,
            port=port,
            partition=partition,
            account=account,
            nextflow=nextflow,
            snakemake=snakemake,
        )
    )


@app.command()
def doctor() -> None:
    """Check this machine for Spectio: one ok, warn or fail line per check."""
    try:
        settings = Settings()
    except ValueError as exc:  # a bad spectio.toml or SPECTIO_* value
        typer.echo(f"fail config {exc}")
        raise typer.Exit(1) from exc
    raise typer.Exit(run_doctor(settings))


@app.command()
def serve(
    force: Annotated[
        bool, Opt("--force", help="Start even if server.json names a server on another node")
    ] = False,
) -> None:
    """Start the server on 127.0.0.1, at the port spectio init recorded."""
    raise typer.Exit(run_serve(force))


@app.command()
def login(
    print_link: Annotated[
        bool, Opt("--print-link", help="Print a new link to the server of this node")
    ] = False,
    as_json: Annotated[bool, Opt("--json", help="One line for spectio open: the ticket")] = False,
) -> None:
    """Get a new single-use token link from the running server (valid 15 minutes)."""
    raise typer.Exit(run_login(print_link, as_json))


@app.command("open")
def open_(
    host: Annotated[str, typer.Argument(help="The cluster, as ssh names it")],
    node: Annotated[
        str | None, Opt(help="Login node for a first start; overrides server.json")
    ] = None,
    remote_cmd: Annotated[
        str | None, Opt(help="Shell text that runs spectio there, e.g. a full path")
    ] = None,
    local_port: Annotated[
        int | None, Opt(help="Laptop end of the tunnel; default a free port")
    ] = None,
    no_browser: Annotated[bool, Opt("--no-browser", help="Print the link only")] = False,
) -> None:
    """On the laptop: open your server on a cluster login node, through an SSH tunnel."""
    raise typer.Exit(run_open(host, node, remote_cmd, local_port, not no_browser))
