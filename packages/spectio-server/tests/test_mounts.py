"""The paths a Snakemake launch's containers would not see (built 2026-11-25).

A launch reads its parameters and the environment's Apptainer options only: no container is
started and no path is stat'd. The pure functions here take the visible roots as values, so the
tests need no cluster and no Apptainer.
"""

from pathlib import Path

import pytest

from spectio_server import mounts


def unmounted(params: object, apptainer_args: str = "", **values: object) -> list[str]:
    """`mounts.unmounted_paths` with this machine's home and a fixed launch directory, unless
    a test gives its own."""
    found = {
        "home": Path("/home/someone"),
        "launch_dir": Path("/runs/run_1/launch"),
        "site_binds": [],
        "env_binds": "",
    }
    found.update(values)
    return mounts.unmounted_paths(params, apptainer_args, **found)


# --- The candidates --------------------------------------------------------------------------


def test_nested_params_are_walked() -> None:
    params = {
        "samples": "/shared/scratch/samples.csv",
        "options": {"reference": "/shared/ref/genome.fa", "threads": 4},
        "runs": [{"bam": "/shared/scratch/a.bam"}, "relative/name.txt", None],
    }
    assert unmounted(params) == [
        "/shared/ref/genome.fa",
        "/shared/scratch/a.bam",
        "/shared/scratch/samples.csv",
    ]


def test_only_absolute_paths_without_control_characters() -> None:
    params = {
        "url": "https://example.org/data.csv",
        "relative": "data/samples.csv",
        "control": "/shared/scratch/a\x00b",
        "newline": "/shared/scratch/a\nb",
        "number": 3,
        "flag": True,
        "nothing": None,
        "path": "/shared/scratch/ok.csv",
    }
    assert unmounted(params) == ["/shared/scratch/ok.csv"]


def test_paths_are_normalised_and_unique() -> None:
    params = {"a": "/shared//scratch/./x.csv", "b": "/shared/scratch/x.csv"}
    assert unmounted(params) == ["/shared/scratch/x.csv"]


def test_at_most_ten_thousand_values_are_read() -> None:
    params = {"paths": [f"/shared/scratch/{i}" for i in range(10_001)]}
    assert len(unmounted(params)) == 10_000


def test_nesting_past_thirty_two_levels_is_not_read() -> None:
    def nest(levels: int) -> dict[str, object]:
        node: dict[str, object] = {"leaf": "/shared/scratch/deep.csv"}
        for _ in range(levels - 1):
            node = {"next": node}
        return node

    assert unmounted(nest(32)) == ["/shared/scratch/deep.csv"]
    assert unmounted(nest(33)) == []


# --- The visible roots -----------------------------------------------------------------------


def test_home_tmp_launch_dir_and_the_apptainer_arguments() -> None:
    params = {
        "in_home": "/home/someone/data.csv",
        "in_tmp": "/tmp/spectio/data.csv",  # noqa: S108 - a root the check itself covers
        "in_launch": "/runs/run_1/launch/results/x.txt",
        "bound": "/data/reads.csv",
        "at_dst": "/ref/genome.fa",
        "unbound": "/shared/scratch/x.csv",
    }
    args = "--nvc --bind /data,/shared/ref.fa:/ref --bind=/etc"
    assert unmounted(params, args) == ["/shared/scratch/x.csv"]


def test_paths_in_the_image_or_mounted_by_apptainer_itself_are_never_refused() -> None:
    params = {"a": "/dev/null", "b": "/opt/conda/x", "c": "/usr/share/x", "d": "/etc/passwd"}
    assert unmounted(params) == []


def test_a_bound_destination_is_the_root() -> None:
    """A bind mounts `src` at `dst`, so the container sees the files at `dst` (CR-02): `/ref`
    is the root, and `/shared/ref` is not — unless the second field is only an option."""
    params = {"at_dst": "/ref/genome.fa", "at_src": "/shared/ref/genome.fa"}
    assert unmounted(params, "-B /shared/ref:/ref") == ["/shared/ref/genome.fa"]
    assert unmounted(params, "-B /shared/ref:/ref:ro") == ["/shared/ref/genome.fa"]


def test_a_bare_option_is_not_a_destination() -> None:
    params = {"ro": "/shared/ref/x.fa", "rw": "/other/y.fa"}
    assert unmounted(params, "-B /shared/ref:ro,/other:rw") == []


def test_a_root_matches_by_path_component() -> None:
    params = {"other": "/scratchy/x.csv", "itself": "/scratch", "under": "/scratch/x.csv"}
    assert unmounted(params, "-B /scratch") == ["/scratchy/x.csv"]


def test_a_root_covers_everything() -> None:
    assert unmounted({"x": "/shared/scratch/x.csv"}, "-B /") == []


def test_site_and_environment_binds_are_roots() -> None:
    params = {"a": "/shared/scratch/x.csv", "b": "/mnt/data/reads.csv", "c": "/work/out.txt"}
    found = unmounted(params, site_binds=["/data:/mnt/data"], env_binds="/work")
    assert found == ["/shared/scratch/x.csv"]


def test_site_and_environment_bind_lists_split_on_commas() -> None:
    params = {"a": "/data/reads.csv", "b": "/work/out.txt", "c": "/other/x"}
    found = unmounted(params, site_binds=["/data,/work:/mnt/work"])
    assert found == ["/other/x", "/work/out.txt"]


def test_extra_roots_reach_the_check_by_value() -> None:
    """The pipeline's directory is a root of its own (CR-05): never parsed as a bind, so a
    comma or a colon in it splits nothing."""
    params = {"in": "/work/a,b/ref.fa", "out": "/shared/scratch/x.csv"}
    found = unmounted(params, extra_roots=["/work/a,b"])
    assert found == ["/shared/scratch/x.csv"]


# --- The suggestion --------------------------------------------------------------------------


def test_suggested_binds_names_the_first_component() -> None:
    paths = ["/shared/scratch/a.csv", "/data/b/c.fa", "/data/d", "/scratch"]
    assert mounts.suggested_binds(paths) == ["/data", "/scratch", "/shared"]


def test_only_plain_paths_are_echoed() -> None:
    """The refusal names and suggests a path it can echo safely (SEC-mounts-01): absolute, one
    line, no space, nothing a terminal would read as two words or an option."""
    paths = ["/shared/scratch/a.csv", "/x --writable-tmpfs/y", "/quo'te", "/uni\\x", "a/b"]
    assert mounts.echoed_paths(paths) == ["/shared/scratch/a.csv"]


# --- The site's Apptainer configuration ------------------------------------------------------


def test_site_bind_paths_reads_bind_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    conf = tmp_path / "apptainer.conf"
    conf.write_text(
        "# bind path = /commented\n"
        "bind path = /shared/scratch\n"
        "bind path = /data:/mnt/data\n"
        "\n"
        "mount hostfs = no\n"
        "bind path = \n"
    )
    other = tmp_path / "singularity.conf"
    other.write_text("bind path = /never\n")
    monkeypatch.setattr(mounts, "CONFIG_FILES", (conf, other))
    assert mounts.site_bind_paths() == ["/shared/scratch", "/data:/mnt/data"]


def test_site_bind_paths_reads_the_first_readable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing.conf"
    other = tmp_path / "singularity.conf"
    other.write_text("bind path = /data\n")
    monkeypatch.setattr(mounts, "CONFIG_FILES", (missing, other))
    assert mounts.site_bind_paths() == ["/data"]
    monkeypatch.setattr(mounts, "CONFIG_FILES", (missing, tmp_path / "also-missing.conf"))
    assert mounts.site_bind_paths() == []


def test_site_bind_paths_reads_at_most_256_kib(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conf = tmp_path / "apptainer.conf"
    conf.write_text("#" * (256 * 1024) + "\nbind path = /late\n")
    monkeypatch.setattr(mounts, "CONFIG_FILES", (conf,))
    assert mounts.site_bind_paths() == []


def test_site_bind_paths_drops_the_line_the_cap_cuts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read stops at MAX_CONF_BYTES; the last line it holds may be cut in half, so it is
    dropped: a `bind path` past the cap is never read as a broken value (SEC-mounts-02)."""
    conf = tmp_path / "apptainer.conf"
    cut = "bind path = /cut"
    pad = "#" * (256 * 1024 - len("bind path = /whole\n") - len(cut))
    conf.write_text(f"bind path = /whole\n{cut}{pad}\nbind path = /never\n")
    monkeypatch.setattr(mounts, "CONFIG_FILES", (conf,))
    assert mounts.site_bind_paths() == ["/whole"]


def test_site_bind_paths_reads_only_a_regular_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory in the list is not read: the next file decides (SEC-mounts-02)."""
    directory = tmp_path / "conf.d"
    directory.mkdir()
    other = tmp_path / "singularity.conf"
    other.write_text("bind path = /data\n")
    monkeypatch.setattr(mounts, "CONFIG_FILES", (directory, other))
    assert mounts.site_bind_paths() == ["/data"]


def test_env_binds_prefers_apptainer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APPTAINER_BIND", "/data")
    monkeypatch.setenv("SINGULARITY_BIND", "/never")
    assert mounts.env_binds() == "/data"
    monkeypatch.delenv("APPTAINER_BIND")
    assert mounts.env_binds() == "/never"
    monkeypatch.delenv("SINGULARITY_BIND")
    assert mounts.env_binds() == ""
