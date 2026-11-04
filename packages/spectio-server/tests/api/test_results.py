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
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

from .conftest import add_run

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
    served: str, settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
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
        httpx2.Client(base_url=served, timeout=10) as http,
        http.stream("GET", f"{API}/runs/{RUN}/results/raw/big.tsv") as response,
    ):
        assert response.status_code == 200
        assert response.headers["content-length"] == "20"
        with pytest.raises(httpx2.RemoteProtocolError):
            response.read()


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
    run_id, stored = launched(authed_client, writer, nf, "nextflow", outdir="out/../x/")
    assert stored == str(run_paths(settings.runs_root, run_id).launch_dir / "x")
    _, stored = launched(authed_client, writer, nf, "nextflow", outdir="/data/project/res")
    assert stored == "/data/project/res"
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
    served: str, settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
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
        httpx2.Client(base_url=served, timeout=10) as http,
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
    served: str, settings: Settings, writer: Writer, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fifth follow stream at once → 429 (dev-env §15.3 req. 14). Until sessions (P1 Tasks 12
    to 16), the local API is one session (inbox #86 rule 1), so the cap is the server's."""
    monkeypatch.setattr(api_logs, "POLL_S", 0.05)
    make_run_dirs(settings.runs_root, RUN)
    add_run(writer, settings, RUN, "nf", "running")
    head_out(settings, RUN, "line\n")
    url = f"{API}/runs/{RUN}/logs?source=head-out&follow=true"

    async def scenario() -> tuple[Counter[int], int, Any]:
        async with httpx2.AsyncClient(base_url=served, timeout=10) as http:

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
