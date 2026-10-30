"""The `spectio` command (cli-and-shared-libraries.md §2)."""

from pathlib import Path
from typing import Annotated

import typer

from spectio.cli.doctor import run_doctor
from spectio.cli.init import run_init
from spectio.config import Settings

app = typer.Typer(no_args_is_help=True, add_completion=False)

Opt = typer.Option


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
