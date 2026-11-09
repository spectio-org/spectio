"""`GET /runs/{id}/results` and `GET /runs/{id}/results/raw/{path}` (P1 Task 31; api §5 note of
2026-10-28, Results; dev-env §15.3 req. 13 and 14), `runs.results_dir` at launch, and the cap
on follow streams of files (req. 14).

The results directory is written by hand under the run's launch directory, as a pipeline's
`publishDir` would; a published symlink points into a task directory of the run's work
directory.
"""

import asyncio
import errno
import os
import struct
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from spectio.config import Settings
from spectio.runner.rundir import RunPaths, make_run_dirs, run_paths
from spectio_server.api import logs as api_logs
from spectio_server.api import results as api_results
from spectio_server.files import results as files_results
from spectio_server.store.schema import runs
from spectio_server.store.writer import Writer

from .conftest import add_run, client_for

RUN = "run_01K8T2F1XTVRES0000000000R1"
API = "/api/v1"
HASH = ("ab", "0123456789abcdef0123456789abcd")
REPORT_CSP = (
    "sandbox allow-scripts allow-downloads; default-src 'none'; "
    "script-src 'unsafe-inline' 'unsafe-eval'; style-src 'unsafe-inline'; "
    "img-src data: blob:; font-src data:; connect-src 'none'; form-action 'none'; "
    "frame-ancestors 'self'"
)


@dataclass
class Results:
    run_id: str
    paths: RunPaths
    root: Path  # the results directory, not created yet
    task_dir: Path  # one task's work directory

    def write(self, rel: str, text: str = "x") -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path


def set_run(writer: Writer, run_id: str, **values: Any) -> None:
    writer.submit(
        lambda c: c.execute(update(runs).where(runs.c.id == run_id).values(**values))
    ).result()


@pytest.fixture
def results(settings: Settings, writer: Writer) -> Results:
    """A Nextflow run whose results directory is `<launch dir>/results`, still missing."""
    paths = make_run_dirs(settings.runs_root, RUN)
    root = paths.launch_dir / "results"
    add_run(writer, settings, RUN, "rnaseq", "running", results_dir=str(root))
    task_dir = paths.work_dir.joinpath(*HASH)
    task_dir.mkdir(parents=True)
    return Results(RUN, paths, root, task_dir)


def listing(client: TestClient, path: str | None = None, run_id: str = RUN) -> Any:
    params = {} if path is None else {"path": path}
    return client.get(f"{API}/runs/{run_id}/results", params=params)


def raw(client: TestClient, rel: str, run_id: str = RUN, **params: Any) -> Any:
    return client.get(f"{API}/runs/{run_id}/results/raw/{rel}", params=params)


def text(client: TestClient, rel: str, run_id: str = RUN, **kwargs: Any) -> Any:
    return client.get(f"{API}/runs/{run_id}/results/text/{rel}", **kwargs)


def stat_of(client: TestClient, rel: str, run_id: str = RUN) -> Any:
    return client.get(f"{API}/runs/{run_id}/results/stat/{rel}")


def problem(response: Any, status: int, slug: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["type"] == f"/problems/{slug}"


MIB = 1048576
TEXT_CSP = "sandbox; default-src 'none'"


# --- Listing ------------------------------------------------------------------------------


def test_results_listing(authed_client: TestClient, results: Results) -> None:
    before = listing(authed_client)
    assert before.status_code == 200, before.text
    assert before.json() == {
        "root": str(results.root),
        "path": "",
        "exists": False,
        "entries": [],
        "truncated": False,
        "reports": [],
    }
    results.write("b.txt", "bee\n")
    results.write("a.tsv", "a\tb\n")
    results.write("multiqc/x/deep.txt")
    (results.root / "fastqc").mkdir()
    found = listing(authed_client).json()
    assert found["exists"] is True and found["truncated"] is False
    assert [(e["name"], e["type"], e["size"]) for e in found["entries"]] == [
        ("fastqc", "dir", None),
        ("multiqc", "dir", None),
        ("a.tsv", "file", 4),
        ("b.txt", "file", 4),
    ]
    assert all(e["mtime"] and e["mtime"].endswith("+00:00") for e in found["entries"])
    inner = listing(authed_client, "multiqc").json()
    assert inner["path"] == "multiqc"
    assert [e["name"] for e in inner["entries"]] == ["x"]  # one level: no recursion
    assert listing(authed_client, "nothing/here").status_code == 404


def test_req14_scandir_cap(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5,000 entries: 1000 read and listed, `truncated`, and `scandir` stopped there."""
    big = results.root / "many"
    big.mkdir(parents=True)
    for i in range(5000):
        (big / f"f{i:04d}.txt").touch()
    read: list[int] = []  # entries read, per scandir: the listing's, then the search's
    real = os.scandir

    class Counting:
        def __init__(self, fd: Any) -> None:
            self.it, self.n = real(fd), len(read)
            read.append(0)

        def __enter__(self) -> "Counting":
            return self

        def __exit__(self, *exc: object) -> None:
            self.it.close()

        def __iter__(self) -> "Counting":
            return self

        def __next__(self) -> Any:
            entry = next(self.it)
            read[self.n] += 1
            return entry

    monkeypatch.setattr(os, "scandir", Counting)  # the walk's `os.scandir`
    found = listing(authed_client, "many").json()
    assert len(found["entries"]) == 1000 and found["truncated"] is True
    assert read[0] == 1001  # the cap, and one more to know it is truncated


# --- Reports --------------------------------------------------------------------------------


def test_results_reports(authed_client: TestClient, results: Results) -> None:
    for rel in (
        "pipeline_info/execution_report.html",
        "fastqc/S2_fastqc.html",
        "fastqc/S1_fastqc.html",
        "multiqc/star_salmon/multiqc_report.html",
        "page.htm",
        "a/b/c/four.html",  # depth 4: found
        "a/b/c/d/five.html",  # depth 5: not looked for
        "notes.txt",
        "plot.svg",
        "page.xhtml",
    ):
        results.write(rel)
    reports = listing(authed_client).json()["reports"]
    assert [r["path"] for r in reports] == [
        "multiqc/star_salmon/multiqc_report.html",
        "a/b/c/four.html",
        "fastqc/S1_fastqc.html",
        "fastqc/S2_fastqc.html",
        "page.htm",
        "pipeline_info/execution_report.html",
    ]
    by_path = {r["path"]: r for r in reports}
    assert by_path["fastqc/S1_fastqc.html"]["group"] == "fastqc"
    assert by_path["fastqc/S2_fastqc.html"]["group"] == "fastqc"
    assert by_path["page.htm"]["group"] is None
    assert by_path["fastqc/S1_fastqc.html"]["title"] == "S1_fastqc"
    assert by_path["multiqc/star_salmon/multiqc_report.html"]["title"] == "MultiQC report"
    for i in range(60):
        results.write(f"more/r{i:02d}.html")
    capped = listing(authed_client).json()["reports"]
    assert len(capped) == 50
    assert capped[0]["path"] == "multiqc/star_salmon/multiqc_report.html"  # CR-P3T31-01


def test_results_reports_multiqc_kept_past_the_cap(
    authed_client: TestClient, results: Results
) -> None:
    """MultiQC's report is kept when 50 others come before it, breadth first (CR-P3T31-01)."""
    for i in range(60):
        results.write(f"fastqc/S{i:02d}_fastqc.html")
    results.write("multiqc/star_salmon/multiqc_report.html")
    reports = listing(authed_client).json()["reports"]
    assert len(reports) == 50
    assert reports[0]["path"] == "multiqc/star_salmon/multiqc_report.html"


def test_req14_report_search_caps(
    authed_client: TestClient,
    results: Results,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The search stops after 10,000 entries visited or 5 s, and is kept once the run ended."""
    assert files_results.SEARCH_ENTRIES == 10_000 and files_results.SEARCH_S == 5.0
    for i in range(30):
        results.write(f"f{i:02d}.txt")
    results.write("z/late.html")  # below the root: visited after its 31 entries
    monkeypatch.setattr(files_results, "SEARCH_ENTRIES", 20)
    assert listing(authed_client).json()["reports"] == []
    monkeypatch.setattr(files_results, "SEARCH_ENTRIES", 10_000)
    assert [r["path"] for r in listing(authed_client).json()["reports"]] == ["z/late.html"]

    clock = iter(range(0, 1000, 10))  # each look at the clock: 10 s later
    monkeypatch.setattr(files_results, "clock", lambda: next(clock))
    assert listing(authed_client).json()["reports"] == []
    monkeypatch.undo()

    results.write("z/second.html")  # running: searched again on each listing
    assert len(listing(authed_client).json()["reports"]) == 2
    set_run(writer, RUN, state="succeeded")
    assert len(listing(authed_client).json()["reports"]) == 2  # searched, then kept
    results.write("z/third.html")
    assert len(listing(authed_client).json()["reports"]) == 2  # the kept result


def test_req13_results_odd_names(
    authed_client: TestClient, results: Results, writer: Writer
) -> None:
    """A name that is not UTF-8, or holds a control, format or bidi character, is neither
    listed nor reported, and the raw route refuses it alike (SEC-P3T31-04)."""
    results.write("ok.html")
    odd = [b"bad\xff.html", b"e\x1b[31m.html", "x\u202e.html".encode()]
    (results.root / "sub").mkdir()
    for name in odd:
        for folder in (bytes(results.root), bytes(results.root / "sub")):
            with open(os.path.join(folder, name), "w") as f:
                f.write("x")
    set_run(writer, RUN, state="succeeded")  # the search is kept: it must not keep a bad name
    for _ in range(2):
        found = listing(authed_client)
        assert found.status_code == 200, found.text
        assert [e["name"] for e in found.json()["entries"]] == ["sub", "ok.html"]
        assert [r["path"] for r in found.json()["reports"]] == ["ok.html"]
    assert listing(authed_client, "sub").json()["entries"] == []
    for bad in ("e\x1b[31m.html", "x\u202e.html", "a\x85b", "a\u2066b"):
        assert raw(authed_client, quote(bad)).status_code == 422, bad


# --- Confined -------------------------------------------------------------------------------


def test_req13_results_confined(
    authed_client: TestClient, results: Results, settings: Settings
) -> None:
    results.write("ok.txt", "fine\n")
    for bad in ("../launch", "/etc", "a/../b", "a\x00b", ".", "a//b"):
        found = listing(authed_client, bad)
        assert found.status_code == 422, (bad, found.text)
    for bad in ("%2e%2e/%2e%2e/x", "a/%2e%2e/b", "%00"):
        assert raw(authed_client, bad).status_code in (404, 422), bad
    home = Path(os.environ["HOME"])
    (results.root / "home").symlink_to(home)
    (results.root / "rc").symlink_to(home / ".bashrc")
    (home / ".bashrc").write_text("export TOKEN=s3cret\n")
    entries = {e["name"]: e["type"] for e in listing(authed_client).json()["entries"]}
    assert entries["home"] == "link_outside" and entries["rc"] == "link_outside"
    refused = raw(authed_client, "rc")
    assert refused.status_code == 422
    assert "link outside the run" in refused.json()["detail"]
    assert "s3cret" not in refused.text
    assert listing(authed_client, "home").status_code == 422


def test_req13_published_link_never_serves_job_files(
    authed_client: TestClient, results: Results
) -> None:
    """A published symlink (`publishDir mode: 'symlink'`) is followed into a task directory of
    the run's work directory, and never to a file that is not served there (SEC-P3T28-05 r3)."""
    (results.task_dir / "out.bam").write_bytes(b"BAM\x01")
    (results.task_dir / ".command.env").write_text("export TOKEN=s3cret\n")
    (results.task_dir / ".command.run").write_text("export TOKEN=s3cret\n")
    (results.paths.work_dir / "top.txt").write_text("not a task's\n")
    results.root.mkdir()
    (results.root / "out.bam").symlink_to(results.task_dir / "out.bam")
    for name, target in (
        ("env", results.task_dir / ".command.env"),
        ("wrapper", results.task_dir / ".command.run"),
        ("top", results.paths.work_dir / "top.txt"),
    ):
        (results.root / name).symlink_to(target)
    served = raw(authed_client, "out.bam")
    assert served.status_code == 200 and served.content == b"BAM\x01"
    entries = {e["name"]: e["type"] for e in listing(authed_client).json()["entries"]}
    assert entries == {
        "out.bam": "file",
        "env": "link_outside",
        "wrapper": "link_outside",
        "top": "link_outside",
    }
    for name in ("env", "wrapper", "top"):
        found = raw(authed_client, name)
        assert found.status_code == 422, name
        assert "s3cret" not in found.text


def test_req13_results_dir_aliases_refused(
    authed_client: TestClient,
    results: Results,
    writer: Writer,
    settings: Settings,
    synthetic: Path,
    tmp_path: Path,
) -> None:
    """A results directory that names the run's work directory, the home directory or the runs
    root by another path is refused when served, by its inode, not its text (SEC-P3T31-01)."""
    (results.task_dir / ".command.env").write_text("export TOKEN=s3cret\n")
    home = Path(os.environ["HOME"])
    (home / ".nextflow").mkdir(exist_ok=True)
    (home / ".nextflow" / "secrets").write_text("s3cret\n")
    run_dir = results.paths.work_dir.parent
    (tmp_path / "alias").symlink_to(run_dir)
    (tmp_path / "roots").symlink_to(settings.runs_root)
    for alias, secret in (
        ("/" + str(results.paths.work_dir), "/".join(HASH) + "/.command.env"),
        (f"/proc/self/root{home}", ".nextflow/secrets"),
        (str(tmp_path / "alias" / "work"), "/".join(HASH) + "/.command.env"),
        (str(tmp_path / "roots"), f"{RUN}/work/{'/'.join(HASH)}/.command.env"),
    ):
        set_run(writer, RUN, results_dir=alias)
        found = listing(authed_client)
        assert found.status_code == 422, (alias, found.text)
        served = raw(authed_client, secret)
        assert served.status_code == 422, (alias, served.text)
        assert "s3cret" not in served.text
    elsewhere = tmp_path / "elsewhere" / "res"  # outside the runs root and home: served
    elsewhere.mkdir(parents=True)
    (elsewhere / "a.txt").write_text("fine\n")
    set_run(writer, RUN, results_dir=str(elsewhere))
    assert raw(authed_client, "a.txt").text == "fine\n"

    nf = synthetic / "nextflow"
    for refused in ("/" + str(results.paths.work_dir), f"{elsewhere}/../res", "/./tmp"):
        _, stored = launched(authed_client, writer, nf, "nextflow", outdir=refused)
        assert stored is None, refused


def test_req13_results_dir_home_dotdirs_refused(
    authed_client: TestClient,
    results: Results,
    writer: Writer,
    settings: Settings,
    synthetic: Path,
    tmp_path: Path,
) -> None:
    """A results directory that is a dot directory below the home directory (`~/.nextflow`
    holds the Nextflow secrets file, `~/.ssh` the user's keys) is refused at launch, absolute
    or relative, and when served, by any path to it (SEC-P3T31-03)."""
    home = Path(os.environ["HOME"])
    for name, secret in ((".nextflow", "secrets/store.json"), (".ssh", "id_ed25519")):
        (home / name / secret).parent.mkdir(parents=True, exist_ok=True)
        (home / name / secret).write_text("s3cret\n")
    (tmp_path / "nf").symlink_to(home / ".nextflow")
    up = os.path.relpath(home / ".nextflow", run_paths(settings.runs_root, RUN).launch_dir)
    assert up.startswith("../") and up.endswith("/.nextflow")
    nf = synthetic / "nextflow"
    for refused in (str(home / ".nextflow"), up, str(home / ".ssh")):
        _, stored = launched(authed_client, writer, nf, "nextflow", outdir=refused)
        assert stored is None, refused
    # a symlink is a text at launch (its folder may not exist yet): refused when served
    _, stored = launched(authed_client, writer, nf, "nextflow", outdir=str(tmp_path / "nf"))
    assert stored == str(tmp_path / "nf")
    for alias, secret in (
        (str(home / ".nextflow"), "secrets/store.json"),
        (str(home / ".nextflow" / "secrets"), "store.json"),
        (str(home / ".ssh"), "id_ed25519"),
        (str(tmp_path / "nf"), "secrets/store.json"),
    ):
        set_run(writer, RUN, results_dir=alias)
        found = listing(authed_client)
        assert found.status_code == 422, (alias, found.text)
        served = raw(authed_client, secret)
        assert served.status_code == 422, (alias, served.text)
        assert "s3cret" not in served.text


def test_req13_snakemake_results_hide_engine_dirs(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    """A Snakemake run's results directory is its launch directory, without `.snakemake/` and
    `.spectio/`, whatever their case."""
    run_id = "run_01K8T2F1XTVRES0000000000R2"
    paths = make_run_dirs(settings.runs_root, run_id)
    add_run(writer, settings, run_id, "smk", "running", engine="snakemake")
    for rel in (".snakemake/log/x.log", ".spectio/head.out", "results/a.txt"):
        (paths.launch_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (paths.launch_dir / rel).write_text("x\n")
    (paths.launch_dir / ".SPECTIO").mkdir()
    (paths.launch_dir / ".SPECTIO" / "y").write_text("y\n")
    found = listing(authed_client, run_id=run_id).json()
    assert found["root"] == str(paths.launch_dir)
    names = {e["name"] for e in found["entries"]}
    assert "results" in names
    assert not names & {".snakemake", ".spectio", ".SPECTIO"}
    for rel in (".snakemake/log/x.log", ".spectio/head.out", ".SPECTIO/y"):
        assert raw(authed_client, rel, run_id).status_code == 422, rel
    assert listing(authed_client, ".snakemake", run_id).status_code == 422


# --- Raw files and their headers ----------------------------------------------------------


def test_req14_headers(authed_client: TestClient, results: Results) -> None:
    results.write("multiqc/multiqc_report.html", "<html><body>report</body></html>")
    results.write("page.HTM", "<p>upper</p>")
    for rel in ("plot.svg", "page.xhtml", "data.xml", "plot.svgz", "notes.txt", "é t.tsv"):
        results.write(rel, "<svg/>")
    page = raw(authed_client, "multiqc/multiqc_report.html")
    assert page.status_code == 200, page.text
    assert page.headers["content-type"] == "text/html; charset=utf-8"
    assert page.headers["content-security-policy"] == REPORT_CSP
    assert "allow-same-origin" not in page.headers["content-security-policy"]
    assert "content-disposition" not in page.headers
    assert page.text == "<html><body>report</body></html>"
    assert raw(authed_client, "page.HTM").headers["content-security-policy"] == REPORT_CSP
    for rel in ("plot.svg", "page.xhtml", "data.xml", "plot.svgz", "notes.txt"):
        found = raw(authed_client, rel)
        assert found.status_code == 200, rel
        assert found.headers["content-type"] == "application/octet-stream", rel
        assert found.headers["content-disposition"] == f"attachment; filename*=UTF-8''{rel}"
        assert found.headers["content-security-policy"].startswith("sandbox;"), rel
    quoted = raw(authed_client, "é t.tsv").headers["content-disposition"]
    assert quoted == "attachment; filename*=UTF-8''%C3%A9%20t.tsv"
    download = raw(authed_client, "multiqc/multiqc_report.html", download="true")
    assert download.headers["content-disposition"].startswith("attachment;")
    assert download.headers["content-type"] == "application/octet-stream"
    for found in (page, download, raw(authed_client, "notes.txt")):
        assert found.headers["cache-control"] == "no-store"
        assert found.headers["referrer-policy"] == "no-referrer"
        assert found.headers["x-content-type-options"] == "nosniff"
    assert raw(authed_client, "missing.html").status_code == 404
    assert raw(authed_client, "multiqc").status_code == 422  # a folder is not a file


def test_raw_whole_file_in_chunks(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report is served whole, read in capped chunks (each in the file pool); one past
    `MAX_RAW` is refused."""
    monkeypatch.setattr(files_results, "CHUNK", 7)
    body = "".join(f"line {i}\n" for i in range(100))
    results.write("big.html", body)
    assert raw(authed_client, "big.html").text == body
    monkeypatch.setattr(api_results, "MAX_RAW", 100)
    too_big = raw(authed_client, "big.html")
    assert too_big.status_code == 413
    assert too_big.json()["type"] == "/problems/file-too-large"


def test_raw_cut_mid_stream_is_incomplete(
    served: str,
    session: dict[str, str],
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A read that fails after the headers are sent aborts the response: with its
    `Content-Length`, the client sees a short body as a failed download, not a whole file
    (CR-P3T31-03)."""
    paths = make_run_dirs(settings.runs_root, RUN)
    root = paths.launch_dir / "results"
    add_run(writer, settings, RUN, "rnaseq", "running", results_dir=str(root))
    root.mkdir()
    (root / "big.tsv").write_text("x" * 20)
    monkeypatch.setattr(files_results, "CHUNK", 7)
    real, calls = files_results.read_chunk, []

    def failing(*args: Any) -> bytes:
        calls.append(args)
        if len(calls) == 2:
            raise OSError(errno.EIO, "I/O error")
        return real(*args)

    monkeypatch.setattr(files_results, "read_chunk", failing)
    with (
        httpx2.Client(base_url=served, timeout=10, cookies=session) as http,
        http.stream("GET", f"{API}/runs/{RUN}/results/raw/big.tsv") as response,
    ):
        assert response.status_code == 200
        assert response.headers["content-length"] == "20"
        with pytest.raises(httpx2.RemoteProtocolError):
            response.read()


# --- Stat and text reads (FU-P3-85a; api §5.3) ---------------------------------------------


def test_req13_results_stat(authed_client: TestClient, results: Results) -> None:
    """The listing's entry for one path, with the listing's checks and problems."""
    problem(stat_of(authed_client, "a.txt"), 404, "not-found")  # no results directory yet
    results.write("multiqc/a.txt", "four")
    (results.task_dir / "out.bam").write_bytes(b"BAM\x01")
    (results.root / "out.bam").symlink_to(results.task_dir / "out.bam")
    (results.root / "away").symlink_to("/etc/hostname")
    found = stat_of(authed_client, "multiqc/a.txt")
    assert found.status_code == 200, found.text
    body = found.json()
    assert body.pop("mtime").endswith("+00:00")
    assert body == {
        "root": str(results.root),
        "path": "multiqc/a.txt",
        "name": "a.txt",
        "type": "file",
        "size": 4,
    }
    assert found.headers["cross-origin-resource-policy"] == "same-origin"
    folder = stat_of(authed_client, "multiqc").json()
    assert (folder["type"], folder["size"]) == ("dir", None)
    assert stat_of(authed_client, "out.bam").json()["size"] == 4  # a published link
    away = stat_of(authed_client, "away").json()
    assert (away["type"], away["size"], away["mtime"]) == ("link_outside", None, None)
    problem(stat_of(authed_client, "multiqc/none.txt"), 404, "not-found")
    problem(stat_of(authed_client, "none/a.txt"), 404, "not-found")
    for bad in (".spectio/x", "a\u202eb", ".nextflow", "a/%2e%2e/b"):
        problem(stat_of(authed_client, bad), 422, "file-not-allowed")


def test_req13_results_text_tail(authed_client: TestClient, results: Results) -> None:
    data = bytes(range(32, 127)) * 1100  # ~100 KiB of printable text
    results.write("big.txt")
    (results.root / "big.txt").write_bytes(data)
    found = text(authed_client, "big.txt")
    assert found.status_code == 200, found.text
    assert found.content == data[-65536:]
    assert "content-range" not in found.headers
    assert text(authed_client, "big.txt", params={"tail": 10}).content == data[-10:]
    big = text(authed_client, "big.txt", params={"tail": MIB + 1})
    problem(big, 422, "validation-failed")


def test_req13_results_text_headers(authed_client: TestClient, results: Results) -> None:
    results.write("page.html", "<script>alert(1)</script>\n")
    found = text(authed_client, "page.html")
    assert found.status_code == 200, found.text
    assert found.text == "<script>alert(1)</script>\n"
    assert found.headers["content-type"] == "text/plain; charset=utf-8"
    assert found.headers["content-security-policy"] == TEXT_CSP
    assert found.headers["cross-origin-resource-policy"] == "same-origin"
    assert found.headers["x-content-type-options"] == "nosniff"
    assert found.headers["cache-control"] == "no-store"
    assert found.headers["referrer-policy"] == "no-referrer"
    assert "content-disposition" not in found.headers


def test_req13_results_text_range(authed_client: TestClient, results: Results) -> None:
    results.write("a.txt", "0123456789")
    found = text(authed_client, "a.txt", headers={"Range": "bytes=2-5"})
    assert found.status_code == 206, found.text
    assert found.text == "2345"
    assert found.headers["content-range"] == "bytes 2-5/10"
    rest = text(authed_client, "a.txt", headers={"Range": "bytes=6-"})
    assert (rest.text, rest.headers["content-range"]) == ("6789", "bytes 6-9/10")
    (results.root / "big.txt").write_bytes(b"y" * (2 * MIB))
    capped = text(authed_client, "big.txt", headers={"Range": f"bytes=0-{5 * MIB}"})
    assert len(capped.content) == MIB
    assert capped.headers["content-range"] == f"bytes 0-{MIB - 1}/{2 * MIB}"
    for bad in ("bytes=9-1", "bytes=10-", "bytes=0-1,4-5", "lines=1-2"):
        problem(text(authed_client, "a.txt", headers={"Range": bad}), 422, "validation-failed")


def test_req13_results_text_utf8_seam(authed_client: TestClient, results: Results) -> None:
    """A range that splits `C3 A9` ends before it, `Content-Range` gives the real end, and the
    next read from its last byte + 1 starts on the whole character."""
    data = "abcé.def".encode()  # é is bytes 3 and 4
    (results.root).mkdir()
    (results.root / "seam.txt").write_bytes(data)
    first = text(authed_client, "seam.txt", headers={"Range": "bytes=0-3"})
    assert first.status_code == 206, first.text
    assert first.content == b"abc"
    assert first.headers["content-range"] == f"bytes 0-2/{len(data)}"
    nxt = text(authed_client, "seam.txt", headers={"Range": "bytes=3-"})
    assert nxt.text == "é.def"
    assert nxt.headers["content-range"] == f"bytes 3-{len(data) - 1}/{len(data)}"
    four = "x\U0001f600".encode()  # a 4-byte sequence cut after each of its first 3 bytes
    (results.root / "emoji.txt").write_bytes(four + b"!")
    for last in (1, 2, 3):
        cut = text(authed_client, "emoji.txt", headers={"Range": f"bytes=0-{last}"})
        assert (cut.text, cut.headers["content-range"]) == ("x", "bytes 0-0/6"), last
    lone = text(authed_client, "seam.txt", headers={"Range": "bytes=3-3"})
    assert lone.headers["content-range"] == f"bytes 3-3/{len(data)}"  # never an empty range
    (results.root / "end.txt").write_bytes(b"ab\xc3")  # a file that ends mid-sequence
    end = text(authed_client, "end.txt", headers={"Range": "bytes=0-"})
    assert (end.text, end.headers["content-range"]) == ("ab\ufffd", "bytes 0-2/3")


def test_req13_results_text_empty_file(authed_client: TestClient, results: Results) -> None:
    results.write("empty.txt", "")
    for headers in ({}, {"Range": "bytes=0-"}, {"Range": "bytes=0-99"}):
        found = text(authed_client, "empty.txt", headers=headers)
        assert found.status_code == 200, (headers, found.text)
        assert found.content == b""
        assert "content-range" not in found.headers


def test_req13_results_text_not_text(authed_client: TestClient, results: Results) -> None:
    results.root.mkdir()
    (results.root / "reads.bam").write_bytes(b"BAM\x00" + b"x" * 100)
    problem(text(authed_client, "reads.bam"), 415, "binary-file")
    (results.root / "latin.txt").write_bytes(b"caf\xe9\n\x1b[31mred\x1b[0m\xe2\x80\xae\n")
    assert text(authed_client, "latin.txt").text == "caf\ufffd\nred\n"  # U+202E removed


def test_req13_results_text_confined(
    authed_client: TestClient, results: Results, settings: Settings, writer: Writer
) -> None:
    results.write("sub/a.txt")
    (results.task_dir / "out.txt").write_text("published\n")
    (results.task_dir / ".command.env").write_text("export TOKEN=s3cret\n")
    (results.root / "out.txt").symlink_to(results.task_dir / "out.txt")
    (results.root / "env").symlink_to(results.task_dir / ".command.env")
    (results.root / "rc").symlink_to(Path(os.environ["HOME"]) / ".bashrc")
    assert text(authed_client, "out.txt").text == "published\n"
    for bad in ("env", "rc", "sub", ".spectio/head.out", "a\u202eb", "a/%2e%2e/b"):
        found = text(authed_client, bad)
        problem(found, 422, "file-not-allowed")
        assert "s3cret" not in found.text
    problem(text(authed_client, "sub/none.txt"), 404, "not-found")
    observed = "run_01K8T2F1XTVRES0000000000R5"
    make_run_dirs(settings.runs_root, observed)
    add_run(writer, settings, observed, "terminal", "running", origin="cli-observed")
    problem(text(authed_client, "a.txt", observed), 404, "not-found")
    problem(stat_of(authed_client, "a.txt", observed), 404, "not-found")


def test_req14_corp_on_every_file_route(authed_client: TestClient, results: Results) -> None:
    results.write("a.txt")
    for found in (listing(authed_client), raw(authed_client, "a.txt")):
        assert found.headers["cross-origin-resource-policy"] == "same-origin"


def test_req2_results_stat_text_need_session(
    settings: Settings, writer: Writer, results: Results
) -> None:
    results.write("a.txt")
    anon = client_for(settings, writer, signed_in=False)
    for found in (text(anon, "a.txt"), stat_of(anon, "a.txt")):
        problem(found, 401, "unauthenticated")


@pytest.mark.parametrize("site", ["same-site", "cross-site"])
def test_req7_results_stat_text_same_site_403(
    authed_client: TestClient, results: Results, site: str
) -> None:
    results.write("a.txt")
    for route in ("text", "stat"):
        found = authed_client.get(
            f"{API}/runs/{RUN}/results/{route}/a.txt", headers={"Sec-Fetch-Site": site}
        )
        assert found.status_code == 403, (route, found.text)


# --- Image mode of the raw route (FU-P3-85b; api §5.3, the table of image-mode steps) -------

IMG = {"Sec-Fetch-Dest": "image"}


def png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">II", width, height) + b"\x08\x06\x00\x00\x00"
    chunk = struct.pack(">I", 13) + b"IHDR" + ihdr
    return b"\x89PNG\r\n\x1a\n" + chunk + struct.pack(">I", zlib.crc32(chunk[4:])) + b"IEND"


def gif(width: int, height: int) -> bytes:
    return b"GIF89a" + struct.pack("<HH", width, height) + b"\x00\x00\x00;"


def webp(kind: bytes, body: bytes) -> bytes:
    chunk = kind + struct.pack("<I", len(body)) + body
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def vp8(width: int, height: int) -> bytes:
    return webp(b"VP8 ", b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", width, height))


def vp8l(width: int, height: int) -> bytes:
    return webp(b"VP8L", b"\x2f" + struct.pack("<I", (width - 1) | (height - 1) << 14))


def vp8x(width: int, height: int) -> bytes:
    size = (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return webp(b"VP8X", b"\x00\x00\x00\x00" + size)


def jpeg(width: int, height: int) -> bytes:
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc2" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def put(results: Results, rel: str, data: bytes) -> Path:
    path = results.root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def image(
    client: TestClient, rel: str, headers: dict[str, str] = IMG, as_: str = "image", **params: Any
) -> Any:
    return client.get(
        f"{API}/runs/{RUN}/results/raw/{rel}", params={"as": as_, **params}, headers=headers
    )


def attachment(response: Any, rel: str) -> None:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == f"attachment; filename*=UTF-8''{rel}"
    assert response.headers["content-security-policy"] == TEXT_CSP
    assert response.headers["vary"] == "Sec-Fetch-Dest"


def test_req14_image_raw_checks_first(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Step 1: every check of the raw route answers first, whatever `as` and the header say."""
    put(results, "plot.png", png(10, 10))
    problem(image(authed_client, "missing.png"), 404, "not-found")
    problem(image(authed_client, "missing.png", as_="thumbnail"), 404, "not-found")
    problem(image(authed_client, ".spectio/plot.png"), 422, "file-not-allowed")
    monkeypatch.setattr(api_results, "MAX_RAW", 10)
    problem(image(authed_client, "plot.png"), 413, "file-too-large")
    problem(image(authed_client, "plot.png", as_="thumbnail"), 413, "file-too-large")


def test_req14_image_download_is_attachment(authed_client: TestClient, results: Results) -> None:
    """Step 2: `?download=true` is the attachment, `as` not read."""
    put(results, "plot.png", png(10, 10))
    attachment(image(authed_client, "plot.png", download="true"), "plot.png")
    attachment(image(authed_client, "plot.png", download="true", as_="x"), "plot.png")
    put(results, "page.html", b"<p>x</p>")
    attachment(image(authed_client, "page.html", download="true"), "page.html")


def test_req14_image_as_other_value(authed_client: TestClient, results: Results) -> None:
    """Step 3: `as` with any value but `image` is `422 validation-failed` on `as`."""
    put(results, "plot.png", png(10, 10))
    for value in ("thumbnail", "", "IMAGE", "image "):
        found = image(authed_client, "plot.png", as_=value)
        problem(found, 422, "validation-failed")
        assert found.json()["errors"][0]["field"] == "as", value


def test_req14_image_name_not_image(authed_client: TestClient, results: Results) -> None:
    """Step 4: `as=image` on a name that is not an image's is `422 file-not-allowed`."""
    for rel in ("page.html", "plot.svgz", "notes.txt", "plot.png.txt", "png", "data.tif"):
        put(results, rel, png(10, 10))
        problem(image(authed_client, rel), 422, "file-not-allowed")
        problem(image(authed_client, rel, headers={}), 422, "file-not-allowed")
    put(results, "UP.PNG", png(10, 10))
    assert image(authed_client, "UP.PNG").headers["content-type"] == "image/png"


def test_req14_image_without_fetch_dest(authed_client: TestClient, results: Results) -> None:
    """Step 5: without `Sec-Fetch-Dest: image` (a navigation, or no Fetch Metadata) the image is
    the attachment, with the 1 GiB cap: no image cap, no signature check."""
    put(results, "fake.png", b"not a png at all")
    for headers in ({}, {"Sec-Fetch-Dest": "document"}, {"Sec-Fetch-Dest": "iframe"}):
        attachment(image(authed_client, "fake.png", headers=headers), "fake.png")
    big = put(results, "big.svg", b"<svg/>")
    os.truncate(big, 5 * MIB + 1)
    attachment(image(authed_client, "big.svg", headers={}), "big.svg")


def test_req14_image_size_caps(authed_client: TestClient, results: Results) -> None:
    """Step 6: with the header, a file over 20 MiB (an SVG over 5 MiB) is `413`."""
    for rel, data, cap in (("a.png", png(10, 10), 20 * MIB), ("a.svg", SVG, 5 * MIB)):
        path = put(results, rel, data)
        os.truncate(path, cap)
        found = image(authed_client, rel)
        assert found.status_code == 200, (rel, found.text[:200])
        assert len(found.content) == cap
        os.truncate(path, cap + 1)
        problem(image(authed_client, rel), 413, "file-too-large")
    path = put(results, "b.png", png(10, 10))
    os.truncate(path, 5 * MIB + 1)  # the SVG cap is for an SVG only
    assert image(authed_client, "b.png").status_code == 200


def test_req14_image_signature_mismatch(authed_client: TestClient, results: Results) -> None:
    """Step 7: a raster file whose first chunk is not the image its name says is `422`; an SVG
    has no signature check."""
    bad = {
        "a.png": jpeg(10, 10),
        "b.jpg": png(10, 10),
        "c.jpeg": b"\xff\xd8",
        "d.gif": b"GIF88a" + gif(10, 10)[6:],
        "e.webp": webp(b"VP9 ", b"\x00" * 10),
        "f.webp": b"RIFX" + vp8x(10, 10)[4:],
        "g.png": png(10, 10)[:8] + b"\x00\x00\x00\x0dIHDX" + png(10, 10)[16:],
        "h.png": png(10, 10)[:20],  # cut inside IHDR
        "i.jpg": b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"\x00" * 14 + b"\xff\xd9",  # no SOF
        "j.jpg": b"\xff\xd8\xff\xe0" + struct.pack(">H", 4000) + b"\x00" * 10,  # segment cut
        "k.jpg": b"\xff\xd8\xff\xda" + b"\x00" * 20,  # scan before any frame
        "l.gif": b"GIF89a\x10",
        "m.webp": vp8(10, 10)[:24],
        "n.png": b"",
    }
    for rel, data in bad.items():
        put(results, rel, data)
        found = image(authed_client, rel)
        problem(found, 422, "file-not-allowed")
        assert "not the image its name says" in found.json()["detail"], rel
    put(results, "x.svg", b"not even xml")
    assert image(authed_client, "x.svg").headers["content-type"] == "image/svg+xml"


def test_req14_image_too_many_pixels(authed_client: TestClient, results: Results) -> None:
    """Step 7: a header that declares more than 50 megapixels is `422` (a PNG of 60000 x 60000
    among them), read from each format's header."""
    big = {
        "huge.png": png(60000, 60000),
        "wide.png": png(50_000_001, 1),
        "huge.gif": gif(65535, 1000),
        "huge-vp8.webp": vp8(10000, 10000),
        "huge-vp8l.webp": vp8l(16384, 16384),
        "huge-vp8x.webp": vp8x(10000, 5001),
        "huge.jpg": jpeg(10000, 5001),
    }
    for rel, data in big.items():
        put(results, rel, data)
        found = image(authed_client, rel)
        problem(found, 422, "file-not-allowed")
        assert "image too large to decode" in found.json()["detail"], rel
    fits = {
        "edge.png": png(10000, 5000),
        "edge.gif": gif(5000, 10000),
        "edge-vp8.webp": vp8(5000, 10000),
        "edge-vp8l.webp": vp8l(5000, 10000),
        "edge-vp8x.webp": vp8x(10000, 5000),
        "edge.jpg": jpeg(10000, 5000),
    }
    for rel, data in fits.items():
        put(results, rel, data)
        assert image(authed_client, rel).status_code == 200, rel


def test_req14_image_served(authed_client: TestClient, results: Results) -> None:
    """Step 8: the image inline, its exact type, the shared headers and the attachment's CSP,
    no `Content-Disposition`."""
    files = {
        "a.png": (png(3, 4), "image/png"),
        "b.jpg": (jpeg(3, 4), "image/jpeg"),
        "c.JPEG": (jpeg(3, 4), "image/jpeg"),
        "d.gif": (gif(3, 4), "image/gif"),
        "e.webp": (vp8(3, 4), "image/webp"),
        "f.webp": (vp8l(3, 4), "image/webp"),
        "g.webp": (vp8x(3, 4), "image/webp"),
        "h.svg": (SVG, "image/svg+xml"),
        "dir/é.png": (png(3, 4), "image/png"),
    }
    for rel, (data, media) in files.items():
        put(results, rel, data)
        found = image(authed_client, quote(rel))
        assert found.status_code == 200, (rel, found.text)
        assert found.content == data, rel
        assert found.headers["content-type"] == media, rel
        assert "content-disposition" not in found.headers, rel
        assert found.headers["content-security-policy"] == TEXT_CSP, rel
        assert found.headers["x-content-type-options"] == "nosniff"
        assert found.headers["cache-control"] == "no-store"
        assert found.headers["referrer-policy"] == "no-referrer"
        assert found.headers["cross-origin-resource-policy"] == "same-origin"
        assert found.headers["vary"] == "Sec-Fetch-Dest"
        assert found.headers["content-length"] == str(len(data))


def test_req14_image_vary_on_every_raw_answer(authed_client: TestClient, results: Results) -> None:
    """`Vary: Sec-Fetch-Dest` on both answers of the raw route: the image and the attachment,
    the report too, so no cache serves one for the other."""
    put(results, "a.png", png(3, 4))
    put(results, "r.html", b"<p>r</p>")
    for found in (
        image(authed_client, "a.png"),
        image(authed_client, "a.png", headers={}),
        raw(authed_client, "a.png"),
        raw(authed_client, "r.html"),
    ):
        assert found.status_code == 200
        assert found.headers["vary"] == "Sec-Fetch-Dest"


def test_req14_image_first_chunk_is_the_body(
    authed_client: TestClient, results: Results, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first chunk, read for the checks, is sent as the first part of the body: the later
    reads start after it (no second open of the bytes checked)."""
    monkeypatch.setattr(files_results, "CHUNK", 32)  # the PNG's IHDR ends at byte 24
    data = png(3, 4) + b"\x00" * 40
    put(results, "a.png", data)
    real, starts = files_results.read_chunk, []

    def counted(where: Any, rel: Any, start: int, *args: Any) -> bytes:
        starts.append(start)
        return real(where, rel, start, *args)

    monkeypatch.setattr(files_results, "read_chunk", counted)
    found = image(authed_client, "a.png")
    assert found.content == data
    assert starts == [32, 64]


def test_req13_raw_file_replaced_mid_download(
    served: str,
    session: dict[str, str],
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every later chunk of the raw route checks `(st_dev, st_ino)` against the first opening:
    a file replaced between chunks aborts the response, image or not (api §5.3)."""
    paths = make_run_dirs(settings.runs_root, RUN)
    root = paths.launch_dir / "results"
    add_run(writer, settings, RUN, "rnaseq", "running", results_dir=str(root))
    root.mkdir()
    monkeypatch.setattr(files_results, "CHUNK", 32)
    real, calls = files_results.read_chunk, []

    def replacing(where: Any, rel: Any, *args: Any) -> bytes:
        calls.append(rel)
        if len(calls) == 1:
            other = root / f"{rel.name}.new"
            other.write_bytes((root / rel).read_bytes())  # same bytes, another inode
            os.replace(other, root / rel)
        return real(where, rel, *args)

    monkeypatch.setattr(files_results, "read_chunk", replacing)
    for rel, query, headers in (("big.tsv", "", {}), ("big.png", "?as=image", IMG)):
        calls.clear()
        (root / rel).write_bytes(png(3, 4) + b"\x00" * 20)
        url = f"{API}/runs/{RUN}/results/raw/{rel}{query}"
        with (
            httpx2.Client(base_url=served, timeout=10, cookies=session) as http,
            http.stream("GET", url, headers=headers) as response,
        ):
            assert response.status_code == 200, rel
            with pytest.raises(httpx2.RemoteProtocolError):
                response.read()
    (root / "same.tsv").write_bytes(b"y" * 100)  # not replaced: served whole, chunk by chunk
    monkeypatch.setattr(files_results, "read_chunk", real)
    with httpx2.Client(base_url=served, timeout=10, cookies=session) as http:
        assert http.get(f"{API}/runs/{RUN}/results/raw/same.tsv").content == b"y" * 100


def test_observed_run_no_results(
    authed_client: TestClient, settings: Settings, writer: Writer
) -> None:
    observed = "run_01K8T2F1XTVRES0000000000R3"
    make_run_dirs(settings.runs_root, observed)
    add_run(writer, settings, observed, "terminal", "running", origin="cli-observed")
    unknown = "run_01K8T2F1XTVRES0000000000R4"
    add_run(writer, settings, unknown, "no-outdir", "running")  # Nextflow, no outdir
    for run_id in (observed, unknown, "run_01K8T2F1XTVRES0000000000ZZ"):
        assert listing(authed_client, run_id=run_id).status_code == 404, run_id
        assert raw(authed_client, "x.html", run_id).status_code == 404, run_id


# --- runs.results_dir at launch -------------------------------------------------------------


def launched(client: TestClient, writer: Writer, location: Path, engine: str, **params: Any) -> Any:
    found = client.post(
        f"{API}/runs",
        json={"workflow": {"location": str(location), "engine": engine}, "params": params},
    )
    assert found.status_code == 201, found.text
    run_id = found.json()["id"]
    with writer.engine.connect() as conn:
        stored = conn.execute(select(runs.c.results_dir).where(runs.c.id == run_id)).scalar()
    assert client.get(f"{API}/runs/{run_id}").json()["results_dir"] == stored
    return run_id, stored


def test_results_dir_at_launch(
    authed_client: TestClient, writer: Writer, settings: Settings, synthetic: Path
) -> None:
    nf = synthetic / "nextflow"
    run_id, stored = launched(authed_client, writer, nf, "nextflow")  # the schema's default
    assert stored == str(run_paths(settings.runs_root, run_id).launch_dir / "results")
    run_id, stored = launched(authed_client, writer, nf, "nextflow", outdir="out//x/")
    assert stored == str(run_paths(settings.runs_root, run_id).launch_dir / "out" / "x")
    _, stored = launched(authed_client, writer, nf, "nextflow", outdir="/data/project/res")
    assert stored == "/data/project/res"
    run_id, stored = launched(authed_client, writer, nf, "nextflow", outdir="./results")
    assert stored == str(run_paths(settings.runs_root, run_id).launch_dir / "results")  # CR-07
    for here in (".", "./"):  # the launch directory: its `.nextflow/` is never served
        run_id, stored = launched(authed_client, writer, nf, "nextflow", outdir=here)
        launch = make_run_dirs(settings.runs_root, run_id).launch_dir
        assert stored == str(launch), here
        (launch / ".nextflow").mkdir(exist_ok=True)
        (launch / ".nextflow" / "history").write_text("h\n")
        (launch / "out.txt").write_text("o\n")
        names = [e["name"] for e in listing(authed_client, run_id=run_id).json()["entries"]]
        assert "out.txt" in names and ".nextflow" not in names, names  # CR-08, SEC-05
        assert raw(authed_client, ".nextflow/history", run_id).status_code == 422
        assert listing(authed_client, ".nextflow", run_id).status_code == 422
    fixed = str(run_paths(settings.runs_root, "run_01K8T2F1XTVRES0000000000R9").launch_dir)
    absolute = files_results.results_dir(
        "nextflow",
        "run_01K8T2F1XTVRES0000000000R9",
        settings.runs_root,
        fixed,
        {"outdir": fixed},
        None,
    )
    assert absolute == fixed  # the same root as `.`: `.nextflow/` hidden by ENGINE_DIRS
    for unservable in ("/x/\udcff", "r\x1b[31m", "r\u202e"):  # SEC-P3T31-06
        assert (
            files_results.results_dir(
                "nextflow", RUN, settings.runs_root, fixed, {"outdir": unservable}, None
            )
            is None
        ), repr(unservable)
    _, stored = launched(authed_client, writer, nf, "nextflow", outdir="r\x1b[31m")
    assert stored is None
    other = str(run_paths(settings.runs_root, run_id).work_dir)
    for refused in (
        "..",  # the run's directory
        "../..",  # the runs root
        "/",
        os.environ["HOME"],
        "../work",  # the run's work directory: its job files
        "../.spectio",
        other,  # another run's
        ".spectio",
        "results/.SNAKEMAKE/x",
        "out/../x",  # a relative `..`, as an absolute one (SEC-P3T31-03)
        ".nextflow",  # the engine's cache and history in the launch directory
        "/data/./res",  # an absolute `.` stays refused
    ):
        _, stored = launched(authed_client, writer, nf, "nextflow", outdir=refused)
        assert stored is None, refused
    run_id, stored = launched(authed_client, writer, synthetic / "snakemake", "snakemake")
    assert stored == str(run_paths(settings.runs_root, run_id).launch_dir)


# --- Follow streams (req. 14) --------------------------------------------------------------


def head_out(settings: Settings, run_id: str, text: str) -> Path:
    path = run_paths(settings.runs_root, run_id).launch_dir / ".spectio" / "head.out"
    with path.open("a") as f:
        f.write(text)
    return path


def test_follow_streams_appended_lines(
    served: str,
    session: dict[str, str],
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`?follow=true` sends the tail, then each line appended, with escapes removed, and ends
    once the run has ended."""
    monkeypatch.setattr(api_logs, "POLL_S", 0.05)
    make_run_dirs(settings.runs_root, RUN)
    add_run(writer, settings, RUN, "nf", "running")
    head_out(settings, RUN, "first\n")
    url = f"{API}/runs/{RUN}/logs?source=head-out&follow=true"
    seen = []
    with (
        httpx2.Client(base_url=served, timeout=10, cookies=session) as http,
        http.stream("GET", url) as response,
    ):
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        chunks = response.iter_text()
        seen.append(next(chunks))
        head_out(settings, RUN, "second \x1b[31mred\x1b[0m\nhalf")
        seen.append(next(chunks))
        head_out(settings, RUN, " line\n")
        set_run(writer, RUN, state="succeeded")
        seen.extend(chunks)  # ends with the run
    assert "".join(seen) == "first\nsecond red\nhalf line\n"


def test_req14_stream_cap(
    served: str,
    session: dict[str, str],
    settings: Settings,
    writer: Writer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fifth follow stream at once → 429 (dev-env §15.3 req. 14). Until sessions (P1 Tasks 12
    to 16), the local API is one session (inbox #86 rule 1), so the cap is the server's."""
    monkeypatch.setattr(api_logs, "POLL_S", 0.05)
    make_run_dirs(settings.runs_root, RUN)
    add_run(writer, settings, RUN, "nf", "running")
    head_out(settings, RUN, "line\n")
    url = f"{API}/runs/{RUN}/logs?source=head-out&follow=true"

    async def scenario() -> tuple[Counter[int], int, Any]:
        async with httpx2.AsyncClient(base_url=served, timeout=10, cookies=session) as http:

            async def one() -> Any:
                return await http.send(http.build_request("GET", url), stream=True)

            opened = await asyncio.gather(*(one() for _ in range(6)))
            codes = Counter(r.status_code for r in opened)
            refused = next(r for r in opened if r.status_code == 429)
            await refused.aread()
            body = refused.json()
            plain = await http.get(url.replace("&follow=true", ""))  # a read takes no slot
            assert plain.status_code == 200
            for response in opened:
                await response.aclose()
            await asyncio.sleep(0.3)  # the server sees the closes
            again = await one()
            await again.aclose()
            return codes, again.status_code, body

    codes, again, body = asyncio.run(scenario())
    assert codes == Counter({200: 4, 429: 2})
    assert body["type"] == "/problems/rate-limited"
    assert again == 200
