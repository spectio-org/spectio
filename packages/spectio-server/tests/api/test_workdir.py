"""`GET /tasks/{id}/attempts/{n}/workdir` and its `stat`, `text` and `raw` routes: a Nextflow
attempt's work directory, read only (FU-P3-85e; api §5.3; dev-env §15.3 req. 13, note of
2026-11-08, and req. 14).

The attempt comes from a synthetic `onTaskStart` event (`NfTask`), its work directory written by
hand as Nextflow would leave it: the job's own `.command.*` files, outputs, and staged inputs as
links, copies or hard links.
"""

import os
import shutil
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import update

from spectio.config import Settings
from spectio_server.store.schema import attempts, runs, workflows
from spectio_server.store.writer import Writer

from .. import test_taskfiles
from ..test_taskfiles import Foreign
from . import test_taskfiles_api
from .conftest import client_for
from .test_results import IMG, TEXT_CSP, png
from .test_taskfiles_api import API, RUN, NfTask, problem

nf_task = test_taskfiles_api.nf_task  # the fixtures of the Job files tests
foreign = test_taskfiles.foreign

OTHER_TASK = ("cd", "fedcba9876543210fedcba98765432")  # another task directory of the run
ENV_LINE = "export TOKEN=s3cret\n"


def base(t: NfTask, task_id: str | None = None, n: int = 1) -> str:
    return f"{API}/tasks/{task_id or t.task_id}/attempts/{n}/workdir"


def listing(t: NfTask, path: str | None = None, **kwargs: Any) -> Any:
    params = {} if path is None else {"path": path}
    return t.client.get(base(t), params=params, **kwargs)


def route(t: NfTask, kind: str, rel: str, **kwargs: Any) -> Any:
    return t.client.get(f"{base(t)}/{kind}/{rel}", **kwargs)


def set_attempt(t: NfTask, **values: Any) -> None:
    t.writer.submit(lambda c: c.execute(update(attempts).values(**values))).result()


def set_run(t: NfTask, **values: Any) -> None:
    t.writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == RUN).values(**values))
    ).result()


def ended(t: NfTask) -> None:
    t.task("onTaskComplete", 2, status="COMPLETED", exit="0")


@pytest.fixture
def work(nf_task: NfTask) -> NfTask:
    """The attempt's work directory with its job files, two outputs and a folder."""
    (nf_task.dir / ".command.env").write_text(ENV_LINE)
    (nf_task.dir / ".command.run").write_text(ENV_LINE)
    (nf_task.dir / ".exitcode").write_text("0")
    (nf_task.dir / "counts.tsv").write_text("gene\tn\nA\t3\n")
    (nf_task.dir / "qc").mkdir()
    (nf_task.dir / "qc" / "report.txt").write_text("fine\n")
    (nf_task.dir / "qc" / ".hidden").write_text(ENV_LINE)
    (nf_task.dir / ".cache").mkdir()
    (nf_task.dir / ".cache" / "x.txt").write_text(ENV_LINE)
    return nf_task


# --- Listing ------------------------------------------------------------------------------


def test_req13_workdir_listing(work: NfTask) -> None:
    """One folder, folders first, dot names hidden at every level, no `reports`; `root` is the
    attempt's work directory."""
    found = listing(work)
    assert found.status_code == 200, found.text
    body = found.json()
    assert set(body) == {"root", "path", "exists", "entries", "truncated"}
    assert (body["root"], body["path"], body["exists"], body["truncated"]) == (
        str(work.dir),
        "",
        True,
        False,
    )
    assert [(e["name"], e["type"], e["size"]) for e in body["entries"]] == [
        ("qc", "dir", None),
        ("counts.tsv", "file", 11),
    ]
    inner = listing(work, "qc").json()
    assert inner["path"] == "qc"
    assert [e["name"] for e in inner["entries"]] == ["report.txt"]
    assert found.headers["cross-origin-resource-policy"] == "same-origin"
    assert found.headers["cache-control"] == "no-store"
    problem(listing(work, "none"), 404, "not-found")
    for bad in (".cache", "qc/.hidden", "../x", "/etc", "a//b"):
        problem(listing(work, bad), 422, "file-not-allowed")


def test_req13_workdir_dot_names_refused(work: NfTask) -> None:
    """A name with a part that starts with `.` is refused by `stat`, `text` and `raw`, with
    `?download=true` and `as=image` too: the job files are served only by their own routes."""
    (work.dir / ".plot.png").write_bytes(png(3, 4))
    for rel in (
        ".command.env",
        ".command.run",
        ".exitcode",
        "qc/.hidden",
        ".cache/x.txt",
        ".plot.png",
    ):
        for found in (
            route(work, "stat", rel),
            route(work, "text", rel),
            route(work, "raw", rel),
            route(work, "raw", rel, params={"download": "true"}),
            route(work, "raw", rel, params={"as": "image"}, headers=IMG),
        ):
            problem(found, 422, "file-not-allowed")
            assert "s3cret" not in found.text, rel


def test_req13_workdir_link_to_job_file_refused(work: NfTask) -> None:
    """`x -> .command.env` is listed as `link_outside` and is not read, nor is any link to a
    job file of another task."""
    (work.dir / "x").symlink_to(".command.env")
    other = work.paths.work_dir.joinpath(*OTHER_TASK)
    other.mkdir(parents=True)
    (other / ".command.run").write_text(ENV_LINE)
    (work.dir / "y").symlink_to(other / ".command.run")
    entries = {e["name"]: e["type"] for e in listing(work).json()["entries"]}
    assert entries["x"] == entries["y"] == "link_outside"
    for rel in ("x", "y"):
        assert route(work, "stat", rel).json()["type"] == "link_outside"
        for kind in ("text", "raw"):
            found = route(work, kind, rel)
            problem(found, 422, "file-not-allowed")
            assert "s3cret" not in found.text


def test_req13_workdir_staged_copy_served(work: NfTask, tmp_path: Path) -> None:
    """Staged inputs (req. 13 note of 2026-11-08): a copy, a hard link to a file of the user and
    a link into a task directory of the same run are served like outputs; a link anywhere else
    is `link_outside` and is not read."""
    data = tmp_path / "data"
    data.mkdir()
    (data / "reads.fq").write_text("@r1\nACGT\n")
    shutil.copyfile(data / "reads.fq", work.dir / "copy.fq")
    os.link(data / "reads.fq", work.dir / "hard.fq")
    (work.dir / "away.fq").symlink_to(data / "reads.fq")
    other = work.paths.work_dir.joinpath(*OTHER_TASK)
    other.mkdir(parents=True)
    (other / "aligned.sam").write_text("@HD\n")
    (work.dir / "aligned.sam").symlink_to(other / "aligned.sam")
    entries = {e["name"]: e["type"] for e in listing(work).json()["entries"]}
    assert entries["copy.fq"] == entries["hard.fq"] == entries["aligned.sam"] == "file"
    assert entries["away.fq"] == "link_outside"
    for rel, text in (
        ("copy.fq", "@r1\nACGT\n"),
        ("hard.fq", "@r1\nACGT\n"),
        ("aligned.sam", "@HD\n"),
    ):
        assert route(work, "text", rel).text == text, rel
        assert route(work, "raw", rel).text == text, rel
        assert route(work, "stat", rel).json()["type"] == "file", rel
    for kind in ("text", "raw"):
        problem(route(work, kind, "away.fq"), 422, "file-not-allowed")


def test_req13_workdir_foreign_hard_link_refused(work: NfTask, foreign: Foreign) -> None:
    """A hard link to another user's file is refused by the `fstat` owner check, and hidden from
    the listing (an inode shown as another uid's, so the test runs without root)."""
    (work.dir / "theirs.txt").write_text("someone else's\n")
    foreign.mark(work.dir / "theirs.txt")
    names = [e["name"] for e in listing(work).json()["entries"]]
    assert "theirs.txt" not in names
    for kind in ("text", "raw"):
        problem(route(work, kind, "theirs.txt"), 422, "file-not-allowed")
    problem(route(work, "stat", "theirs.txt"), 404, "not-found")


# --- stat, text and raw -----------------------------------------------------------------------


def test_req13_workdir_stat(work: NfTask) -> None:
    found = route(work, "stat", "qc/report.txt")
    assert found.status_code == 200, found.text
    body = found.json()
    assert body.pop("mtime").endswith("+00:00")
    assert body == {
        "root": str(work.dir),
        "path": "qc/report.txt",
        "name": "report.txt",
        "type": "file",
        "size": 5,
    }
    assert route(work, "stat", "qc").json()["type"] == "dir"
    problem(route(work, "stat", "qc/none.txt"), 404, "not-found")


def test_req13_workdir_text(work: NfTask) -> None:
    """The results text read: the tail, one `Range`, an empty file, `415`, the text headers."""
    found = route(work, "text", "counts.tsv")
    assert found.status_code == 200, found.text
    assert found.text == "gene\tn\nA\t3\n"
    assert found.headers["content-type"] == "text/plain; charset=utf-8"
    assert found.headers["content-security-policy"] == TEXT_CSP
    assert found.headers["cross-origin-resource-policy"] == "same-origin"
    assert found.headers["x-content-type-options"] == "nosniff"
    part = route(work, "text", "counts.tsv", headers={"Range": "bytes=0-3"})
    assert (part.status_code, part.text) == (206, "gene")
    assert part.headers["content-range"] == "bytes 0-3/11"
    (work.dir / "empty.txt").write_text("")
    assert route(work, "text", "empty.txt").content == b""
    (work.dir / "reads.bam").write_bytes(b"BAM\x00" + b"x" * 10)
    problem(route(work, "text", "reads.bam"), 415, "binary-file")
    problem(route(work, "text", "none.txt"), 404, "not-found")
    problem(route(work, "text", "qc"), 422, "file-not-allowed")


def test_req14_workdir_raw(work: NfTask) -> None:
    """The results raw route, except that `.html` and `.htm` are always attachments: a work
    directory has no report viewer. `as=image` serves an image to `<img>`."""
    (work.dir / "page.html").write_text("<script>alert(1)</script>")
    (work.dir / "PAGE.HTM").write_text("<p>x</p>")
    (work.dir / "plot.png").write_bytes(png(3, 4))
    for rel in ("page.html", "PAGE.HTM", "counts.tsv"):
        found = route(work, "raw", rel)
        assert found.status_code == 200, (rel, found.text)
        assert found.headers["content-type"] == "application/octet-stream", rel
        assert found.headers["content-disposition"] == f"attachment; filename*=UTF-8''{rel}"
        assert found.headers["content-security-policy"] == TEXT_CSP, rel
        assert found.headers["vary"] == "Sec-Fetch-Dest"
        assert found.headers["cross-origin-resource-policy"] == "same-origin"
    shown = route(work, "raw", "plot.png", params={"as": "image"}, headers=IMG)
    assert shown.status_code == 200, shown.text
    assert shown.headers["content-type"] == "image/png"
    assert "content-disposition" not in shown.headers
    assert shown.content == png(3, 4)
    problem(
        route(work, "raw", "page.html", params={"as": "image"}, headers=IMG),
        422,
        "file-not-allowed",
    )
    download = route(
        work, "raw", "plot.png", params={"download": "true", "as": "image"}, headers=IMG
    )
    assert download.headers["content-disposition"] == "attachment; filename*=UTF-8''plot.png"
    problem(route(work, "raw", "none.txt"), 404, "not-found")
    problem(route(work, "raw", "qc"), 422, "file-not-allowed")


# --- The attempt and its directory --------------------------------------------------------


def test_req13_workdir_cleaned_410(work: NfTask) -> None:
    """A work directory gone after the attempt ended is `410 log-cleaned` on every route."""
    ended(work)
    shutil.rmtree(work.dir)
    problem(listing(work), 410, "log-cleaned")
    for kind in ("stat", "text", "raw"):
        problem(route(work, kind, "counts.tsv"), 410, "log-cleaned")


def test_workdir_not_visible_yet(nf_task: NfTask) -> None:
    """While the attempt runs, a work directory not there yet (a shared file system) is not a
    cleaned one: the listing says it does not exist, a file is `404`."""
    shutil.rmtree(nf_task.dir)
    found = listing(nf_task)
    assert found.status_code == 200, found.text
    assert (found.json()["exists"], found.json()["entries"]) == (False, [])
    problem(route(nf_task, "stat", "a.txt"), 404, "not-found")
    problem(listing(nf_task, "qc"), 404, "not-found")


def test_workdir_runs_root_unreachable_409(nf_task: NfTask, tmp_path: Path) -> None:
    """FU-P3-81: a work directory recorded under another runs root, or a runs root that is not
    there, is `409 run-dir-unreachable`, not a cleaned directory."""
    other = tmp_path / "other-runs"
    other.mkdir(mode=0o700)
    for runs_root in (other, tmp_path / "missing" / "runs"):
        nf_task.client = client_for(
            nf_task.settings.model_copy(update={"runs_root": runs_root}), nf_task.writer
        )
        problem(listing(nf_task), 409, "run-dir-unreachable")
        for kind in ("stat", "text", "raw"):
            problem(route(nf_task, kind, "a.txt"), 409, "run-dir-unreachable")


def test_workdir_not_found(nf_task: NfTask) -> None:
    """`404 not-found` for an unknown attempt, a Snakemake attempt, a Nextflow attempt with no
    recorded work directory, and an attempt of a run started from a terminal."""
    (nf_task.dir / "a.txt").write_text("a\n")
    for url in (base(nf_task, n=9), base(nf_task, "tsk_nope")):
        problem(nf_task.client.get(url), 404, "not-found")
        problem(nf_task.client.get(f"{url}/stat/a.txt"), 404, "not-found")
    smk = {"engine": "snakemake"}
    nf_task.writer.submit(lambda c: c.execute(update(workflows).values(**smk))).result()
    for found in (listing(nf_task), route(nf_task, "text", "a.txt")):
        problem(found, 404, "not-found")
    nf_task.writer.submit(lambda c: c.execute(update(workflows).values(engine="nextflow"))).result()
    set_run(nf_task, origin="cli-observed")
    for found in (
        listing(nf_task),
        route(nf_task, "text", "a.txt"),
        route(nf_task, "raw", "a.txt"),
    ):
        problem(found, 404, "not-found")
    set_run(nf_task, origin="ui")
    assert route(nf_task, "text", "a.txt").text == "a\n"
    set_attempt(nf_task, work_dir=None)
    for found in (
        listing(nf_task),
        route(nf_task, "stat", "a.txt"),
        route(nf_task, "raw", "a.txt"),
    ):
        problem(found, 404, "not-found")


# --- Session and cross-site requests ------------------------------------------------------


def routes_of(t: NfTask) -> list[str]:
    return [base(t), f"{base(t)}/stat/a.txt", f"{base(t)}/text/a.txt", f"{base(t)}/raw/a.txt"]


def test_req2_workdir_routes_need_session(
    nf_task: NfTask, settings: Settings, writer: Writer
) -> None:
    (nf_task.dir / "a.txt").write_text("a\n")
    anon = client_for(settings, writer, signed_in=False)
    for url in routes_of(nf_task):
        problem(anon.get(url), 401, "unauthenticated")


@pytest.mark.parametrize("site", ["same-site", "cross-site"])
def test_req7_workdir_routes_same_site_403(nf_task: NfTask, site: str) -> None:
    (nf_task.dir / "a.txt").write_text("a\n")
    for url in routes_of(nf_task):
        found = nf_task.client.get(url, headers={"Sec-Fetch-Site": site})
        assert found.status_code == 403, (url, found.text)
