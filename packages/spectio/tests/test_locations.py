"""The shared location checks (`spectio.locations`, api §5.6, SEC-PRE-FU87-02): every refusal is
a ValueError whose message never quotes the value (SEC-P3FU87A-01)."""

from collections.abc import Callable

import pytest

from spectio import locations

SECRET = "SECRET"  # noqa: S105 - a marker, not a password
FULLWIDTH_AT = chr(0xFF20)  # NFKC turns it into "@"
CHECKS: list[tuple[Callable[[str], object], str]] = [
    (locations.git_url, f"https://u:SECRET{FULLWIDTH_AT}host/r"),  # urlsplit: NFKC netloc error
    (locations.git_url, "https://[SECRET]/r"),  # not an IPv6 address
    (locations.git_url, "https://SECRET.example:99999/r"),  # a port out of range
    (locations.git_url, "https://u:SECRET@host/r"),
    (locations.git_url, "ftp://SECRET/r"),
    (locations.check_location, "https://[SECRET]/r"),
    (locations.check_location, "SECRET‮"),
    (locations.check_revision, "-SECRET"),
    (locations.check_params_file, "SECRET.txt"),
]


@pytest.mark.parametrize(("check", "value"), CHECKS)
def test_refusal_message_never_quotes_the_value(check: Callable[[str], object], value: str) -> None:
    with pytest.raises(ValueError) as caught:
        check(value)
    assert SECRET not in str(caught.value)


# --- The extra config file of a launch (FU-P3-110a, api §5.7) ---------------------------------

TMP, SHM = "/tmp", "/dev/shm"  # noqa: S108 - the refused places themselves
ROOTS = ["/home/u", "/nfs/home/u", f"{TMP}/pipe"]


@pytest.mark.parametrize(
    ("value", "engine", "found"),
    [
        ("/home/u/extra.config", "nextflow", ("/home/u", ("extra.config",))),
        ("/nfs/home/u/conf/x.config", "nextflow", ("/nfs/home/u", ("conf", "x.config"))),
        (f"{TMP}/pipe/conf/extra.yaml", "snakemake", (f"{TMP}/pipe", ("conf", "extra.yaml"))),
        (f"{TMP}/pipe/extra.yml", "snakemake", (f"{TMP}/pipe", ("extra.yml",))),
        (f"{TMP}/pipe/extra.json", "snakemake", (f"{TMP}/pipe", ("extra.json",))),
        ("/home/u/" + "/".join(["d"] * 31) + "/x.config", "nextflow", None),  # 32 parts
    ],
)
def test_req20_config_file_accepted(
    value: str, engine: str, found: tuple[str, tuple[str, ...]] | None
) -> None:
    root, parts = locations.check_config_file(value, ROOTS, engine)
    if found is not None:
        assert (root, parts) == found
    assert len(parts) <= 32


def test_req20_config_file_longest_root_wins() -> None:
    root, parts = locations.check_config_file(
        "/home/u/p/x.config", ["/home/u", "/home/u/p"], "nextflow"
    )
    assert (root, parts) == ("/home/u/p", ("x.config",))


@pytest.mark.parametrize(
    ("value", "engine", "why"),
    [
        ("extra.config", "nextflow", "absolute"),
        ("home/u/extra.config", "nextflow", "absolute"),
        ("/home/u/../v/extra.config", "nextflow", "plain names"),
        ("/home/u/./extra.config", "nextflow", "plain names"),
        ("/home/u//extra.config", "nextflow", "plain names"),
        ("/home/u/conf/", "nextflow", "plain names"),
        ("/home/u/ex\ttra.config", "nextflow", "control"),
        ("/home/u/ex‮tra.config", "nextflow", "control"),
        ("/home/u/extra.yaml", "nextflow", ".config"),
        ("/home/u/extra.config", "snakemake", ".yaml"),
        (f"{TMP}/x.config", "nextflow", "home directory or in the pipeline"),
        (f"{SHM}/x.config", "nextflow", "home directory or in the pipeline"),
        ("/home/v/x.config", "nextflow", "home directory or in the pipeline"),
        ("/home/uu/x.config", "nextflow", "home directory or in the pipeline"),
        ("/home/u", "nextflow", "home directory or in the pipeline"),
        ("/home/u/" + "/".join(["d"] * 32) + "/x.config", "nextflow", "1 to 32"),
        ("/home/u/" + "a" * 4096 + ".config", "nextflow", "longer"),
    ],
)
def test_req20_config_file_refused(value: str, engine: str, why: str) -> None:
    with pytest.raises(ValueError, match=why):
        locations.check_config_file(value, ROOTS, engine)


def test_req20_config_file_refusal_never_quotes_the_value() -> None:
    for value in ("/home/u/SECRET.txt", "/elsewhere/SECRET.config", "/home/u/../SECRET.config"):
        with pytest.raises(ValueError) as caught:
            locations.check_config_file(value, ROOTS, "nextflow")
        assert SECRET not in str(caught.value)
